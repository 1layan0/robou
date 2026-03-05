"""FastAPI app: health + ML-backed predict for all models."""
import json
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.valuation import DEFAULT_PRICE_PER_SQM, estimate_price_per_sqm
from config.settings import settings
from db import get_db
from services.recommender import get_insights_data
from models.growth_model import (
    GrowthModelNotAvailableError,
    predict_annual_growth_rate_from_request,
)
from models.investment_score import compute_investment_score
from models.price_model import (
    InvalidPredictInputError,
    PriceModelNotAvailableError,
    predict_price_per_sqm_from_request,
)
from models.rent_model import (
    RentModelNotAvailableError,
    predict_monthly_rent_from_request,
)
from models.report_llm import generate_report
from schemas.predict import (
    PROXIMITY_PRICE_FACTOR,
    BestAreaItem,
    BestAreasRequest,
    BestAreasResponse,
    GrowthResponse,
    InvestmentResponse,
    PredictRequest,
    PredictResponse,
    GrowthComponent,
    RecommendDistrictItem,
    RecommendDistrictsRequest,
    RecommendDistrictsResponse,
    ReportResponse,
    RentResponse,
)

app = FastAPI(
    title=settings.app_name,
    description="Robou ML API — land valuation, rent, growth, and investment score.",
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


def _get_price_per_sqm(payload: PredictRequest, db: Session) -> float:
    """Resolve price_per_sqm from ML model or DB/default fallback, then apply proximity factor."""
    try:
        base = predict_price_per_sqm_from_request(payload)
    except InvalidPredictInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PriceModelNotAvailableError:
        try:
            base = estimate_price_per_sqm(
                db, land_use=payload.land_use, area_sqm=payload.area_sqm
            )
        except Exception:
            base = DEFAULT_PRICE_PER_SQM
    except Exception:
        try:
            base = estimate_price_per_sqm(
                db, land_use=payload.land_use, area_sqm=payload.area_sqm
            )
        except Exception:
            base = DEFAULT_PRICE_PER_SQM

    # تعديل السعر حسب القرب من المرافق (قريب=1.0، متوسط=0.97، بعيد=0.92)
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


def _build_reasons(proximity: str | None, growth_rate_pct: float | None) -> list[str]:
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
    city: str | None = Query(None, description="فلتر بالمدينة"),
    district: str | None = Query(None, description="فلتر بالحي"),
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
    property_type: str | None = Query(None, description="نوع العقار، افتراضي سكني"),
) -> dict:
    """بيانات التحليلات الحقيقية: أحياء مع متوسط سعر، معاملات، نمو، وإحصائيات مدن."""
    prop = (property_type or "قطعة أرض-سكنى").strip()
    districts_list, city_stats, meta = get_insights_data(property_type_ar=prop)
    return {
        "districts": districts_list,
        "cityStats": city_stats,
        "meta": meta,
    }


@app.get("/predict/options")
def predict_options() -> dict:
    """إرجاع الخيارات الصحيحة للتنبؤ (نوع العقار، أزواج مدينة-حي)."""
    try:
        from models.price_model import _load_metadata

        meta = _load_metadata()
        return {
            "valid_land_uses": meta["valid_land_uses"],
            "valid_city_districts": meta["valid_city_districts"],
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


@app.post("/predict", response_model=PredictResponse)
def predict(
    payload: PredictRequest,
    db: Session = Depends(get_db),
) -> PredictResponse:
    """مودل السعر: تقدير سعر المتر والسعر الإجمالي."""
    price_per_sqm = _get_price_per_sqm(payload, db)
    total_price = payload.area_sqm * price_per_sqm
    return PredictResponse(
        price_per_sqm=price_per_sqm,
        total_price=total_price,
        currency="SAR",
    )


@app.post("/predict/rent", response_model=RentResponse)
def predict_rent(
    payload: PredictRequest,
    db: Session = Depends(get_db),
) -> RentResponse:
    """مودل الإيجار: تقدير الإيجار الشهري (ريال)."""
    price_per_sqm = _get_price_per_sqm(payload, db)
    try:
        monthly_rent = predict_monthly_rent_from_request(payload, price_per_sqm=price_per_sqm)
    except RentModelNotAvailableError:
        raise HTTPException(
            status_code=503,
            detail="Rent model not trained. Run: python -m scripts.train_rent_model",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return RentResponse(
        monthly_rent_sar=round(monthly_rent, 2),
        price_per_sqm_used=price_per_sqm,
        currency="SAR",
    )


@app.post("/predict/growth", response_model=GrowthResponse)
def predict_growth(payload: PredictRequest) -> GrowthResponse:
    """مودل النمو: معدل نمو سعر المتر السنوي المتوقع."""
    try:
        growth = predict_annual_growth_rate_from_request(payload)
    except GrowthModelNotAvailableError:
        raise HTTPException(
            status_code=503,
            detail="Growth model not trained. Run: python -m scripts.train_growth_model",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return GrowthResponse(
        growth_rate=growth,
        growth_rate_pct=round(growth * 100, 2),
    )


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
        try:
            growth = predict_annual_growth_rate_from_request(req)
        except (GrowthModelNotAvailableError, Exception):
            growth = 0.0
        growth_pct = round(growth * 100, 2)
        reasons = _build_reasons(payload.proximity, growth_pct)
        best_areas.append(
            BestAreaItem(
                city=city,
                district=district,
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


@app.post("/predict/report", response_model=ReportResponse)
def predict_report(
    payload: PredictRequest,
    db: Session = Depends(get_db),
) -> ReportResponse:
    """التوصية + التقرير بالعربي (من LLM أو stub): سعر، نمو، توصية، report_ar."""
    price_per_sqm = _get_price_per_sqm(payload, db)
    total_price = payload.area_sqm * price_per_sqm
    try:
        growth = predict_annual_growth_rate_from_request(payload)
    except (GrowthModelNotAvailableError, Exception):
        growth = 0.03
    growth_pct = growth * 100.0
    result = generate_report(
        price_per_sqm=price_per_sqm,
        total_price=total_price,
        growth_pct=growth_pct,
        district=payload.district or "",
        area_sqm=payload.area_sqm,
        land_use=payload.land_use,
        city=payload.city,
    )
    return ReportResponse(
        price_per_sqm=price_per_sqm,
        total_price=round(total_price, 2),
        growth_rate_pct=round(growth_pct, 2),
        recommendation=result.recommendation,
        score=result.score,
        report_ar=result.report_ar,
        currency="SAR",
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

    if count_in_radius == 0:
        return RecommendDistrictsResponse(
            query=payload.model_dump(exclude_none=True),
            count_in_radius=0,
            top_k=payload.top_k,
            tie=False,
            note="لا توجد أحياء ضمن النطاق",
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


@app.post("/predict/investment", response_model=InvestmentResponse)
def predict_investment(
    payload: PredictRequest,
    db: Session = Depends(get_db),
) -> InvestmentResponse:
    """تقييم الاستثمار: سعر + إيجار + نمو → score وتوصية (strong_buy | buy | hold | avoid)."""
    price_per_sqm = _get_price_per_sqm(payload, db)
    total_price = payload.area_sqm * price_per_sqm

    try:
        monthly_rent = predict_monthly_rent_from_request(payload, price_per_sqm=price_per_sqm)
    except (RentModelNotAvailableError, Exception):
        monthly_rent = (total_price * 0.05) / 12  # fallback 5% annual yield

    try:
        growth = predict_annual_growth_rate_from_request(payload)
    except (GrowthModelNotAvailableError, Exception):
        growth = 0.03  # fallback 3%

    annual_rent = monthly_rent * 12
    rent_yield = annual_rent / total_price if total_price > 0 else 0.0
    liquidity = 0.5  # placeholder; can later use transaction count per district

    summary = compute_investment_score(
        growth_rate=growth,
        rent_yield=rent_yield,
        liquidity=liquidity,
    )

    return InvestmentResponse(
        price_per_sqm=price_per_sqm,
        total_price=round(total_price, 2),
        monthly_rent_sar=round(monthly_rent, 2),
        annual_growth_rate=growth,
        rent_yield=rent_yield,
        liquidity=summary.liquidity,
        score=summary.score,
        recommendation=summary.label,
        currency="SAR",
    )
