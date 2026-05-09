"""FastAPI app: health + ML-backed predict for all models."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.valuation import DEFAULT_PRICE_PER_SQM, estimate_price_per_sqm
from config.settings import settings
from db import get_db
from services.recommender import get_insights_data
from schemas.predict import (
    PROXIMITY_PRICE_FACTOR,
    BestAreaItem,
    BestAreasRequest,
    BestAreasResponse,
    PredictRequest,
    GrowthComponent,
    RecommendDistrictItem,
    RecommendDistrictsRequest,
    RecommendDistrictsResponse,
)
from utils.district_id_map import get_district_id

app = FastAPI(
    title=settings.app_name,
    description="Robou ML API — land valuation, growth, and investment score.",
    version="0.1.0",
)


@app.on_event("startup")
def _startup_cache():
    """تحميل مراكز الأحياء و whitelist مرة واحدة لـ /recommend/districts."""
    global _centroids_map, _whitelist
    if not DISTRICT_CENTROIDS_PATH.exists():
        return
    with open(DISTRICT_CENTROIDS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    for r in data.get("centroids", []):
        city = (r.get("city") or "").strip()
        district = (r.get("district") or "").strip() or "_غير_محدد"
        lat, lon = r.get("latitude"), r.get("longitude")
        if not city or lat is None or lon is None:
            continue
        if city not in ALLOWED_CITIES:
            continue
        _centroids_map[(city, district)] = (float(lat), float(lon))
        _whitelist.add((city, district))


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    """الجذر: معلومات الخدمة وروابط التوثيق."""
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


def _get_price_per_sqm(payload: PredictRequest, db: Session) -> float:
    """سعر المتر من valuation (DB) أو القيمة الافتراضية؛ ثم تعديل حسب القرب من المرافق.
    مودل السعر الرئيسي أُزيل؛ المعتمد هو مودل السعر المجمع في الريكومندر (أفضل أحياء)."""
    try:
        base = estimate_price_per_sqm(
            db, land_use=payload.land_use, area_sqm=payload.area_sqm
        )
    except Exception:
        base = DEFAULT_PRICE_PER_SQM
    proximity = (payload.proximity or "").strip()
    factor = PROXIMITY_PRICE_FACTOR.get(proximity, 1.0)
    return base * factor


DISTRICT_CENTROIDS_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "district_centroids.json"
ALLOWED_CITIES = {"الدمام", "الخبر", "الظهران"}

# Startup cache for recommend/districts: (city_ar, district_ar) -> (lat, lon), whitelist
_centroids_map: dict[tuple[str, str], tuple[float, float]] = {}
_whitelist: set[tuple[str, str]] = set()


def _load_district_centroids() -> list[dict]:
    """تحميل مراكز الأحياء من district_centroids.json (مصدر: Google)."""
    if not DISTRICT_CENTROIDS_PATH.exists():
        return []
    import json
    with open(DISTRICT_CENTROIDS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("centroids", [])


def _pick_top_districts_in_bbox(
    bbox: list[float],
    centroids: list[dict],
    top_n: int = 3,
) -> list[dict]:
    """أفضل حتى top_n أحياء داخل الـ bbox (أو الأقرب لمركز النطاق). لا نملأ من خارج النطاق."""
    if len(bbox) < 4 or not centroids:
        return []
    min_lng, min_lat, max_lng, max_lat = bbox[0], bbox[1], bbox[2], bbox[3]
    center_lat = (min_lat + max_lat) / 2
    center_lng = (min_lng + max_lng) / 2

    inside = [
        c
        for c in centroids
        if (c.get("city") or "").strip() in ALLOWED_CITIES
        and min_lat <= (c.get("latitude") or 0) <= max_lat
        and min_lng <= (c.get("longitude") or 0) <= max_lng
    ]
    if not inside:
        return []  # لا نرجع أحياء من خارج المستطيل أبداً
    inside.sort(
        key=lambda c: (c.get("latitude", 0) - center_lat) ** 2 + (c.get("longitude", 0) - center_lng) ** 2,
    )
    return inside[: max(1, min(top_n, len(inside)))]


def _build_reasons(proximity: Optional[str], growth_rate_pct: Optional[float]) -> list[str]:
    """بناء أسباب مقترحة للحي من القرب والنمو."""
    reasons = []
    p = (proximity or "").strip()
    if p == "قريب":
        reasons.append("قرب من المرافق")
    elif p == "متوسط":
        reasons.append("بعد معتدل عن المرافق")
    elif p == "بعيد":
        reasons.append("بعيد عن المرافق")
    if growth_rate_pct is not None and growth_rate_pct > 0:
        reasons.append("نمو متوقع")
    return reasons if reasons else ["مناسب حسب المعايير المختارة"]


@app.get("/districts/coordinates")
def districts_coordinates(
    city: Optional[str] = Query(None, description="فلتر بالمدينة"),
    district: Optional[str] = Query(None, description="فلتر بالحي"),
) -> dict:
    """إرجاع إحداثيات مراكز الأحياء (من Google Geocoding / district_centroids.json).

    بدون معاملات: كل الأحياء.
    مع city: أحياء المدينة فقط.
    مع city و district: نقطة واحدة إن وُجدت.
    """
    centroids = _load_district_centroids()
    if city:
        city = city.strip()
        centroids = [c for c in centroids if (c.get("city") or "").strip() == city]
    if district:
        district = district.strip()
        centroids = [c for c in centroids if (c.get("district") or "").strip() == district]
    return {"source": "Google", "centroids": centroids}


@app.get("/insights")
def insights(
    property_type: Optional[str] = Query(None, description="نوع العقار، افتراضي سكني"),
) -> dict:
    """بيانات التحليلات الحقيقية: أحياء مع متوسط سعر، معاملات، نمو، وإحصائيات مدن."""
    prop = (property_type or "قطعة أرض-سكنى").strip()
    districts_list, city_stats, meta = get_insights_data(property_type_ar=prop)
    return {
        "districts": districts_list,
        "cityStats": city_stats,
        "meta": meta,
    }


def _deals_from_csv(limit: int) -> list[dict]:
    """قراءة صفقات من real_sales_merged.csv عند فراغ جدول RealSale.

    لضمان ظهور صفقات لكل من الدمام/الخبر/الظهران، نوزّع الاختيار على المدن بدلاً من
    أخذ أول N صف فقط (التي قد تكون كلها لمدينة واحدة).
    """
    csv_path = Path(__file__).resolve().parents[1] / "data" / "real" / "real_sales_merged.csv"
    if not csv_path.exists():
        return []
    try:
        import csv

        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return []
            rows = list(reader)

        # أحدث الصفوف أولاً (year DESC, quarter DESC)
        def key(r: dict) -> tuple[int, int]:
            y = int(r.get("year") or 0)
            q = int(r.get("quarter") or 0)
            return (-y, -q)

        rows.sort(key=key)

        # تحويل إلى شكل موحّد مع تجاهل السجلات الناقصة
        cleaned: list[dict] = []
        for r in rows:
            try:
                city = (r.get("city_ar") or "").strip()
                district = (r.get("district_ar") or "").strip()
                ptype = (r.get("property_type_ar") or "").strip()
                year = int(r.get("year") or 0)
                quarter = int(r.get("quarter") or 0)
                price_sqm = float(r.get("price_per_sqm") or 0)
            except (TypeError, ValueError):
                continue
            if not city or not ptype:
                continue
            price_total = None
            if r.get("price_total"):
                try:
                    price_total = float(r["price_total"])
                except (TypeError, ValueError):
                    pass
            area_sqm = None
            if r.get("area_sqm"):
                try:
                    area_sqm = float(r["area_sqm"])
                except (TypeError, ValueError):
                    pass
            cleaned.append(
                {
                    "city_ar": city,
                    "district_ar": district,
                    "year": year,
                    "quarter": quarter,
                    "property_type_ar": ptype,
                    "price_per_sqm": price_sqm,
                    "price_total": price_total,
                    "area_sqm": area_sqm,
                }
            )

        if not cleaned:
            return []

        # توزيع الصفوف على المدن الثلاث المستهدفة بحيث تحصل كل مدينة على نصيب عادل
        cities = ["الدمام", "الخبر", "الظهران"]
        by_city: dict[str, list[dict]] = {c: [] for c in cities}
        others: list[dict] = []
        for tx in cleaned:
            c = tx["city_ar"]
            if c in by_city:
                by_city[c].append(tx)
            else:
                others.append(tx)

        # الحفاظ على ترتيب الأحدث داخل كل مدينة (cleaned أصلاً مرتب)
        for c in cities:
            by_city[c] = sorted(by_city[c], key=lambda r: (-r["year"], -r["quarter"]))

        per_city_limit = max(1, limit // max(1, len(cities)))
        out: list[dict] = []
        for c in cities:
            out.extend(by_city[c][:per_city_limit])

        # إذا بقي مجال في limit نملأه من بقية الصفوف (أي مدينة) مع الحفاظ على الترتيب الزمني
        if len(out) < limit:
            remaining = [tx for tx in cleaned if tx not in out]
            remaining.sort(key=lambda r: (-r["year"], -r["quarter"]))
            out.extend(remaining[: max(0, limit - len(out))])

        return out[:limit]
    except Exception:
        return []


_valid_deals_city_districts: set[tuple[str, str]] | None = None


def _load_valid_city_districts_for_deals() -> set[tuple[str, str]]:
    """قائمة أزواج (مدينة، حي) المسموح عرضها في صفحة الصفقات."""
    global _valid_deals_city_districts
    if _valid_deals_city_districts is not None:
        return _valid_deals_city_districts
    try:
        config_path = Path(__file__).resolve().parents[1] / "config" / "city_districts.json"
        if not config_path.exists():
            _valid_deals_city_districts = set()
            return _valid_deals_city_districts
        with open(config_path, encoding="utf-8") as f:
            city_districts = json.load(f)
        pairs: set[tuple[str, str]] = set()
        for city, districts in (city_districts or {}).items():
            city_clean = (city or "").strip()
            for dist in districts or []:
                dist_clean = (dist or "").strip()
                if city_clean and dist_clean:
                    pairs.add((city_clean, dist_clean))
        _valid_deals_city_districts = pairs
        return _valid_deals_city_districts
    except Exception:
        _valid_deals_city_districts = set()
        return _valid_deals_city_districts


@app.get("/deals")
def deals(
    limit: int = Query(500, ge=1, le=2000, description="أقصى عدد صفقات"),
    db: Session = Depends(get_db),
) -> dict:
    """آخر صفقات الأراضي من جدول RealSale؛ إن كان فارغاً من ملف real_sales_merged.csv.

    ملاحظة: نكتفي حالياً بتنظيف القيم الواضحة غير المفيدة مثل "أخرى" أو الأحياء الفارغة،
    ولا نقيّد النتائج بقائمة الأحياء المعتمدة حتى لا تُحذف صفقات صحيحة (كما حدث مع الدمام/الظهران).
    """
    try:
        rows = db.execute(
            text("""
                SELECT city_ar, district_ar, year, quarter, property_type_ar,
                       price_per_sqm, price_total, area_sqm
                FROM RealSale
                ORDER BY year DESC, quarter DESC
                LIMIT :lim
            """),
            {"lim": limit},
        ).fetchall()
        if rows:
            transactions: list[dict[str, object]] = []
            for r in rows:
                city = (r[0] or "").strip()
                district = (r[1] or "").strip()
                year = int(r[2])
                quarter = int(r[3])
                ptype = (r[4] or "").strip()
                # استبعاد الأحياء غير المفيدة للمستخدم مثل "أخرى" أو الفارغة
                if not city or not district:
                    continue
                if district in ("أخرى", "اخرى", "غير محدد", "غير معروف"):
                    continue
                price_per_sqm = float(r[5]) if r[5] is not None else 0.0
                price_total = float(r[6]) if r[6] is not None else None
                area_sqm = float(r[7]) if r[7] is not None else None
                transactions.append(
                    {
                        "city_ar": city,
                        "district_ar": district,
                        "year": year,
                        "quarter": quarter,
                        "property_type_ar": ptype,
                        "price_per_sqm": price_per_sqm,
                        "price_total": price_total,
                        "area_sqm": area_sqm,
                    }
                )
            if transactions:
                return {"transactions": transactions}
    except Exception:
        pass
    # جدول RealSale فارغ أو غير متاح → قراءة من CSV + تطبيق نفس الفلاتر
    raw_transactions = _deals_from_csv(limit)
    transactions: list[dict[str, object]] = []
    for r in raw_transactions:
        city = (r.get("city_ar") or "").strip()
        district = (r.get("district_ar") or "").strip()
        if not city or not district:
            continue
        if district in ("أخرى", "اخرى", "غير محدد", "غير معروف"):
            continue
        transactions.append(r)
    return {"transactions": transactions}


@app.get("/predict/options")
def predict_options() -> dict:
    """إرجاع الخيارات الصحيحة للتنبؤ (نوع العقار، أزواج مدينة-حي). مصدر: config أو قوائم افتراضية."""
    try:
        config_path = Path(__file__).resolve().parents[1] / "config" / "city_districts.json"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                city_districts = json.load(f)
            valid_city_districts = [
                {"city": city, "district": dist}
                for city, districts in city_districts.items()
                for dist in (districts or [])
            ]
        else:
            valid_city_districts = []
        valid_land_uses = ["قطعة أرض-سكنى", "قطعة أرض-تجارى", "شقة", "فيلا"]
        return {
            "valid_land_uses": valid_land_uses,
            "valid_city_districts": valid_city_districts,
        }
    except Exception:
        return {"valid_land_uses": [], "valid_city_districts": []}


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Health check: service + DB connectivity."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {
        "status": "ok",
        "service": settings.app_name,
        "db": db_status,
    }


# Growth: نستخدم YoY في الريكومندر؛ هنا قيمة افتراضية للـ endpoints الداخلية
DEFAULT_GROWTH_RATE = 0.03


@app.post("/predict/best-areas", response_model=BestAreasResponse)
def predict_best_areas(
    payload: BestAreasRequest,
    db: Session = Depends(get_db),
) -> BestAreasResponse:
    """أفضل 1–3 أحياء داخل المستطيل (bbox). إذا المستطيل يضم حي واحد نرجع واحد؛ أكثر من حي نرجع مقارنة 2–3."""
    centroids = _load_district_centroids()
    top_districts = _pick_top_districts_in_bbox(
        list(payload.bbox),
        centroids,
        top_n=payload.top_n,
    )
    if not top_districts:
        raise HTTPException(
            status_code=404,
            detail="لا توجد أحياء في النطاق المحدد (الدمام، الخبر، الظهران فقط).",
        )
    best_areas: list[BestAreaItem] = []
    for c in top_districts:
        city = (c.get("city") or "").strip()
        district = (c.get("district") or "").strip()
        lat = float(c.get("latitude", 0))
        lng = float(c.get("longitude", 0))
        req = PredictRequest(
            city=city,
            district=district,
            area_sqm=payload.area_sqm,
            land_use=payload.land_use,
            proximity=payload.proximity or "قريب",
        )
        try:
            price_per_sqm = _get_price_per_sqm(req, db)
        except HTTPException:
            price_per_sqm = DEFAULT_PRICE_PER_SQM
        except Exception:
            price_per_sqm = DEFAULT_PRICE_PER_SQM
        growth_pct = round(DEFAULT_GROWTH_RATE * 100, 2)
        reasons = _build_reasons(payload.proximity, growth_pct)
        best_areas.append(
            BestAreaItem(
                city=city,
                district=district,
                district_id=get_district_id(city, district),
                latitude=round(lat, 6),
                longitude=round(lng, 6),
                price_per_sqm=round(price_per_sqm, 2),
                growth_rate_pct=growth_pct,
                reasons=reasons,
            )
        )
    return BestAreasResponse(
        best_areas=best_areas,
        primary=best_areas[0],
    )


def _ensure_recommend_cache():
    """تعبئة كاش الأحياء إن كان فارغاً (مفيد مع TestClient الذي لا يشغّل startup)."""
    global _centroids_map, _whitelist
    if _whitelist:
        return
    if not DISTRICT_CENTROIDS_PATH.exists():
        return
    with open(DISTRICT_CENTROIDS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    for r in data.get("centroids", []):
        city = (r.get("city") or "").strip()
        district = (r.get("district") or "").strip() or "_غير_محدد"
        lat, lon = r.get("latitude"), r.get("longitude")
        if not city or lat is None or lon is None:
            continue
        if city not in ALLOWED_CITIES:
            continue
        _centroids_map[(city, district)] = (float(lat), float(lon))
        _whitelist.add((city, district))


@app.post("/recommend/districts", response_model=RecommendDistrictsResponse)
def recommend_districts(payload: RecommendDistrictsRequest) -> RecommendDistrictsResponse:
    """اقتراح أفضل أحياء داخل نطاق (دائرة): mode + budget + score + confidence. التقدير دائماً على أحدث ربع متاح."""
    from services.recommender import (
        compute_scores,
        get_districts_in_radius,
        get_latest_period,
        predict_price_for_districts,
    )

    _ensure_recommend_cache()
    year, quarter = get_latest_period()
    city_filter = (payload.city_ar or "").strip() or None
    districts = get_districts_in_radius(
        payload.center_lat,
        payload.center_lon,
        payload.radius_km,
        _centroids_map,
        _whitelist,
        city_ar=city_filter,
    )
    count_in_radius = len(districts)

    # فلتر جغرافي: إن وُجد bbox (المستطيل المرسوم) نعيد فقط الأحياء داخل المستطيل
    if payload.bbox is not None and len(payload.bbox) >= 4:
        try:
            min_lng, min_lat = float(payload.bbox[0]), float(payload.bbox[1])
            max_lng, max_lat = float(payload.bbox[2]), float(payload.bbox[3])
            if min_lng <= max_lng and min_lat <= max_lat:
                districts = [
                    d for d in districts
                    if min_lat <= d["lat"] <= max_lat and min_lng <= d["lon"] <= max_lng
                ]
        except (TypeError, ValueError):
            pass

    if len(districts) == 0:
        note = "لا توجد أحياء ضمن المستطيل المحدد" if (payload.bbox is not None and len(payload.bbox) >= 4) else "لا توجد أحياء ضمن النطاق"
        return RecommendDistrictsResponse(
            query=payload.model_dump(exclude_none=True),
            count_in_radius=count_in_radius,
            top_k=0,
            tie=False,
            note=note,
            results=[],
            mode_used=payload.mode,
            latest_year=year,
            latest_quarter=quarter,
            used_weights={},
        )

    districts = predict_price_for_districts(
        districts,
        payload.property_type_ar,
        year,
        quarter,
        _centroids_map,
    )

    # Budget filter: استبعاد خارج النطاق
    if payload.min_price_per_sqm is not None:
        districts = [d for d in districts if d["predicted_median_price_per_sqm"] >= payload.min_price_per_sqm]
    if payload.max_price_per_sqm is not None:
        districts = [d for d in districts if d["predicted_median_price_per_sqm"] <= payload.max_price_per_sqm]

    if not districts:
        return RecommendDistrictsResponse(
            query=payload.model_dump(exclude_none=True),
            count_in_radius=count_in_radius,
            top_k=0,
            tie=False,
            note="لا توجد أحياء ضمن نطاق السعر المحدد",
            results=[],
            mode_used=payload.mode,
            latest_year=year,
            latest_quarter=quarter,
            used_weights={},
        )

    weights = None
    if payload.weights:
        weights = {
            "price": payload.weights.price,
            "growth": payload.weights.growth,
            "services": payload.weights.services,
        }
    districts, score_meta = compute_scores(
        districts,
        weights=weights,
        property_type_ar=payload.property_type_ar,
        proximity=payload.proximity,
        mode=payload.mode,
    )

    districts.sort(key=lambda d: d["score"], reverse=True)
    top_k = min(payload.top_k, len(districts))
    results = districts[:top_k]

    # فلتر أمان: استبعاد أي حي خارج نطاق السعر المحدد من النتيجة النهائية
    if payload.min_price_per_sqm is not None or payload.max_price_per_sqm is not None:
        def in_range(d: dict) -> bool:
            p = d.get("predicted_median_price_per_sqm")
            if p is None:
                return False
            if payload.min_price_per_sqm is not None and p < payload.min_price_per_sqm:
                return False
            if payload.max_price_per_sqm is not None and p > payload.max_price_per_sqm:
                return False
            return True
        results = [d for d in results if in_range(d)]

    # فلتر أمان جغرافي: استبعاد أي حي خارج المستطيل (bbox) من النتيجة النهائية
    if payload.bbox is not None and len(payload.bbox) >= 4:
        try:
            min_lng = float(payload.bbox[0])
            min_lat = float(payload.bbox[1])
            max_lng = float(payload.bbox[2])
            max_lat = float(payload.bbox[3])
            if min_lng <= max_lng and min_lat <= max_lat:
                results = [
                    d for d in results
                    if min_lat <= d.get("lat", 0) <= max_lat and min_lng <= d.get("lon", 0) <= max_lng
                ]
        except (TypeError, ValueError):
            pass

    if not results:
        return RecommendDistrictsResponse(
            query=payload.model_dump(exclude_none=True),
            count_in_radius=count_in_radius,
            top_k=0,
            tie=False,
            note="لا توجد أحياء ضمن نطاق السعر المحدد",
            results=[],
            mode_used=payload.mode,
            latest_year=year,
            latest_quarter=quarter,
            used_weights={},
        )

    tie = False
    note = None
    if len(results) >= 2 and abs(results[0]["score"] - results[1]["score"]) < 5:
        tie = True
        note = "الأحياء متقاربة"

    out_items: list[RecommendDistrictItem] = []
    for d in results:
        gc = d.get("growth_component")
        growth_component = GrowthComponent(**gc) if gc else None
        out_items.append(
            RecommendDistrictItem(
                city_ar=d["city_ar"],
                district_ar=d["district_ar"],
                district_id=get_district_id(d["city_ar"], d["district_ar"]),
                lat=round(d["lat"], 6),
                lon=round(d["lon"], 6),
                predicted_median_price_per_sqm=round(d["predicted_median_price_per_sqm"], 2),
                score=d["score"],
                confidence=d.get("confidence", "low"),
                confidence_reason=d.get("confidence_reason"),
                services_level=d.get("services_level", "medium"),
                growth_trend=d.get("growth_trend", "flat"),
                reasons_ar=d.get("reasons_ar", [])[:2],
                components=d.get("components", {}),
                growth_component=growth_component,
                price_source=d.get("price_source"),
                deals_count_used=d.get("deals_count_used"),
                baseline_used=round(d["baseline_used"], 2) if d.get("baseline_used") is not None else None,
            )
        )

    return RecommendDistrictsResponse(
        query=payload.model_dump(exclude_none=True),
        count_in_radius=count_in_radius,
        top_k=len(out_items),
        tie=tie,
        note=note,
        results=out_items,
        mode_used=score_meta.get("mode_used", payload.mode),
        latest_year=year,
        latest_quarter=quarter,
        used_weights=score_meta.get("used_weights") or {},
        proximity_applied=score_meta.get("proximity_applied"),
        services_mult=score_meta.get("services_mult"),
    )


