"""Load and use the rent model (monthly rent in SAR).

The training script `scripts/train_rent_model.py` saves a scikit-learn
Pipeline to `artifacts/rent_monthly_model.pkl`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

from schemas.predict import PredictRequest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "artifacts" / "rent_monthly_model.pkl"


class RentModelNotAvailableError(RuntimeError):
    """Raised when the rent model artifact is missing or cannot be loaded."""


_MODEL = None  # lazy-loaded Pipeline


def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    if not MODEL_PATH.exists():
        raise RentModelNotAvailableError(
            f"Rent model artifact not found at {MODEL_PATH}. "
            "Train it via `python -m scripts.train_rent_model` first."
        )
    _MODEL = joblib.load(MODEL_PATH)
    return _MODEL


def predict_monthly_rent_from_request(
    payload: PredictRequest,
    price_per_sqm: Optional[float] = None,
) -> float:
    """Predict monthly rent (SAR) from PredictRequest and optional price_per_sqm.

    Features must match those used in `scripts/train_rent_model.py`:
        - area_sqm
        - land_use
        - latitude
        - longitude
        - price_per_sqm

    If price_per_sqm is not provided, we can either:
        - call the price model separately, or
        - fall back to a reasonable default (e.g. 1000 SAR/m²).
    To keep this module decoupled, we expect the caller to pass
    price_per_sqm if available.
    """
    model = _load_model()

    lat: Optional[float] = payload.lat
    lng: Optional[float] = payload.lng

    if price_per_sqm is None or not np.isfinite(price_per_sqm) or price_per_sqm <= 0:
        price_per_sqm = 1000.0

    data = pd.DataFrame(
        [
            {
                "area_sqm": payload.area_sqm,
                "land_use": payload.land_use,
                "latitude": lat,
                "longitude": lng,
                "price_per_sqm": price_per_sqm,
            }
        ]
    )

    pred = model.predict(data)
    value = float(pred[0])
    if not np.isfinite(value) or value <= 0:
        raise RuntimeError(f"Rent model returned invalid monthly rent: {value}")
    return value

