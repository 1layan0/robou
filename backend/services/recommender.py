"""اقتراح أفضل أحياء داخل نطاق: فلترة بالمسافة، تنبؤ السعر (مودل aggregated)، حساب أفضلية Score."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from utils.geo import haversine_km

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
AGG_MODEL_PATH = ARTIFACTS_DIR / "price_model_agg_residual.pkl"
AGG_METADATA_PATH = ARTIFACTS_DIR / "price_model_agg_residual_metadata.json"
DISTRICT_QUARTER_MD10 = PROJECT_ROOT / "data" / "features" / "district_quarter_md10.csv"
DISTRICT_QUARTER_MD10_W8 = PROJECT_ROOT / "data" / "features" / "district_quarter_md10_w8.csv"
DISTRICT_GROWTH_YOY_CSV = PROJECT_ROOT / "data" / "features" / "district_growth_yoy.csv"
CITY_GROWTH_YOY_CSV = PROJECT_ROOT / "data" / "features" / "city_growth_yoy.csv"

ALLOWED_CITIES = {"الدمام", "الخبر", "الظهران"}
# نمو YoY: أعلى نمو = أفضل. نطاق تقريبي للنسبة -20..+20 → 0..1
GROWTH_PCT_MIN, GROWTH_PCT_MAX = -20.0, 20.0
DEFAULT_FALLBACK_PRICE_PER_SQM = 2500.0

# Cache: (city_ar, district_ar, property_type_ar, year, quarter) -> stats
_dq_map: dict[tuple[str, str, str, int, int], dict[str, Any]] = {}
# Fallback: (city_ar, property_type_ar, year, quarter) -> aggregated stats
_dq_city_type_map: dict[tuple[str, str, int, int], dict[str, Any]] = {}
# Global fallback
_dq_global_map: dict[str, Any] = {}
_dq_loaded = False


# أحدث فترة متاحة من جدول الحي-ربع (تُحمّل مرة واحدة)
_latest_period: tuple[int, int] | None = None


def get_latest_period() -> tuple[int, int]:
    """أحدث (year, quarter) من district_quarter_md10_w8 أو district_quarter_md10. يُستخدم تلقائياً في التقدير."""
    global _latest_period
    if _latest_period is not None:
        return _latest_period
    path = DISTRICT_QUARTER_MD10_W8 if DISTRICT_QUARTER_MD10_W8.exists() else DISTRICT_QUARTER_MD10
    if not path.exists():
        _latest_period = (2023, 1)
        return _latest_period
    df = pd.read_csv(path, encoding="utf-8-sig", usecols=["year", "quarter"], nrows=50000)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    df["quarter"] = pd.to_numeric(df["quarter"], errors="coerce").fillna(1).astype(int)
    df = df.dropna(subset=["year"])
    if df.empty:
        _latest_period = (2023, 1)
        return _latest_period
    max_year = int(df["year"].max())
    sub = df[df["year"] == max_year]
    max_q = int(sub["quarter"].max()) if not sub.empty and "quarter" in sub.columns and sub["quarter"].notna().any() else 1
    _latest_period = (max_year, max_q)
    return _latest_period


def _load_dq_cache() -> None:
    """تحميل جدول الحي-ربع (md10) مرة واحدة وبناء خرائط البحث."""
    global _dq_map, _dq_city_type_map, _dq_global_map, _dq_loaded
    if _dq_loaded:
        return
    if not DISTRICT_QUARTER_MD10.exists():
        _dq_global_map.update({
            "median_price": DEFAULT_FALLBACK_PRICE_PER_SQM,
            "deals_count": 10,
            "iqr_price": 0.0,
            "std_price": 0.0,
            "prev_year_median_price_per_sqm": DEFAULT_FALLBACK_PRICE_PER_SQM,
            "baseline_price": DEFAULT_FALLBACK_PRICE_PER_SQM,
            "baseline_log": np.log1p(DEFAULT_FALLBACK_PRICE_PER_SQM),
        })
        _dq_loaded = True
        return
    df = pd.read_csv(DISTRICT_QUARTER_MD10, encoding="utf-8-sig")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    df["quarter"] = pd.to_numeric(df["quarter"], errors="coerce").fillna(1).astype(int)
    for _, row in df.iterrows():
        c = (str(row.get("city_ar") or "").strip())
        d = (str(row.get("district_ar") or "").strip())
        t = (str(row.get("property_type_ar") or "").strip())
        y = int(row.get("year") or 0)
        q = int(row.get("quarter") or 1)
        if not c or not t:
            continue
        median_p = row.get("target_median_price_per_sqm")
        if pd.isna(median_p):
            median_p = row.get("baseline_price_per_sqm")
        median_p = float(median_p) if not pd.isna(median_p) else DEFAULT_FALLBACK_PRICE_PER_SQM
        deals = float(row.get("deals_count") or 1)
        iqr = float(row.get("iqr_price") or 0)
        std = float(row.get("std_price") or 0)
        prev = row.get("prev_year_median_price_per_sqm")
        prev = float(prev) if prev is not None and not pd.isna(prev) else median_p
        baseline_p = row.get("baseline_price_per_sqm")
        baseline_p = float(baseline_p) if baseline_p is not None and not pd.isna(baseline_p) else median_p
        baseline_l = row.get("baseline_log")
        baseline_l = float(baseline_l) if baseline_l is not None and not pd.isna(baseline_l) else np.log1p(baseline_p)
        stats = {
            "median_price": median_p,
            "deals_count": max(1, int(deals)),
            "iqr_price": iqr,
            "std_price": std,
            "prev_year_median_price_per_sqm": prev,
            "baseline_price": baseline_p,
            "baseline_log": baseline_l,
        }
        _dq_map[(c, d, t, y, q)] = stats
    # City+type+year+quarter aggregates (median of medians, sum deals, mean iqr/std)
    for (c, t, y, q), g in df.groupby(["city_ar", "property_type_ar", "year", "quarter"], dropna=False):
        c, t = (str(c or "").strip(), str(t or "").strip())
        y, q = int(y or 0), int(q or 1)
        if not c or not t:
            continue
        median_p = g["target_median_price_per_sqm"].median()
        median_p = float(median_p) if not pd.isna(median_p) else DEFAULT_FALLBACK_PRICE_PER_SQM
        deals = g["deals_count"].sum()
        deals = max(1, int(deals)) if deals and not pd.isna(deals) else 1
        iqr = float(g["iqr_price"].mean()) if "iqr_price" in g.columns and g["iqr_price"].notna().any() else 0.0
        std = float(g["std_price"].mean()) if "std_price" in g.columns and g["std_price"].notna().any() else 0.0
        prev = g["prev_year_median_price_per_sqm"].median()
        prev = float(prev) if prev is not None and not pd.isna(prev) else median_p
        bl = g["baseline_price_per_sqm"].median() if "baseline_price_per_sqm" in g.columns else median_p
        baseline_p = float(bl) if bl is not None and not pd.isna(bl) else median_p
        _dq_city_type_map[(c, t, y, q)] = {
            "median_price": median_p,
            "deals_count": deals,
            "iqr_price": iqr,
            "std_price": std,
            "prev_year_median_price_per_sqm": prev,
            "baseline_price": baseline_p,
            "baseline_log": np.log1p(baseline_p),
        }
    # Global
    _dq_global_map = {
        "median_price": float(df["target_median_price_per_sqm"].median()) if "target_median_price_per_sqm" in df.columns else DEFAULT_FALLBACK_PRICE_PER_SQM,
        "deals_count": 10,
        "iqr_price": 0.0,
        "std_price": 0.0,
        "prev_year_median_price_per_sqm": float(df["target_median_price_per_sqm"].median()) if "target_median_price_per_sqm" in df.columns else DEFAULT_FALLBACK_PRICE_PER_SQM,
        "baseline_price": float(df["baseline_price_per_sqm"].median()) if "baseline_price_per_sqm" in df.columns else DEFAULT_FALLBACK_PRICE_PER_SQM,
    }
    _dq_global_map["baseline_log"] = np.log1p(_dq_global_map["baseline_price"])
    _dq_loaded = True


FEATURE_COLS_ORDER = [
    "city_ar", "district_ar", "property_type_ar", "year", "quarter",
    "log_deals", "iqr_price", "std_price", "prev_year_median_price_per_sqm",
    "baseline_price_per_sqm", "latitude", "longitude",
    "dist_school_km", "dist_hospital_km", "dist_mall_km",
    "count_school_3km", "count_hospital_3km", "count_mall_3km",
]


def get_districts_in_radius(
    center_lat: float,
    center_lon: float,
    radius_km: float,
    centroids_map: dict[tuple[str, str], tuple[float, float]],
    whitelist: set[tuple[str, str]],
    city_ar: str | None = None,
) -> list[dict[str, Any]]:
    """أحياء داخل النطاق (Haversine)، مع تطبيق whitelist وفلتر المدينة إن وُجد."""
    out = []
    for (c_ar, d_ar), (lat, lon) in centroids_map.items():
        if (c_ar, d_ar) not in whitelist:
            continue
        if c_ar not in ALLOWED_CITIES:
            continue
        if city_ar is not None and (city_ar or "").strip() and c_ar.strip() != (city_ar or "").strip():
            continue
        dist_km = haversine_km(center_lat, center_lon, lat, lon)
        if dist_km > radius_km:
            continue
        out.append({
            "city_ar": c_ar,
            "district_ar": d_ar,
            "lat": lat,
            "lon": lon,
            "distance_km": round(dist_km, 3),
        })
    return out


def _load_agg_model():
    import joblib
    if not AGG_MODEL_PATH.exists():
        return None, None
    model = joblib.load(AGG_MODEL_PATH)
    with open(AGG_METADATA_PATH, encoding="utf-8") as f:
        meta = json.load(f)
    return model, meta


def _load_fallback_medians() -> tuple[float, dict[tuple[str, str], float]]:
    """Global median + (city_ar, property_type_ar) -> median for fallback."""
    global_med = DEFAULT_FALLBACK_PRICE_PER_SQM
    by_city_type: dict[tuple[str, str], float] = {}
    if DISTRICT_QUARTER_MD10.exists():
        df = pd.read_csv(DISTRICT_QUARTER_MD10, encoding="utf-8-sig", nrows=50000)
        if "target_median_price_per_sqm" in df.columns:
            global_med = float(df["target_median_price_per_sqm"].median())
        if "city_ar" in df.columns and "property_type_ar" in df.columns:
            grp = df.groupby(["city_ar", "property_type_ar"])["target_median_price_per_sqm"].median()
            for (c, t), v in grp.items():
                by_city_type[(str(c).strip(), str(t).strip())] = float(v)
    return global_med, by_city_type


_agg_model_cache: tuple[Any, Any] | None = None
_fallback_cache: tuple[float, dict] | None = None


def _get_osm_features(city_district_pairs: list[tuple[str, str]]) -> dict[tuple[str, str], dict[str, float]]:
    """استدعاء build_osm_features_table وإرجاع قاموس (city, district) -> {dist_*, count_*}."""
    out = {}
    try:
        from models.osm_features import build_osm_features_table
        df = build_osm_features_table(city_district_pairs)
        if df.empty:
            for (c, d) in city_district_pairs:
                out[(c, d)] = {
                    "dist_school_km": 99.0, "dist_hospital_km": 99.0, "dist_mall_km": 99.0,
                    "count_school_3km": 0, "count_hospital_3km": 0, "count_mall_3km": 0,
                }
        else:
            for _, row in df.iterrows():
                c, d = (row.get("city") or "").strip(), (row.get("district") or "").strip()
                out[(c, d)] = {
                    "dist_school_km": float(row.get("dist_school_km", 99)),
                    "dist_hospital_km": float(row.get("dist_hospital_km", 99)),
                    "dist_mall_km": float(row.get("dist_mall_km", 99)),
                    "count_school_3km": int(row.get("count_school_3km", 0)),
                    "count_hospital_3km": int(row.get("count_hospital_3km", 0)),
                    "count_mall_3km": int(row.get("count_mall_3km", 0)),
                }
            for (c, d) in city_district_pairs:
                if (c, d) not in out:
                    out[(c, d)] = {
                        "dist_school_km": 99.0, "dist_hospital_km": 99.0, "dist_mall_km": 99.0,
                        "count_school_3km": 0, "count_hospital_3km": 0, "count_mall_3km": 0,
                    }
    except Exception:
        for (c, d) in city_district_pairs:
            out[(c, d)] = {
                "dist_school_km": 99.0, "dist_hospital_km": 99.0, "dist_mall_km": 99.0,
                "count_school_3km": 0, "count_hospital_3km": 0, "count_mall_3km": 0,
            }
    return out


def predict_price_for_districts(
    districts: list[dict[str, Any]],
    property_type_ar: str,
    year: int,
    quarter: int,
    centroids_map: dict[tuple[str, str], tuple[float, float]],
) -> list[dict[str, Any]]:
    """تنبؤ وسيط سعر المتر لكل حي باستخدام (year, quarter) أحدث فترة متاحة."""
    global _agg_model_cache, _fallback_cache
    _load_dq_cache()
    if _fallback_cache is None:
        _fallback_cache = _load_fallback_medians()
    global_med, by_city_type = _fallback_cache
    prop = (property_type_ar or "").strip()
    fallback_baseline = by_city_type.get((districts[0]["city_ar"], prop), global_med) if districts else global_med

    pairs = [(d["city_ar"], d["district_ar"]) for d in districts]
    osm_lookup = _get_osm_features(pairs)

    # استخدم (year, quarter) والمودل
    if _agg_model_cache is None:
        _agg_model_cache = _load_agg_model()
    model, meta = _agg_model_cache
    feature_cols = list(meta.get("feature_cols", FEATURE_COLS_ORDER))
    rows = []
    for d in districts:
        c_ar, d_ar = (d["city_ar"] or "").strip(), (d["district_ar"] or "").strip()
        lat, lon = centroids_map.get((c_ar, d_ar), (26.3, 50.1))
        osm = osm_lookup.get((c_ar, d_ar), {})
        key_dq = (c_ar, d_ar, prop, year, quarter)
        key_ct = (c_ar, prop, year, quarter)
        if key_dq in _dq_map:
            stats = _dq_map[key_dq]
            price_source = "model_district_q"
        elif key_ct in _dq_city_type_map:
            stats = _dq_city_type_map[key_ct]
            price_source = "model_city_q"
        else:
            stats = _dq_global_map
            price_source = "baseline_only"
        deals_count = int(stats.get("deals_count", 1)) if stats else 1
        deals_count = max(1, deals_count)
        iqr_price = float(stats.get("iqr_price", 0)) if stats else 0.0
        std_price = float(stats.get("std_price", 0)) if stats else 0.0
        prev_year = float(stats.get("prev_year_median_price_per_sqm", fallback_baseline)) if stats else fallback_baseline
        baseline_price = float(stats.get("baseline_price") or stats.get("median_price") or fallback_baseline) if stats else fallback_baseline
        d["_price_source"] = price_source
        d["_deals_count_used"] = deals_count
        d["_baseline_used"] = round(baseline_price, 2)
        d["_volatility"] = std_price or iqr_price
        row = {
            "city_ar": c_ar,
            "district_ar": d_ar,
            "property_type_ar": property_type_ar,
            "year": year,
            "quarter": quarter,
            "log_deals": np.log1p(float(deals_count)),
            "iqr_price": iqr_price,
            "std_price": std_price,
            "prev_year_median_price_per_sqm": prev_year,
            "baseline_price_per_sqm": baseline_price,
            "latitude": lat,
            "longitude": lon,
            "dist_school_km": osm.get("dist_school_km", 99.0),
            "dist_hospital_km": osm.get("dist_hospital_km", 99.0),
            "dist_mall_km": osm.get("dist_mall_km", 99.0),
            "count_school_3km": osm.get("count_school_3km", 0),
            "count_hospital_3km": osm.get("count_hospital_3km", 0),
            "count_mall_3km": osm.get("count_mall_3km", 0),
        }
        rows.append(row)

    if not model or not rows:
        for d in districts:
            d["predicted_median_price_per_sqm"] = fallback_baseline
            d["price_source"] = "baseline_only"
            d["deals_count_used"] = d.get("_deals_count_used") or 0
            d["baseline_used"] = d.get("_baseline_used") if d.get("_baseline_used") is not None else fallback_baseline
            d["_volatility"] = d.get("_volatility", 0.0)
            d.pop("_price_source", None)
            d.pop("_deals_count_used", None)
            d.pop("_baseline_used", None)
        return districts

    X = pd.DataFrame(rows)
    for c in feature_cols:
        if c not in X.columns:
            X[c] = 0.0 if "count" in c or "dist" in c or c in ("iqr_price", "std_price") else (global_med if "price" in c or "median" in c else np.log1p(10))
    X = X[feature_cols]

    for i, d in enumerate(districts):
        d["count_school_3km"] = rows[i]["count_school_3km"]
        d["count_hospital_3km"] = rows[i]["count_hospital_3km"]
        d["count_mall_3km"] = rows[i]["count_mall_3km"]
        d["_volatility"] = float(rows[i].get("std_price") or rows[i].get("iqr_price") or 0)

    try:
        pred_resid = model.predict(X)
        baseline_log = np.log1p(X["baseline_price_per_sqm"].values)
        pred_log = baseline_log + pred_resid
        pred_prices = np.expm1(pred_log)
        for i, d in enumerate(districts):
            d["predicted_median_price_per_sqm"] = float(pred_prices[i])
            d["price_source"] = d.get("_price_source", "model_district_q")
            d["deals_count_used"] = d.get("_deals_count_used", 0)
            d["baseline_used"] = d.get("_baseline_used")
            d.pop("_price_source", None)
            d.pop("_deals_count_used", None)
            d.pop("_baseline_used", None)
    except Exception:
        for d in districts:
            d["predicted_median_price_per_sqm"] = by_city_type.get((d["city_ar"], prop), global_med)
            d["price_source"] = "baseline_only"
            d["deals_count_used"] = d.get("_deals_count_used", 0)
            d["baseline_used"] = d.get("_baseline_used", global_med)
            d.pop("_price_source", None)
            d.pop("_deals_count_used", None)
            d.pop("_baseline_used", None)
    return districts


# (city, district, type) -> {"growth_pct": float, "growth_source": str, "growth_confidence": str}
_growth_lookup: dict[tuple[str, str, str], dict[str, Any]] | None = None

# نوع العقار الافتراضي لصفحة التحليلات (سكني)
INSIGHTS_DEFAULT_PROPERTY_TYPE = "قطعة أرض-سكنى"


def get_insights_data(
    property_type_ar: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """إرجاع بيانات التحليلات الحقيقية: قائمة أحياء + إحصائيات مدن + أحدث فترة.
    يُستخدم في GET /insights لعرض صفحة التحليلات بناءً على بيانات الحي-ربع ونمو YoY.
    """
    _load_dq_cache()
    growth_lookup = _load_growth_yoy()
    year, quarter = get_latest_period()
    prop = (property_type_ar or INSIGHTS_DEFAULT_PROPERTY_TYPE).strip()

    # جمع كل (city_ar, district_ar) التي لها بيانات في أحدث فترة لهذا النوع
    seen: set[tuple[str, str]] = set()
    districts_out: list[dict[str, Any]] = []
    for (c, d, t, y, q), stats in _dq_map.items():
        if (c, d) in seen or t != prop or y != year or q != quarter:
            continue
        if c not in ALLOWED_CITIES:
            continue
        seen.add((c, d))
        median_price = float(stats.get("median_price") or DEFAULT_FALLBACK_PRICE_PER_SQM)
        deals_count = int(stats.get("deals_count") or 1)
        growth_info = growth_lookup.get((c, d, prop), {})
        growth_pct = float(growth_info.get("growth_pct") or 0.0)
        # demand: نعكسها كنسبة 0–100 من عدد الصفقات (نسبية داخل البيانات)
        districts_out.append({
            "district": d,
            "city": c,
            "avgPrice": round(median_price, 2),
            "transactions": deals_count,
            "growth": round(growth_pct, 2),
            "demand": min(100, max(0, deals_count * 2)),  # تقريبي: كل 0.5 صفقة = 1%
        })

    # ترتيب حسب المدينة ثم الحي
    districts_out.sort(key=lambda x: (x["city"], x["district"]))

    # إحصائيات المدن: متوسط سعر، مجموع معاملات، متوسط نمو، متوسط طلب
    city_stats: dict[str, dict[str, Any]] = {}
    for c in ALLOWED_CITIES:
        subset = [row for row in districts_out if row["city"] == c]
        if not subset:
            city_stats[c] = {
                "avgPrice": 0,
                "totalTransactions": 0,
                "avgGrowth": 0.0,
                "avgDemand": 0,
            }
            continue
        city_stats[c] = {
            "avgPrice": round(sum(r["avgPrice"] for r in subset) / len(subset), 0),
            "totalTransactions": sum(r["transactions"] for r in subset),
            "avgGrowth": round(sum(r["growth"] for r in subset) / len(subset), 1),
            "avgDemand": round(sum(r["demand"] for r in subset) / len(subset), 0),
        }

    meta = {"year": year, "quarter": quarter, "property_type_ar": prop}
    return districts_out, city_stats, meta


def _load_growth_yoy() -> dict[tuple[str, str, str], dict[str, Any]]:
    """تحميل district_growth_yoy.csv مرة واحدة. كل صف فيه growth_pct (بدون NaN) + source + confidence."""
    global _growth_lookup
    if _growth_lookup is not None:
        return _growth_lookup
    _growth_lookup = {}
    if DISTRICT_GROWTH_YOY_CSV.exists():
        df = pd.read_csv(DISTRICT_GROWTH_YOY_CSV, encoding="utf-8-sig")
        for _, row in df.iterrows():
            c = (row.get("city_ar") or "").strip()
            d = (row.get("district_ar") or "").strip()
            t = (row.get("property_type_ar") or "").strip()
            pct = row.get("growth_pct", 0.0)
            if pd.isna(pct):
                pct = 0.0
            _growth_lookup[(c, d, t)] = {
                "growth_pct": float(pct),
                "growth_source": str(row.get("growth_source") or "default"),
                "growth_confidence": str(row.get("growth_confidence") or "low"),
            }
    return _growth_lookup


def _growth_pct_to_score(pct: float) -> float:
    """تحويل نسبة النمو إلى score 0..1. نطاق تقريبي -20..+20."""
    x = max(GROWTH_PCT_MIN, min(GROWTH_PCT_MAX, float(pct)))
    return (x - GROWTH_PCT_MIN) / (GROWTH_PCT_MAX - GROWTH_PCT_MIN)


def _clip01(x: float) -> float:
    """تقييد القيمة بين 0 و 1."""
    return max(0.0, min(1.0, float(x)))


# أوزان حسب mode (تُستخدم إن لم يُرسل المستخدم weights)
MODE_WEIGHTS = {
    "value": {"price": 0.45, "growth": 0.25, "services": 0.30},
    "premium": {"price": 0.15, "growth": 0.20, "services": 0.65},
    "growth": {"price": 0.20, "growth": 0.60, "services": 0.20},
}
DEFAULT_WEIGHTS = {"price": 0.30, "growth": 0.20, "services": 0.50}

# قيم القرب: معامل الخدمات (يُطبّق على services_score)
PROXIMITY_CONFIG = {
    "قريب": {"services_mult": 1.30},
    "متوسط": {"services_mult": 1.00},
    "بعيد": {"services_mult": 0.60},
}

# عتبات الثقة: deals_count و volatility (std أو iqr)
CONFIDENCE_DEALS_HIGH = 20
CONFIDENCE_DEALS_MEDIUM = 10
CONFIDENCE_VOLATILITY_LOW = 200.0  # std أو iqr تحت هذا = منخفض تقلب


def _confidence_badge(deals_count: int, volatility: float) -> tuple[str, dict[str, Any]]:
    """high: deals>=20 و volatility منخفض؛ medium: deals>=10؛ وإلا low."""
    reason = {"deals_count": deals_count, "volatility": round(volatility, 2)}
    if deals_count >= CONFIDENCE_DEALS_HIGH and volatility <= CONFIDENCE_VOLATILITY_LOW:
        return "high", reason
    if deals_count >= CONFIDENCE_DEALS_MEDIUM:
        return "medium", reason
    return "low", reason


def _services_level(normalized_index: float) -> str:
    """>=0.66 high, 0.33-0.66 medium, <0.33 low."""
    if normalized_index >= 0.66:
        return "high"
    if normalized_index >= 0.33:
        return "medium"
    return "low"


def _growth_trend(growth_pct: float) -> str:
    """>+3% up, -3..+3 flat, <-3% down."""
    if growth_pct > 3.0:
        return "up"
    if growth_pct >= -3.0:
        return "flat"
    return "down"


def _build_reasons_ar_two(components: dict[str, float]) -> list[str]:
    """سببين فقط من أعلى مكوّنين (للتوافق مع الاستدعاءات المنفردة)."""
    labels = [
        ("price_score", "سعر مناسب ضمن النطاق"),
        ("services_score", "خدمات أعلى من المتوسط"),
        ("growth_score", "اتجاه نمو أفضل"),
    ]
    ordered = sorted(
        [(k, components.get(k, 0), msg) for k, msg in labels],
        key=lambda x: -x[1],
    )
    reasons = [msg for _, score, msg in ordered[:2] if score > 0]
    if not reasons:
        reasons = ["مناسب حسب المعايير المختارة"]
    return reasons[:2]


def _build_reasons_ar_ranked(
    districts: list[dict[str, Any]],
) -> None:
    """يُحدّث reasons_ar لكل حي بناءً على ترتيبه بين الثلاثة، مع إضافة نسبة النمو عند ذكر النمو."""
    if not districts:
        return
    prices = [d["predicted_median_price_per_sqm"] for d in districts]
    services_list = [d.get("_raw_services") or 0 for d in districts]
    growth_pcts = [
        (d.get("growth_component") or {}).get("growth_pct", 0.0)
        for d in districts
    ]
    min_price = min(prices)
    max_services = max(services_list)
    max_growth = max(growth_pcts) if growth_pcts else 0.0

    for i, d in enumerate(districts):
        reasons = []
        p = d["predicted_median_price_per_sqm"]
        s = d.get("_raw_services") or 0
        g = (d.get("growth_component") or {}).get("growth_pct", 0.0)

        if p == min_price and (max(prices) - min_price) > 0.01:
            reasons.append("أفضل سعر بين الأحياء الثلاثة")
        if s == max_services and (max(services_list) - min(services_list) or 0) > 0:
            reasons.append("أعلى خدمات في المقارنة")
        if growth_pcts and g == max_growth and max_growth != min(growth_pcts):
            sign = "+" if g >= 0 else ""
            reasons.append(f"أعلى نمو متوقع ({sign}{g:.1f}%)")
        elif growth_pcts and g != 0:
            sign = "+" if g >= 0 else ""
            if len(reasons) < 2:
                reasons.append(f"نمو متوقع ({sign}{g:.1f}%)")

        # إن لم يكفِ سببين، أضف حسب المكوّنات
        comp = d.get("components") or {}
        if len(reasons) < 2:
            labels = [
                ("price_score", "سعر مناسب ضمن النطاق"),
                ("services_score", "خدمات أعلى من المتوسط"),
                ("growth_score", "اتجاه نمو أفضل"),
            ]
            ordered = sorted(
                [(k, comp.get(k, 0), msg) for k, msg in labels],
                key=lambda x: -x[1],
            )
            has_growth_reason = any("نمو" in r for r in reasons)
            for k, score, msg in ordered:
                if score > 0 and len(reasons) < 2:
                    if k == "growth_score":
                        if has_growth_reason:
                            continue
                        if growth_pcts:
                            g = (d.get("growth_component") or {}).get("growth_pct", 0.0)
                            sign = "+" if g >= 0 else ""
                            msg = f"اتجاه نمو أفضل ({sign}{g:.1f}%)"
                    if msg not in reasons:
                        reasons.append(msg)
        if not reasons:
            reasons = ["مناسب حسب المعايير المختارة"]
        d["reasons_ar"] = reasons[:2]


def compute_scores(
    districts: list[dict[str, Any]],
    weights: dict[str, float] | None = None,
    property_type_ar: str | None = None,
    proximity: str = "قريب",
    mode: str = "value",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """حساب Score 0–100 مع mode + proximity، وإرجاع confidence/services_level/growth_trend/reasons_ar (2)."""
    effective_mode = mode or "value"
    meta: dict[str, Any] = {
        "used_weights": None,
        "proximity_applied": proximity,
        "services_mult": None,
        "mode_used": effective_mode,
    }
    if not districts:
        return districts, meta

    services_mult = PROXIMITY_CONFIG.get(proximity, PROXIMITY_CONFIG["متوسط"])["services_mult"]
    meta["services_mult"] = services_mult
    if weights is not None:
        w = {**DEFAULT_WEIGHTS, **weights}
    else:
        w = MODE_WEIGHTS.get(effective_mode, MODE_WEIGHTS["value"])
    meta["used_weights"] = dict(w)

    w_price = w.get("price", 0.5)
    w_growth = w.get("growth", 0.3)
    w_services = w.get("services", 0.2)

    growth_lookup = _load_growth_yoy()
    prop = (property_type_ar or "").strip()

    prices = [d["predicted_median_price_per_sqm"] for d in districts]
    min_p, max_p = min(prices), max(prices)
    range_p = (max_p - min_p) or 1.0

    for d in districts:
        p = d["predicted_median_price_per_sqm"]
        price_score = 1.0 - (p - min_p) / range_p if range_p > 0 else 0.5
        c_ar = (d.get("city_ar") or "").strip()
        d_ar = (d.get("district_ar") or "").strip()
        g = growth_lookup.get((c_ar, d_ar, prop)) if prop else None
        if not g:
            g = {"growth_pct": 0.0, "growth_source": "default", "growth_confidence": "low"}
        growth_pct = g["growth_pct"]
        growth_score = _growth_pct_to_score(growth_pct)
        d["_growth_component"] = {
            "growth_pct": round(growth_pct, 2),
            "source": g["growth_source"],
            "confidence": g["growth_confidence"],
        }
        d["growth_trend"] = _growth_trend(growth_pct)
        c_s = d.get("count_school_3km", 0) or 0
        c_h = d.get("count_hospital_3km", 0) or 0
        c_m = d.get("count_mall_3km", 0) or 0
        d["_raw_services"] = c_s + c_h + c_m
        d["_price_score"] = price_score
        d["_growth_score"] = growth_score

    raw_services_list = [d["_raw_services"] for d in districts]
    min_s, max_s = min(raw_services_list), max(raw_services_list)
    range_s = (max_s - min_s) or 1.0
    for d in districts:
        services_index = (d["_raw_services"] - min_s) / range_s if range_s > 0 else 0.5
        services_score = _clip01(services_index * services_mult)
        d["services_level"] = _services_level(services_index)
        final = 100.0 * (w_price * d["_price_score"] + w_growth * d["_growth_score"] + w_services * services_score)
        d["score"] = int(round(final))
        comp = {
            "price_score": round(d["_price_score"], 4),
            "growth_score": round(d["_growth_score"], 4),
            "services_score": round(services_score, 4),
        }
        d["components"] = comp
        d["growth_component"] = d["_growth_component"]
        deals_count = d.get("deals_count_used") or 0
        vol = d.get("_volatility", 0.0)
        conf, conf_reason = _confidence_badge(deals_count, vol)
        d["confidence"] = conf
        d["confidence_reason"] = conf_reason
    _build_reasons_ar_ranked(districts)
    for d in districts:
        del d["_raw_services"], d["_price_score"], d["_growth_score"], d["_growth_component"]
        d.pop("_volatility", None)
    return districts, meta


def build_reasons_ar(district: dict[str, Any], components: dict[str, float]) -> list[str]:
    """سببين فقط (للتوافق مع الاستدعاءات القديمة)."""
    return _build_reasons_ar_two(components)
