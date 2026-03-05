"""Build district-quarter aggregated dataset for the aggregated price model.

- Reads: data/real/real_sales_merged.csv
- Filters: only land (property_type_ar contains قطعة أرض), price_per_sqm in [500, 20000]
- Groupby: city_ar, district_ar, property_type_ar, year, quarter
- Aggregates: target_median_price_per_sqm, deals_count, iqr_price, std_price, min_price, max_price
- Merges district-level features (centroids + OSM/Google) on (city_ar, district_ar)
- Output: data/features/district_quarter_dataset.csv

Run from project root: python scripts/build_district_quarter_dataset.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
REAL_DATA_PATH = PROJECT_ROOT / "data" / "real" / "real_sales_merged.csv"
FEATURES_DIR = PROJECT_ROOT / "data" / "features"
OUTPUT_PATH = FEATURES_DIR / "district_quarter_dataset.csv"
OUTPUT_PATH_BASELINE = FEATURES_DIR / "district_quarter_dataset_with_baseline.csv"
DISTRICT_CENTROIDS_JSON = PROJECT_ROOT / "data" / "raw" / "district_centroids.json"

# قيم min_deals للتجربة التلقائية (جودة الوسيط)
MIN_DEALS_LIST = [2, 5, 10]
OSM_DIST_COLS = ["dist_school_km", "dist_hospital_km", "dist_mall_km"]
OSM_COUNT_COLS = ["count_school_3km", "count_hospital_3km", "count_mall_3km"]

ONLY_LAND_PATTERN = "قطعة أرض"
MIN_PRICE_PER_SQM = 500
MAX_PRICE_PER_SQM = 20_000


def load_and_filter_sales() -> pd.DataFrame:
    """Load real sales and apply same filters as main price pipeline."""
    if not REAL_DATA_PATH.exists():
        raise FileNotFoundError(f"Expected {REAL_DATA_PATH}. Run merge_real_estate_data first.")
    df = pd.read_csv(REAL_DATA_PATH, encoding="utf-8-sig")
    # Ensure numeric
    df["price_per_sqm"] = pd.to_numeric(df["price_per_sqm"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["quarter"] = pd.to_numeric(df["quarter"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["price_per_sqm", "year", "quarter", "city_ar", "district_ar", "property_type_ar"])
    # Only land
    df = df[df["property_type_ar"].astype(str).str.contains(ONLY_LAND_PATTERN, na=False)]
    # Price band
    df = df[(df["price_per_sqm"] >= MIN_PRICE_PER_SQM) & (df["price_per_sqm"] <= MAX_PRICE_PER_SQM)]
    return df


def build_aggregated(df: pd.DataFrame) -> pd.DataFrame:
    """Group by (city_ar, district_ar, property_type_ar, year, quarter) and compute aggregates."""
    grp = df.groupby(["city_ar", "district_ar", "property_type_ar", "year", "quarter"], dropna=False)
    q1 = grp["price_per_sqm"].quantile(0.25)
    q3 = grp["price_per_sqm"].quantile(0.75)
    agg = grp["price_per_sqm"].agg(
        target_median_price_per_sqm="median",
        deals_count="size",
        std_price="std",
        min_price="min",
        max_price="max",
    ).reset_index()
    agg["iqr_price"] = (q3 - q1).reset_index(drop=True)
    agg["std_price"] = agg["std_price"].fillna(0)
    # Lagged median (same district, previous year) for market-cycle signal
    yearly = agg.groupby(["city_ar", "district_ar", "property_type_ar", "year"])["target_median_price_per_sqm"].median().reset_index()
    yearly = yearly.rename(columns={"target_median_price_per_sqm": "yearly_median"})
    yearly["prev_year"] = yearly["year"] + 1
    prev = yearly[["city_ar", "district_ar", "property_type_ar", "prev_year", "yearly_median"]].copy()
    prev = prev.rename(columns={"prev_year": "year", "yearly_median": "prev_year_median_price_per_sqm"})
    agg = agg.merge(prev, on=["city_ar", "district_ar", "property_type_ar", "year"], how="left")
    global_med = agg["target_median_price_per_sqm"].median()
    agg["prev_year_median_price_per_sqm"] = agg["prev_year_median_price_per_sqm"].fillna(global_med)
    return agg


def load_district_centroids() -> pd.DataFrame:
    """Load district centroids from district_centroids.json (same as train_price_model)."""
    if not DISTRICT_CENTROIDS_JSON.exists():
        return pd.DataFrame(columns=["city", "district", "latitude", "longitude"])
    with open(DISTRICT_CENTROIDS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    rows = []
    for r in data.get("centroids", []):
        city = (r.get("city") or "").strip()
        district = (r.get("district") or "").strip() or "_غير_محدد"
        lat, lon = r.get("latitude"), r.get("longitude")
        if not city or lat is None or lon is None:
            continue
        rows.append({"city": city, "district": district, "latitude": float(lat), "longitude": float(lon)})
    return pd.DataFrame(rows)


def merge_district_features(agg: pd.DataFrame) -> pd.DataFrame:
    """Attach lat/lon and OSM-style features at (city_ar, district_ar) level."""
    from models.osm_features import build_osm_features_table

    unique = agg[["city_ar", "district_ar"]].drop_duplicates().copy()
    unique["city"] = unique["city_ar"]
    unique["district"] = unique["district_ar"]

    centroids = load_district_centroids()
    if centroids.empty:
        unique["latitude"] = 26.3
        unique["longitude"] = 50.1
    else:
        unique = unique.merge(centroids, on=["city", "district"], how="left")
        unique["latitude"] = pd.to_numeric(unique["latitude"], errors="coerce").fillna(26.3)
        unique["longitude"] = pd.to_numeric(unique["longitude"], errors="coerce").fillna(50.1)

    pair_tuples = list(unique[["city", "district"]].drop_duplicates().itertuples(index=False, name=None))
    osm_df = build_osm_features_table(pair_tuples)
    if osm_df.empty:
        for c in OSM_DIST_COLS:
            unique[c] = 99.0
        for c in OSM_COUNT_COLS:
            unique[c] = 0
    else:
        unique = unique.merge(osm_df, on=["city", "district"], how="left")
        for c in OSM_DIST_COLS:
            unique[c] = pd.to_numeric(unique[c], errors="coerce").fillna(99.0)
        for c in OSM_COUNT_COLS:
            unique[c] = pd.to_numeric(unique[c], errors="coerce").fillna(0).astype(int)

    feature_cols = ["city_ar", "district_ar", "latitude", "longitude"] + OSM_DIST_COLS + OSM_COUNT_COLS
    district_features = unique[feature_cols].drop_duplicates(subset=["city_ar", "district_ar"])
    out = agg.merge(district_features, on=["city_ar", "district_ar"], how="left")
    return out


def add_rolling_baseline(agg: pd.DataFrame) -> pd.DataFrame:
    """Add rolling 4-quarter lagged median baseline (no leakage) and target_resid.

    - year_quarter_idx = year*4 + quarter, sort by [city_ar, district_ar, property_type_ar, year_quarter_idx]
    - baseline_roll4 = shift(1).rolling(4, min_periods=1).median() per (city, district, type)
    - fallback1: same rolling at (city_ar, property_type_ar); fallback2: global median
    - Adds: baseline_price_per_sqm, baseline_log, target_log, target_resid
    """
    agg = agg.copy()
    agg["year_quarter_idx"] = agg["year"].astype(int) * 4 + agg["quarter"].astype(int)
    agg = agg.sort_values(["city_ar", "district_ar", "property_type_ar", "year_quarter_idx"]).reset_index(drop=True)

    # Level 0: (city_ar, district_ar, property_type_ar) — shift(1) then rolling 4
    agg["baseline_roll4"] = agg.groupby(
        ["city_ar", "district_ar", "property_type_ar"], sort=False
    )["target_median_price_per_sqm"].transform(
        lambda s: s.shift(1).rolling(window=4, min_periods=1).median()
    )

    # Fallback1: rolling at (city_ar, property_type_ar)
    city_type_roll = agg.groupby(
        ["city_ar", "property_type_ar"], sort=False
    )["target_median_price_per_sqm"].transform(
        lambda s: s.shift(1).rolling(window=4, min_periods=1).median()
    )
    agg["baseline_roll4"] = agg["baseline_roll4"].fillna(city_type_roll)

    # Fallback2: global median
    global_med = agg["target_median_price_per_sqm"].median()
    agg["baseline_roll4"] = agg["baseline_roll4"].fillna(global_med)
    assert agg["baseline_roll4"].notna().all(), "baseline_roll4 must have no NaN"

    agg["baseline_price_per_sqm"] = agg["baseline_roll4"]
    agg["baseline_log"] = np.log1p(agg["baseline_price_per_sqm"])
    agg["target_log"] = np.log1p(agg["target_median_price_per_sqm"])
    agg["target_resid"] = agg["target_log"] - agg["baseline_log"]
    return agg


def main() -> None:
    print(f"Loading sales from {REAL_DATA_PATH}...")
    df = load_and_filter_sales()
    print(f"Filtered rows: {len(df):,} (land only, price_per_sqm in [{MIN_PRICE_PER_SQM}, {MAX_PRICE_PER_SQM}])")

    print("Building district-quarter aggregates...")
    agg = build_aggregated(df)
    print(f"Aggregated rows: {len(agg):,}")

    print("Merging district features (centroids + OSM/Google)...")
    agg = merge_district_features(agg)

    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    agg.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"Saved full table to {OUTPUT_PATH}")

    for md in MIN_DEALS_LIST:
        grp_md = agg[agg["deals_count"] >= md].copy()
        print(f"  min_deals>={md}: {len(grp_md):,} rows")
        grp_md = add_rolling_baseline(grp_md)
        path_md = FEATURES_DIR / f"district_quarter_md{md}.csv"
        grp_md.to_csv(path_md, index=False, encoding="utf-8-sig")
        print(f"  Saved to {path_md.name}")
        if md == MIN_DEALS_LIST[0]:
            grp_md.to_csv(OUTPUT_PATH_BASELINE, index=False, encoding="utf-8-sig")
            print(f"  (also {OUTPUT_PATH_BASELINE.name})")


if __name__ == "__main__":
    main()
