"""Load and use the land price-per-sqm model.

The training script `scripts/train_price_model.py` saves a scikit-learn
Pipeline to `artifacts/price_per_sqm_model.pkl`. This module provides a
thin wrapper to load it once and run predictions based on `PredictRequest`.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from schemas.predict import PredictRequest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "artifacts" / "price_per_sqm_model.pkl"
METADATA_PATH = PROJECT_ROOT / "artifacts" / "price_model_metadata.json"

# تحويل المدخلات الشائعة إلى القيم المدربة بالضبط (يجب أن تطابق البيانات)
LAND_USE_ALIASES = {
    "أرض زراعية": "قطعة أرض-زراعي",
    "زراعي": "قطعة أرض-زراعي",
    "agricultural": "قطعة أرض-زراعي",
    "أرض سكنية": "قطعة أرض-سكنى",
    "سكني": "قطعة أرض-سكنى",
    "سكنى": "قطعة أرض-سكنى",
    "residential": "قطعة أرض-سكنى",
    "أرض تجارية": "قطعة أرض-تجارى",
    "تجاري": "قطعة أرض-تجارى",
    "تجارى": "قطعة أرض-تجارى",
    "commercial": "قطعة أرض-تجارى",
    "شقة": "شقة",
    "apartment": "شقة",
    "فيلا": "فيلا",
    "villa": "فيلا",
    # القيم المدربة (تُقبل كما هي)
    "قطعة أرض-زراعي": "قطعة أرض-زراعي",
    "قطعة أرض-سكنى": "قطعة أرض-سكنى",
    "قطعة أرض-تجارى": "قطعة أرض-تجارى",
    "سكني تجاري": "سكني تجاري",
}


class PriceModelNotAvailableError(RuntimeError):
    """Raised when the ML model artifact is missing or cannot be loaded."""


class InvalidPredictInputError(ValueError):
    """Raised when city/district or land_use is invalid (not in training data)."""


_MODEL = None  # lazy-loaded scikit-learn Pipeline
_METADATA = None  # lazy-loaded validation metadata


def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    if not MODEL_PATH.exists():
        raise PriceModelNotAvailableError(
            f"Price model artifact not found at {MODEL_PATH}. "
            "Train it via `python -m scripts.train_price_model` first."
        )
    _MODEL = joblib.load(MODEL_PATH)
    return _MODEL


def _load_metadata() -> dict:
    global _METADATA
    if _METADATA is not None:
        return _METADATA
    if not METADATA_PATH.exists():
        raise PriceModelNotAvailableError(
            f"Price model metadata not found at {METADATA_PATH}. "
            "Retrain via `python -m scripts.train_price_model`."
        )
    with open(METADATA_PATH, encoding="utf-8") as f:
        _METADATA = json.load(f)
    return _METADATA


def _get_baseline_from_meta(
    meta: dict,
    city: str,
    district: str,
    land_use: str,
    year: int,
    quarter: int,
) -> float:
    """baseline هرمي: level0 → level1 → level2 → global_median."""
    level0 = {(r["city"], r["district"], r["land_use"], r["year"], r["quarter"]): r["median_price_per_sqm"]
              for r in meta.get("baseline_level0") or []}
    level1 = {(r["city"], r["land_use"], r["year"], r["quarter"]): r["median_price_per_sqm"]
              for r in meta.get("baseline_level1") or []}
    level2 = {(r["city"], r["land_use"]): r["median_price_per_sqm"]
              for r in meta.get("baseline_level2") or []}
    global_med = float(meta.get("baseline_global_median", meta.get("default_mean_price_per_sqm", 2500.0)))
    key0 = (city, district, land_use, year, quarter)
    key1 = (city, land_use, year, quarter)
    key2 = (city, land_use)
    if key0 in level0:
        return float(level0[key0])
    if key1 in level1:
        return float(level1[key1])
    if key2 in level2:
        return float(level2[key2])
    return global_med


def _normalize_land_use(raw: str) -> str:
    """تحويل land_use إلى القيمة المدربة."""
    key = (raw or "").strip()
    return LAND_USE_ALIASES.get(key, key)  # إن لم يُعثر يُرجع كما هو


def _validate_predict_input(city: str, district: str, land_use: str) -> None:
    """التحقق من صحة المدخلات، يرفع InvalidPredictInputError إذا كانت غير صحيحة."""
    meta = _load_metadata()
    allowed_cities = set(meta.get("allowed_cities", []))
    valid_land = set(meta["valid_land_uses"])
    valid_pairs = {(p["city"], p["district"]) for p in meta["valid_city_districts"]}

    if allowed_cities and city not in allowed_cities:
        raise InvalidPredictInputError(
            f"المشروع يركز على الدمام والظهران والخبر فقط. المدينة '{city}' غير مدعومة."
        )

    if land_use not in valid_land:
        allowed = ", ".join(sorted(valid_land))
        raise InvalidPredictInputError(
            f"نوع العقار غير صحيح: '{land_use}'. القيم المسموحة: {allowed}"
        )

    if (city, district) not in valid_pairs:
        raise InvalidPredictInputError(
            f"الحي '{district}' غير تابع للمدينة '{city}' في بيانات التدريب. "
            "تأكد من صحة المدينة والحي (يجب أن يكونا زوجاً موجوداً في البيانات)."
        )


def predict_price_per_sqm_from_request(payload: PredictRequest) -> float:
    """Predict price_per_sqm from a PredictRequest using the trained model.

    Features used match `scripts/train_price_model.py` (real data + OSM):
        - area_sqm, land_use, city, district
        - dist_school_km, dist_hospital_km, dist_mall_km (from metadata)

    Raises InvalidPredictInputError if city/district or land_use is invalid.
    """
    city = (payload.city or "").strip()
    district = (payload.district or "").strip()
    if not district:
        district = "_غير_محدد"

    land_use = _normalize_land_use(payload.land_use)
    _validate_predict_input(city, district, land_use)

    meta = _load_metadata()
    osm_features = meta.get("osm_features") or []
    osm_lookup = {(p["city"], p["district"]): p for p in osm_features}
    o = osm_lookup.get((city, district), {})
    year = int(meta.get("default_prediction_year", 2024))
    quarter = int(meta.get("default_prediction_quarter", 1))
    latitude = float(o.get("latitude", 26.3))
    longitude = float(o.get("longitude", 50.1))
    dist_school = o.get("dist_school_km", 99.0)
    dist_hospital = o.get("dist_hospital_km", 99.0)
    dist_mall = o.get("dist_mall_km", 99.0)
    count_school = int(o.get("count_school_3km", 0))
    count_hospital = int(o.get("count_hospital_3km", 0))
    count_mall = int(o.get("count_mall_3km", 0))

    te_default = float(meta.get("te_default_mean", meta.get("default_mean_price_per_sqm", 2500.0)))
    mean_by_city = meta.get("mean_price_by_city") or {}
    mean_by_cd = {(p["city"], p["district"]): p["mean_price_per_sqm"] for p in meta.get("mean_price_by_city_district") or []}
    mean_by_land_use = meta.get("mean_price_by_land_use") or {}
    city_te = mean_by_city.get(city, te_default)
    district_te = mean_by_cd.get((city, district), te_default)
    land_use_te = mean_by_land_use.get(land_use, te_default)

    prev_year = year - 1
    city_prev_year_median = float(meta.get("default_mean_price_per_sqm", 2500.0))
    for p in meta.get("city_year_median_lookup", []):
        if (p["city"], p["year"]) == (city, prev_year):
            city_prev_year_median = float(p["city_year_median_price_per_sqm"])
            break
    district_prev_year_median = city_prev_year_median
    for p in meta.get("district_year_median_lookup", []):
        if (p["city"], p["district"], p["year"]) == (city, district, prev_year):
            district_prev_year_median = float(p["district_year_median_price_per_sqm"])
            break
    deals_prev_year_count = 0

    # مزيج مع متوسط الدلو إن وُجد (لرفع R²): أفضل تطابق = سنة+ربع ثم سنة ثم دلو عام
    bucket_mean = float(meta.get("default_mean_price_per_sqm", 2500.0))
    for p in meta.get("bucket_mean_lookup", []):
        if (p["city"], p["district"], p["land_use"]) == (city, district, land_use):
            bucket_mean = float(p["mean_price_per_sqm"])
            break
    bucket_mean_year = bucket_mean
    for p in meta.get("bucket_mean_year_lookup", []):
        if (p["city"], p["district"], p["land_use"], p["year"]) == (city, district, land_use, year):
            bucket_mean_year = float(p["mean_price_per_sqm"])
            break
    bucket_mean_year_quarter = bucket_mean_year
    for p in meta.get("bucket_mean_year_quarter_lookup", []):
        if (p["city"], p["district"], p["land_use"], p["year"], p["quarter"]) == (city, district, land_use, year, quarter):
            bucket_mean_year_quarter = float(p["mean_price_per_sqm"])
            break

    baseline_price = _get_baseline_from_meta(meta, city, district, land_use, year, quarter)

    model = _load_model()
    area = max(1.0, float(payload.area_sqm))
    row = {
        "year": year,
        "quarter": quarter,
        "area_sqm": area,
        "log_area_sqm": float(np.log1p(area)),
        "latitude": latitude,
        "longitude": longitude,
        "land_use": land_use,
        "city": city,
        "district": district,
        "dist_school_km": dist_school,
        "dist_hospital_km": dist_hospital,
        "dist_mall_km": dist_mall,
        "count_school_3km": count_school,
        "count_hospital_3km": count_hospital,
        "count_mall_3km": count_mall,
        "mean_price_by_city": city_te,
        "mean_price_by_city_district": district_te,
        "mean_price_by_land_use": land_use_te,
        "city_prev_year_median_price_per_sqm": city_prev_year_median,
        "district_prev_year_median_price_per_sqm": district_prev_year_median,
        "deals_prev_year_count": deals_prev_year_count,
    }
    data = pd.DataFrame([row])
    pred = model.predict(data)
    pred_val = float(pred[0])
    if meta.get("model_is_residual"):
        value = float(np.expm1(np.log1p(baseline_price) + pred_val))
    elif meta.get("target_is_log"):
        value = float(np.expm1(pred_val))
    else:
        value = pred_val
    alpha = float(meta.get("blend_alpha", 0))
    if alpha > 0:
        value = alpha * baseline_price + (1 - alpha) * value
    # Guardrail: prices must be positive and not absurdly small
    if not np.isfinite(value) or value <= 0:
        raise RuntimeError(f"Model returned invalid price_per_sqm: {value}")
    return value

