"""Build district-quarter aggregated dataset for the aggregated price model.

- Reads: data/real/real_sales_merged.csv
- Filters: only land (property_type_ar contains قطعة أرض), price_per_sqm in [500, 20000]
- Maps raw (city_ar, district_ar) to whitelist (district_centroids.json); drops unmapped rows
- Groupby: city_ar, district_ar, property_type_ar, year, quarter
- Aggregates: target_median_price_per_sqm, deals_count, iqr_price, std_price, min_price, max_price
- Merges district-level features (centroids + Google Places) on (city_ar, district_ar)
- Output: data/features/district_quarter_dataset.csv

Run from project root: python scripts/build_district_quarter_dataset.py
"""
from __future__ import annotations

import json
import re
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
DISTRICT_GROWTH_YOY_CSV = FEATURES_DIR / "district_growth_yoy.csv"
CITY_GROWTH_YOY_CSV = FEATURES_DIR / "city_growth_yoy.csv"

# قيم min_deals للتجربة التلقائية (جودة الوسيط)
MIN_DEALS_LIST = [2, 3, 4, 5, 7, 10]
PLACE_DIST_COLS = ["dist_school_km", "dist_hospital_km", "dist_mall_km"]
PLACE_COUNT_COLS = ["count_school_3km", "count_hospital_3km", "count_mall_3km"]

ONLY_LAND_PATTERN = "قطعة أرض"
MIN_PRICE_PER_SQM = 500
MAX_PRICE_PER_SQM = 20_000

# أحياء نستبعدها من التعيين (لا نربطها بأي حي رسمي)
SKIP_DISTRICT_SUBSTRINGS = ("أخرى", "بدون", "ش خ ", "ش.خ ", "ش د ", "ش.د ", "/ ش", "ش د", "38/", "43/", "489/")

# تعيين أسماء خام → اسم رسمي (للحي فقط)
DISTRICT_ALIASES: dict[str, str] = {
    "البحيره": "البحيرة",
    "الحزام الاخضر": "الحزام الأخضر",
    "اشبيليا": "إشبيلية",
    "الامواج": "الأمواج",
    "احد": "أحد",
    "الاثير": "الأثير",
    "العدامه": "العدامة",
    "الشعله": "الشعلة",
    "العزيزيه": "العزيزية",
    "الصوارى": "الصواري",
    "الراكه": "الراكة",
}


def load_whitelist() -> frozenset[tuple[str, str]]:
    """قائمة (مدينة، حي) الرسمية من district_centroids.json."""
    if not DISTRICT_CENTROIDS_JSON.exists():
        return frozenset()
    with open(DISTRICT_CENTROIDS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    out: set[tuple[str, str]] = set()
    for r in data.get("centroids", []):
        city = (r.get("city") or "").strip()
        district = (r.get("district") or "").strip() or "_غير_محدد"
        if not city or r.get("latitude") is None or r.get("longitude") is None:
            continue
        out.add((city, district))
    return frozenset(out)


def _normalize_district_for_mapping(district: str) -> str:
    """توحيد كتابة الحي للتعيين."""
    s = (district or "").strip()
    if not s:
        return s
    if s.endswith("شمالي"):
        s = s[:-5] + "الشمالية"
    elif s.endswith("جنوبي"):
        s = s[:-5] + "الجنوبية"
    s = s.replace(" شمالي", " الشمالية").replace(" جنوبي", " الجنوبية")
    return s.strip()


def _strip_city_prefix(district: str, city: str) -> str:
    """إزالة بادئة 'مدينة/ ' من اسم الحي."""
    s = (district or "").strip()
    for prefix in ("الخبر/ ", "الدمام/ ", "الظهران/ ", "الخبر/", "الدمام/", "الظهران/"):
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
            break
    return s


def _should_skip_district(district: str) -> bool:
    """True إذا كان الحي من النوع الذي نستبعده."""
    d = (district or "").strip()
    if not d or len(d) < 2:
        return True
    for skip in SKIP_DISTRICT_SUBSTRINGS:
        if skip in d:
            return True
    if re.match(r"^\d+\s*/\s*\d+", d):
        return True
    return False


def build_raw_to_canonical_mapping(
    unique_pairs: list[tuple[str, str]],
    whitelist: frozenset[tuple[str, str]],
) -> dict[tuple[str, str], tuple[str, str]]:
    """تعيين (مدينة، حي خام) → (مدينة، حي رسمي) من الوايت لست."""
    mapping: dict[tuple[str, str], tuple[str, str]] = {}
    for city, district in unique_pairs:
        city = (city or "").strip()
        district = (district or "").strip()
        if not city or not district:
            continue
        if _should_skip_district(district):
            continue
        key = (city, district)
        if key in whitelist:
            mapping[key] = key
            continue
        d_stripped = _strip_city_prefix(district, city)
        if d_stripped and (city, d_stripped) in whitelist:
            mapping[key] = (city, d_stripped)
            continue
        d_norm = _normalize_district_for_mapping(d_stripped if d_stripped else district)
        if d_norm and (city, d_norm) in whitelist:
            mapping[key] = (city, d_norm)
            continue
        d_lower = (d_norm or district).replace(" ", "")
        for raw, canonical in DISTRICT_ALIASES.items():
            if raw.replace(" ", "") == d_lower and (city, canonical) in whitelist:
                mapping[key] = (city, canonical)
                break
        else:
            d_clean = (d_norm or district).strip()
            if (city, d_clean) in whitelist:
                mapping[key] = (city, d_clean)
    return mapping


def apply_whitelist_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """تعيين (city_ar, district_ar) إلى الأحياء الرسمية وحذف الصفوف غير القابلة للتعيين."""
    whitelist = load_whitelist()
    if not whitelist:
        print("Warning: no whitelist (district_centroids.json). Skipping mapping.")
        return df
    unique = df[["city_ar", "district_ar"]].drop_duplicates()
    pairs = list(unique.itertuples(index=False, name=None))
    raw_to_canonical = build_raw_to_canonical_mapping(pairs, whitelist)
    def map_row(row: pd.Series) -> tuple[str, str] | None:
        c, d = (row["city_ar"] or "").strip(), (row["district_ar"] or "").strip()
        return raw_to_canonical.get((c, d))

    df = df.copy()
    mapped = df.apply(map_row, axis=1)
    df["_canonical"] = mapped
    before = len(df)
    df = df[df["_canonical"].notna()].copy()
    df["city_ar"] = df["_canonical"].apply(lambda x: x[0])
    df["district_ar"] = df["_canonical"].apply(lambda x: x[1])
    df = df.drop(columns=["_canonical"])
    dropped = before - len(df)
    if dropped > 0:
        print(f"Whitelist mapping: dropped {dropped:,} rows (no canonical district); kept {len(df):,} rows.")
    return df


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
    """Load district centroids from district_centroids.json (same format as elsewhere)."""
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
    """Attach lat/lon and Google Places proximity features at (city_ar, district_ar) level."""
    from models.place_features import build_place_features_table

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
    place_df = build_place_features_table(pair_tuples)
    if place_df.empty:
        for c in PLACE_DIST_COLS:
            unique[c] = 99.0
        for c in PLACE_COUNT_COLS:
            unique[c] = 0
    else:
        unique = unique.merge(place_df, on=["city", "district"], how="left")
        for c in PLACE_DIST_COLS:
            unique[c] = pd.to_numeric(unique[c], errors="coerce").fillna(99.0)
        for c in PLACE_COUNT_COLS:
            unique[c] = pd.to_numeric(unique[c], errors="coerce").fillna(0).astype(int)

    feature_cols = ["city_ar", "district_ar", "latitude", "longitude"] + PLACE_DIST_COLS + PLACE_COUNT_COLS
    district_features = unique[feature_cols].drop_duplicates(subset=["city_ar", "district_ar"])
    out = agg.merge(district_features, on=["city_ar", "district_ar"], how="left")
    return out


def add_growth_and_quarter_features(agg: pd.DataFrame) -> pd.DataFrame:
    """Add growth_pct (district then city fallback) and cyclic quarter_sin/quarter_cos."""
    agg = agg.copy()
    # نمو على مستوى (مدينة، حي، نوع): من district_growth_yoy
    if DISTRICT_GROWTH_YOY_CSV.exists():
        dg = pd.read_csv(DISTRICT_GROWTH_YOY_CSV, encoding="utf-8-sig")
        if "growth_pct" in dg.columns and all(c in dg.columns for c in ["city_ar", "district_ar", "property_type_ar"]):
            dg = dg[["city_ar", "district_ar", "property_type_ar", "growth_pct"]].drop_duplicates(
                subset=["city_ar", "district_ar", "property_type_ar"], keep="first"
            )
            dg["growth_pct"] = pd.to_numeric(dg["growth_pct"], errors="coerce")
            agg = agg.merge(dg, on=["city_ar", "district_ar", "property_type_ar"], how="left")
    if "growth_pct" not in agg.columns:
        agg["growth_pct"] = np.nan
    # تعبئة من مستوى المدينة: city_growth_yoy
    if CITY_GROWTH_YOY_CSV.exists():
        cg = pd.read_csv(CITY_GROWTH_YOY_CSV, encoding="utf-8-sig")
        for col in ["yoy_growth_3y_avg_pct", "yoy_growth_last_year_pct"]:
            if col in cg.columns:
                cg[col] = pd.to_numeric(cg[col], errors="coerce")
        if "yoy_growth_3y_avg_pct" in cg.columns:
            cg["city_growth_pct"] = cg["yoy_growth_3y_avg_pct"].fillna(cg.get("yoy_growth_last_year_pct", pd.Series(dtype=float)))
        elif "yoy_growth_last_year_pct" in cg.columns:
            cg["city_growth_pct"] = cg["yoy_growth_last_year_pct"]
        else:
            cg["city_growth_pct"] = np.nan
        if "city_growth_pct" in cg.columns and "property_type_ar" in cg.columns:
            cg = cg[["city_ar", "property_type_ar", "city_growth_pct"]].drop_duplicates(
                subset=["city_ar", "property_type_ar"], keep="first"
            )
            agg = agg.merge(cg, on=["city_ar", "property_type_ar"], how="left")
            agg["growth_pct"] = agg["growth_pct"].fillna(agg["city_growth_pct"])
            agg = agg.drop(columns=["city_growth_pct"], errors="ignore")
    agg["growth_pct"] = pd.to_numeric(agg["growth_pct"], errors="coerce").fillna(0.0)
    # ربع دوري (0..3) → sin/cos
    q = agg["quarter"].astype(int).clip(1, 4)
    agg["quarter_sin"] = np.sin(2.0 * np.pi * (q - 1) / 4.0)
    agg["quarter_cos"] = np.cos(2.0 * np.pi * (q - 1) / 4.0)
    return agg


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

    WINDOW = 4
    # Level 0: (city_ar, district_ar, property_type_ar) — shift(1) then rolling 4
    agg["baseline_roll4"] = agg.groupby(
        ["city_ar", "district_ar", "property_type_ar"], sort=False
    )["target_median_price_per_sqm"].transform(
        lambda s: s.shift(1).rolling(window=WINDOW, min_periods=1).median()
    )

    # Fallback1: rolling at (city_ar, property_type_ar)
    city_type_roll = agg.groupby(
        ["city_ar", "property_type_ar"], sort=False
    )["target_median_price_per_sqm"].transform(
        lambda s: s.shift(1).rolling(window=WINDOW, min_periods=1).median()
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

    print("Applying whitelist mapping (raw → canonical districts)...")
    df = apply_whitelist_mapping(df)
    if len(df) == 0:
        raise SystemExit("No rows left after whitelist mapping. Check district_centroids.json and data.")

    print("Building district-quarter aggregates...")
    agg = build_aggregated(df)
    print(f"Aggregated rows: {len(agg):,}")

    print("Merging district features (centroids + Google Places)...")
    agg = merge_district_features(agg)
    print("Adding growth_pct and quarter_sin/quarter_cos...")
    agg = add_growth_and_quarter_features(agg)

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
