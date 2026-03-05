"""Load and use the annual growth model.

التدريب: scripts/train_growth_model.py (كل البيانات، ميزات زمنية وسوقية).
المدخلات: مدينة، حي، مساحة، استخدام، قرب مرافق؛ عند الاستدعاء يُضاف سنة وعدد صفقات وسعر سابق من الميتاداتا إن لزم.
المخرجات: معدل النمو السنوي (كسر، مثلاً 0.05 = 5%).
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from schemas.predict import PredictRequest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "artifacts" / "growth_model.pkl"
METADATA_PATH = PROJECT_ROOT / "artifacts" / "growth_model_metadata.json"

LAND_USE_ALIASES = {
    "سكني": "قطعة أرض-سكنى",
    "تجاري": "قطعة أرض-تجارى",
    "زراعي": "قطعة أرض-زراعي",
    "قطعة أرض-سكنى": "قطعة أرض-سكنى",
    "قطعة أرض-تجارى": "قطعة أرض-تجارى",
    "قطعة أرض-زراعي": "قطعة أرض-زراعي",
    "أخرى": "أخرى",
    "شقة": "شقة",
    "فيلا": "فيلا",
}


class GrowthModelNotAvailableError(RuntimeError):
    """Raised when the growth model artifact is missing or cannot be loaded."""


_MODEL = None
_METADATA = None


def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    if not MODEL_PATH.exists():
        raise GrowthModelNotAvailableError(
            f"Growth model not found at {MODEL_PATH}. "
            "Train via: python -m scripts.train_growth_model"
        )
    _MODEL = joblib.load(MODEL_PATH)
    return _MODEL


def _load_metadata() -> dict:
    global _METADATA
    if _METADATA is not None:
        return _METADATA
    if not METADATA_PATH.exists():
        raise GrowthModelNotAvailableError(
            f"Growth metadata not found at {METADATA_PATH}. "
            "Train via: python -m scripts.train_growth_model"
        )
    with open(METADATA_PATH, encoding="utf-8") as f:
        _METADATA = json.load(f)
    return _METADATA


def _normalize_land_use(raw: str) -> str:
    key = (raw or "").strip()
    return LAND_USE_ALIASES.get(key, key)


def predict_annual_growth_rate_from_request(payload: PredictRequest) -> float:
    """تقدير معدل النمو السنوي (كسر) للطلب المعطى.

    يستخدم نفس المدخلات مثل مودل السعر: مدينة، حي، مساحة، استخدام، قرب مرافق.
    """
    model = _load_model()
    meta = _load_metadata()

    city = (payload.city or "").strip()
    district = (payload.district or "").strip() or "_غير_محدد"
    land_use = _normalize_land_use(payload.land_use)

    allowed = set(meta.get("allowed_cities", []))
    if allowed and city not in allowed:
        raise ValueError(f"المدينة '{city}' غير مدعومة. المدن: {sorted(allowed)}")
    valid_pairs = {(p["city"], p["district"]) for p in meta.get("valid_city_districts", [])}
    valid_land = set(meta.get("valid_land_uses", []))
    # إن (مدينة، حي) أو النوع غير موجودين في بيانات النمو نرجع نمو افتراضي لئلا نكسر التقرير/الاستثمار
    if valid_pairs and (city, district) not in valid_pairs:
        return 0.03
    if valid_land and land_use not in valid_land:
        return 0.03

    osm_lookup = {(p["city"], p["district"]): p for p in meta.get("osm_features", [])}
    o = osm_lookup.get((city, district), {})
    dist_school = o.get("dist_school_km", 99.0)
    dist_hospital = o.get("dist_hospital_km", 99.0)
    dist_mall = o.get("dist_mall_km", 99.0)
    count_school = int(o.get("count_school_3km", 0))
    count_hospital = int(o.get("count_hospital_3km", 0))
    count_mall = int(o.get("count_mall_3km", 0))
    year_start = int(meta.get("default_prediction_year", 2024))
    deed_prev = float(meta.get("median_deed_count_prev", 5.0))
    price_prev = float(meta.get("median_avg_price_prev", 2000.0))
    avg_price_prev_log = float(np.log1p(price_prev))
    lagged = float(meta.get("median_lagged_growth", 0.03))
    liquidity_2y = float(meta.get("median_liquidity_2y", 10.0))
    price_volatility_log = float(meta.get("median_price_volatility_log", 0.0))
    city_avg_growth = float(meta.get("median_city_avg_growth", 0.03))
    region_avg_growth = float(meta.get("median_region_avg_growth", 0.03))
    growth_2y = float(meta.get("median_growth_2y", 0.03))
    price_trend_slope = float(meta.get("median_price_trend_slope", 0.0))

    row = {
        "year_start": year_start,
        "area_sqm": payload.area_sqm,
        "avg_price_prev": avg_price_prev_log,
        "deed_count_prev": min(deed_prev, 500.0),
        "lagged_growth": lagged,
        "liquidity_2y": min(liquidity_2y, 1000.0),
        "price_volatility": price_volatility_log,
        "city_avg_growth": city_avg_growth,
        "region_avg_growth": region_avg_growth,
        "growth_2y": growth_2y,
        "price_trend_slope": price_trend_slope,
        "dist_school_km": dist_school,
        "dist_hospital_km": dist_hospital,
        "dist_mall_km": dist_mall,
        "count_school_3km": count_school,
        "count_hospital_3km": count_hospital,
        "count_mall_3km": count_mall,
        "land_use": land_use,
        "city": city,
        "district": district,
    }
    X = pd.DataFrame([row])
    pred_residual = model.predict(X)
    residual = float(pred_residual[0])
    if not np.isfinite(residual):
        raise RuntimeError(f"Growth model returned invalid value: {residual}")
    baseline = meta.get("default_baseline_growth", 0.03)
    if meta.get("predicts_residual") and meta.get("baseline_growth_lookup"):
        key = (city, district, land_use)
        for item in meta["baseline_growth_lookup"]:
            if (item.get("city"), item.get("district"), item.get("land_use")) == key:
                baseline = float(item.get("baseline_growth", baseline))
                break
    value = baseline + residual
    value = float(np.clip(value, -0.1, 0.2))
    return value
