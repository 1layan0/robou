"""Build historical YoY growth table per (city, district, property_type). No NaN in output.

Fallback chain: district yoy_3y_avg -> city yoy_3y_avg -> 0.0 (source=default, confidence=low).
Output: district_growth_yoy.csv with growth_pct, growth_source, growth_confidence.

Input: data/features/district_quarter_md10.csv
Output: data/features/district_growth_yoy.csv, data/features/city_growth_yoy.csv

Run: python scripts/build_district_growth_yoy.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURES_DIR = PROJECT_ROOT / "data" / "features"
DISTRICT_QUARTER_CSV = FEATURES_DIR / "district_quarter_md10.csv"
PRICE_COL = "target_median_price_per_sqm"
OUT_DISTRICT = FEATURES_DIR / "district_growth_yoy.csv"
OUT_CITY = FEATURES_DIR / "city_growth_yoy.csv"


def main() -> None:
    if not DISTRICT_QUARTER_CSV.exists():
        raise FileNotFoundError(
            f"Expected district-quarter table at {DISTRICT_QUARTER_CSV}. "
            "Run scripts/build_district_quarter_dataset.py first."
        )

    df = pd.read_csv(DISTRICT_QUARTER_CSV, encoding="utf-8-sig")
    for c in ["city_ar", "district_ar", "property_type_ar", "year", PRICE_COL]:
        if c not in df.columns:
            raise ValueError(f"Missing column: {c}")

    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["year", PRICE_COL])

    # ---- 1) سنوي حي: (city, district, type, year) -> median price ----
    annual = (
        df.groupby(["city_ar", "district_ar", "property_type_ar", "year"], dropna=False)[PRICE_COL]
        .median()
        .reset_index()
        .rename(columns={PRICE_COL: "annual_median_price_per_sqm"})
    )
    annual = annual.sort_values(["city_ar", "district_ar", "property_type_ar", "year"])
    annual["prev_year_price"] = annual.groupby(["city_ar", "district_ar", "property_type_ar"])[
        "annual_median_price_per_sqm"
    ].shift(1)
    annual["yoy_growth_pct"] = (
        (annual["annual_median_price_per_sqm"] - annual["prev_year_price"])
        / annual["prev_year_price"].replace(0, float("nan"))
        * 100
    )

    # ---- 2) نمو المدينة أولاً (للاستخدام كـ fallback) ----
    city_annual = (
        df.groupby(["city_ar", "property_type_ar", "year"], dropna=False)[PRICE_COL]
        .median()
        .reset_index()
        .rename(columns={PRICE_COL: "annual_median_price_per_sqm"})
    )
    city_annual = city_annual.sort_values(["city_ar", "property_type_ar", "year"])
    city_annual["prev_year_price"] = city_annual.groupby(["city_ar", "property_type_ar"])[
        "annual_median_price_per_sqm"
    ].shift(1)
    city_annual["yoy_growth_pct"] = (
        (city_annual["annual_median_price_per_sqm"] - city_annual["prev_year_price"])
        / city_annual["prev_year_price"].replace(0, float("nan"))
        * 100
    )

    city_rows = []
    for (city_ar, prop_type), grp in city_annual.groupby(["city_ar", "property_type_ar"], dropna=False):
        grp = grp.dropna(subset=["yoy_growth_pct"]).sort_values("year")
        if len(grp) < 1:
            city_rows.append({
                "city_ar": city_ar,
                "property_type_ar": prop_type,
                "yoy_growth_last_year_pct": None,
                "yoy_growth_3y_avg_pct": None,
                "last_year": None,
            })
            continue
        yoy = grp["yoy_growth_pct"].values
        last_year = int(grp["year"].iloc[-1])
        yoy_last = float(yoy[-1])
        yoy_3 = yoy[-3:] if len(yoy) >= 3 else yoy
        yoy_3_avg = float(pd.Series(yoy_3).mean())
        city_rows.append({
            "city_ar": city_ar,
            "property_type_ar": prop_type,
            "yoy_growth_last_year_pct": round(yoy_last, 2),
            "yoy_growth_3y_avg_pct": round(yoy_3_avg, 2),
            "last_year": last_year,
        })

    city_growth_df = pd.DataFrame(city_rows)
    city_lookup = {}
    for _, row in city_growth_df.iterrows():
        c = (row.get("city_ar") or "").strip()
        t = (row.get("property_type_ar") or "").strip()
        v = row.get("yoy_growth_3y_avg_pct")
        if pd.notna(v):
            city_lookup[(c, t)] = float(v)

    # ---- 3) لكل حي: district yoy ثم دمج مع city fallback، لا NaN ----
    district_rows = []
    for key, grp in annual.groupby(["city_ar", "district_ar", "property_type_ar"], dropna=False):
        grp = grp.dropna(subset=["yoy_growth_pct"]).sort_values("year")
        c_ar, d_ar, p_ar = key[0], key[1], key[2]
        yoy_last = None
        yoy_3_avg = None
        yoy_vol = None
        last_year = None

        if len(grp) >= 1:
            yoy = grp["yoy_growth_pct"].values
            last_year = int(grp["year"].iloc[-1])
            yoy_last = round(float(yoy[-1]), 2)
            yoy_3 = yoy[-3:] if len(yoy) >= 3 else yoy
            yoy_3_avg = round(float(pd.Series(yoy_3).mean()), 2)
            yoy_vol = round(float(pd.Series(yoy_3).std()), 2) if len(yoy_3) >= 2 else 0.0

        if yoy_3_avg is not None:
            growth_pct = yoy_3_avg
            growth_source = "district"
            growth_confidence = "high"
        elif (c_ar, p_ar) in city_lookup:
            growth_pct = city_lookup[(c_ar, p_ar)]
            growth_source = "city"
            growth_confidence = "medium"
        else:
            growth_pct = 0.0
            growth_source = "default"
            growth_confidence = "low"

        district_rows.append({
            "city_ar": c_ar,
            "district_ar": d_ar,
            "property_type_ar": p_ar,
            "growth_pct": round(growth_pct, 2),
            "growth_source": growth_source,
            "growth_confidence": growth_confidence,
            "yoy_growth_last_year_pct": yoy_last,
            "yoy_volatility_3y": yoy_vol,
            "last_year": last_year,
        })

    district_growth = pd.DataFrame(district_rows)

    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    district_growth.to_csv(OUT_DISTRICT, index=False, encoding="utf-8-sig")
    city_growth_df.to_csv(OUT_CITY, index=False, encoding="utf-8-sig")

    n_high = (district_growth["growth_source"] == "district").sum()
    n_city = (district_growth["growth_source"] == "city").sum()
    n_default = (district_growth["growth_source"] == "default").sum()
    print(f"Saved {OUT_DISTRICT.name}: {len(district_growth)} rows (district={n_high}, city={n_city}, default={n_default})")
    print(f"Saved {OUT_CITY.name}: {len(city_growth_df)} rows")
    assert district_growth["growth_pct"].isna().sum() == 0, "growth_pct must have no NaN"


if __name__ == "__main__":
    main()
