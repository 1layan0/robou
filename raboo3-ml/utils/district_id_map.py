"""خريطة (city_ar, district_ar) → district_id تتوافق مع ترتيب إدراج جدول District من district_centroids.csv."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DISTRICT_CENTROIDS_CSV = PROJECT_ROOT / "data" / "raw" / "district_centroids.csv"


@lru_cache(maxsize=1)
def district_id_by_key() -> dict[tuple[str, str], int]:
    if not DISTRICT_CENTROIDS_CSV.exists():
        return {}
    df = pd.read_csv(DISTRICT_CENTROIDS_CSV, encoding="utf-8-sig")
    out: dict[tuple[str, str], int] = {}
    for i, row in enumerate(df.itertuples(index=False), start=1):
        c = str(getattr(row, "city", "") or "").strip()
        d = str(getattr(row, "district", "") or "").strip()
        if c and d:
            out[(c, d)] = i
    return out


def get_district_id(city_ar: str, district_ar: str) -> int | None:
    return district_id_by_key().get(((city_ar or "").strip(), (district_ar or "").strip()))


def require_district_id(city_ar: str, district_ar: str) -> int:
    i = get_district_id(city_ar, district_ar)
    if i is None:
        raise KeyError(f"لا district_id للمدينة/الحي: {city_ar!r} / {district_ar!r}")
    return i
