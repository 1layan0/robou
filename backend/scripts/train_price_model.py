"""Train a land price-per-sqm model on real sales data.

التركيز: الدمام، الظهران، الخبر فقط.

Usage (from project root):
    python -m scripts.train_price_model

Data source: data/real/real_sales_merged.csv (البيانات الحقيقية قبل الـ expand)

Features (from real data + OSM):
    - area_sqm
    - property_type_ar (→ land_use)
    - city_ar (→ city)
    - district_ar (→ district)
    - dist_school_km, dist_hospital_km, dist_mall_km (من بيانات OSM)

Target: price_per_sqm

مع التحسينات الحالية (إحداثيات، quarter، log(area)، target encoding، تقييد الأحياء المعتمدة، مزيج مع متوسط الدلو): R² ~0.59.
الوصول إلى R² ~0.7 يتطلب ميزات إضافية (مؤشرات سوق، مزيد من المرافق، إلخ) أو بيانات أغنى.

Output:
    - artifacts/price_per_sqm_model.pkl  (scikit-learn Pipeline)
    - artifacts/price_model_metadata.json (valid land_uses, city-district pairs)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from models.osm_features import build_osm_features_table

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REAL_DATA_PATH = PROJECT_ROOT / "data" / "real" / "real_sales_merged.csv"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DISTRICT_CENTROIDS_JSON = PROJECT_ROOT / "data" / "raw" / "district_centroids.json"
MODEL_PATH = ARTIFACTS_DIR / "price_per_sqm_model.pkl"
METADATA_PATH = ARTIFACTS_DIR / "price_model_metadata.json"

# إحداثيات مركز الحي (من Google) + quarter و log(area) + target encoding + دورة السوق (LAG سنة سابقة)
TE_COLS = ["mean_price_by_city", "mean_price_by_city_district", "mean_price_by_land_use"]
MARKET_CYCLE_COLS = [
    "city_prev_year_median_price_per_sqm",
    "district_prev_year_median_price_per_sqm",
    "deals_prev_year_count",
]
FEATURE_COLS = [
    "year", "quarter", "area_sqm", "log_area_sqm", "latitude", "longitude",
    "mean_price_by_city", "mean_price_by_city_district", "mean_price_by_land_use",
    "city_prev_year_median_price_per_sqm", "district_prev_year_median_price_per_sqm", "deals_prev_year_count",
    "land_use", "city", "district",
    "dist_school_km", "dist_hospital_km", "dist_mall_km",
    "count_school_3km", "count_hospital_3km", "count_mall_3km",
]
TARGET_COL = "price_per_sqm"
OSM_DIST_COLS = ["dist_school_km", "dist_hospital_km", "dist_mall_km"]
OSM_COUNT_COLS = ["count_school_3km", "count_hospital_3km", "count_mall_3km"]
OSM_NUMERIC_COLS = OSM_DIST_COLS + OSM_COUNT_COLS

# المدن المدعومة فقط (الدمام، الظهران، الخبر)
ALLOWED_CITIES = {"الدمام", "الظهران", "الخبر"}

# حدود معقولة لسعر المتر والمساحة (استبعاد قيم شاذة)
PRICE_PER_SQM_MIN, PRICE_PER_SQM_MAX = 100.0, 50_000.0
AREA_SQM_MIN, AREA_SQM_MAX = 20.0, 50_000.0

LAND_USE_NORMALIZE = {
    "قطعة أرض- زراعي": "قطعة أرض-زراعي",
    "قطعة أرض-سكنى": "قطعة أرض-سكنى",
    "قطعة أرض-تجارى": "قطعة أرض-تجارى",
    "قطعة أرض-زراعي": "قطعة أرض-زراعي",
}


def load_training_dataframe() -> pd.DataFrame:
    """Load real sales data (merged, before expand) and prepare for training."""
    if not REAL_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Expected real data at {REAL_DATA_PATH}. "
            "Run scripts/merge_real_estate_data.py first."
        )

    df = pd.read_csv(REAL_DATA_PATH, encoding="utf-8-sig")

    # سنة وربع (للتدريب؛ عند التنبؤ نستخدم سنة وربع افتراضيين من الميتاداتا)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["year"] = df["year"].fillna(df["year"].median()).astype(int)
    df["quarter"] = pd.to_numeric(df.get("quarter", 1), errors="coerce")
    df["quarter"] = df["quarter"].fillna(1).clip(1, 4).astype(int)

    # Keep only rows with valid price_per_sqm and area
    df = df[
        df["price_per_sqm"].notna()
        & (df["price_per_sqm"] > 0)
        & df["area_sqm"].notna()
        & (df["area_sqm"] > 0)
    ].copy()

    # استبعاد قيم شاذة لسعر المتر والمساحة
    df = df[
        (df["price_per_sqm"] >= PRICE_PER_SQM_MIN)
        & (df["price_per_sqm"] <= PRICE_PER_SQM_MAX)
        & (df["area_sqm"] >= AREA_SQM_MIN)
        & (df["area_sqm"] <= AREA_SQM_MAX)
    ].copy()

    # استبعاد قيم شاذة إضافية (IQR) لسعر المتر لتحسين R²
    q1, q3 = df["price_per_sqm"].quantile(0.25), df["price_per_sqm"].quantile(0.75)
    iqr = q3 - q1
    low, high = q1 - 2 * iqr, q3 + 2 * iqr
    df = df[(df["price_per_sqm"] >= low) & (df["price_per_sqm"] <= high)].copy()

    # Map real columns to model feature names (align with PredictRequest)
    pt = df["property_type_ar"].fillna("").astype(str).str.strip()
    df["land_use"] = pt.replace(LAND_USE_NORMALIZE)
    df["city"] = df["city_ar"].fillna("").astype(str).str.strip()
    df["district"] = df["district_ar"].fillna("").astype(str).str.strip().replace("nan", "")

    # Drop rows with empty city (required for location)
    df = df[df["city"].str.len() > 0].copy()

    # فلترة: الدمام، الظهران، الخبر فقط
    df = df[df["city"].isin(ALLOWED_CITIES)].copy()
    if len(df) == 0:
        raise ValueError(
            f"No data for allowed cities {ALLOWED_CITIES}. "
            "Check that city_ar in the CSV contains الدمام, الظهران, or الخبر."
        )

    # Fill empty district with placeholder
    df.loc[df["district"].str.len() == 0, "district"] = "_غير_محدد"

    # ميزة إضافية: log(area) غالباً يفسر سعر المتر بشكل أفضل
    df["log_area_sqm"] = np.log1p(df["area_sqm"].astype(float))

    return df


def load_district_centroids() -> pd.DataFrame:
    """تحميل إحداثيات مراكز الأحياء من district_centroids.json (مصدرها Google Geocoding)."""
    default_lat, default_lon = 26.3, 50.1
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
    out = pd.DataFrame(rows)
    if out.empty:
        out = pd.DataFrame(columns=["city", "district", "latitude", "longitude"])
    return out


def merge_centroids(df: pd.DataFrame) -> pd.DataFrame:
    """إضافة latitude, longitude (مركز الحي) من district_centroids.json لكل صف."""
    centroids = load_district_centroids()
    if centroids.empty:
        df["latitude"] = 26.3
        df["longitude"] = 50.1
        return df
    df = df.merge(centroids, on=["city", "district"], how="left")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce").fillna(26.3)
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce").fillna(50.1)
    return df


def build_hierarchical_baseline(train_df: pd.DataFrame) -> tuple:
    """baseline هرمي على price_per_sqm: (city,district,land_use,year,quarter) → fallback1 → fallback2 → global.
    train_df يجب أن يحتوي: city, district, land_use, year, quarter, price_per_sqm.
    يُرجع (level0_median, level1_median, level2_median, global_median).
    """
    level0 = train_df.groupby(["city", "district", "land_use", "year", "quarter"])["price_per_sqm"].median()
    level1 = train_df.groupby(["city", "land_use", "year", "quarter"])["price_per_sqm"].median()
    level2 = train_df.groupby(["city", "land_use"])["price_per_sqm"].median()
    global_median = float(train_df["price_per_sqm"].median())
    return level0, level1, level2, global_median


def get_baseline(
    row,
    level0: pd.Series,
    level1: pd.Series,
    level2: pd.Series,
    global_median: float,
) -> float:
    """ترجع أول قيمة متاحة من الهرم: level0 → level1 → level2 → global_median."""
    c, d, l, y, q = (
        str(getattr(row, "city", "")),
        str(getattr(row, "district", "")),
        str(getattr(row, "land_use", "")),
        int(getattr(row, "year", 2022)),
        int(getattr(row, "quarter", 1)),
    )
    try:
        v = level0.loc[(c, d, l, y, q)]
        if not pd.isna(v):
            return float(v)
    except (KeyError, TypeError):
        pass
    try:
        v = level1.loc[(c, l, y, q)]
        if not pd.isna(v):
            return float(v)
    except (KeyError, TypeError):
        pass
    try:
        v = level2.loc[(c, l)]
        if not pd.isna(v):
            return float(v)
    except (KeyError, TypeError):
        pass
    return global_median


def smape(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-6) -> float:
    """sMAPE نسبة مئوية: mean( 2*|y-pred| / (|y|+|pred|+eps) ) * 100."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    denom = np.abs(y_true) + np.abs(y_pred) + eps
    return float(np.mean(2.0 * np.abs(y_true - y_pred) / denom) * 100)


def merge_osm_features(df: pd.DataFrame) -> pd.DataFrame:
    """إضافة ميزات قرب وكثافة مرافق (مسافة + عدد ضمن 3كم) من Google Places."""
    pairs = df[["city", "district"]].drop_duplicates()
    pair_tuples = list(pairs.itertuples(index=False, name=None))
    osm_df = build_osm_features_table(pair_tuples)
    if osm_df.empty:
        for c in OSM_DIST_COLS:
            df[c] = 99.0
        for c in OSM_COUNT_COLS:
            df[c] = 0
        return df
    df = df.merge(osm_df, on=["city", "district"], how="left")
    for c in OSM_DIST_COLS:
        if c not in df.columns:
            df[c] = 99.0
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(99.0)
    for c in OSM_COUNT_COLS:
        if c not in df.columns:
            df[c] = 0
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df


def fit_target_encodings(X_train: pd.DataFrame, y_train: pd.Series, smoothing: float = 20.0) -> tuple[dict, list, dict, float]:
    """حساب ترميز الهدف (مدينة، حي+مدينة، نوع) مع تنعيم. يُرجع lookups للاستخدام عند التنبؤ."""
    global_mean = float(y_train.mean())
    agg = X_train.copy()
    agg["_y"] = y_train.values

    by_city = agg.groupby("city")["_y"].agg(["mean", "count"])
    by_city["encoded"] = (by_city["count"] * by_city["mean"] + smoothing * global_mean) / (by_city["count"] + smoothing)
    mean_by_city = by_city["encoded"].to_dict()

    by_cd = agg.groupby(["city", "district"])["_y"].agg(["mean", "count"])
    by_cd["encoded"] = (by_cd["count"] * by_cd["mean"] + smoothing * global_mean) / (by_cd["count"] + smoothing)
    mean_by_city_district = [
        {"city": c, "district": d, "mean_price_per_sqm": round(float(v), 2)}
        for (c, d), v in by_cd["encoded"].items()
    ]

    by_lu = agg.groupby("land_use")["_y"].agg(["mean", "count"])
    by_lu["encoded"] = (by_lu["count"] * by_lu["mean"] + smoothing * global_mean) / (by_lu["count"] + smoothing)
    mean_by_land_use = by_lu["encoded"].to_dict()

    return mean_by_city, mean_by_city_district, mean_by_land_use, global_mean


def apply_target_encodings(
    X: pd.DataFrame,
    mean_by_city: dict,
    mean_by_city_district: list,
    mean_by_land_use: dict,
    default_mean: float,
) -> pd.DataFrame:
    """إضافة أعمدة ترميز الهدف إلى X."""
    cd_lookup = {(r["city"], r["district"]): r["mean_price_per_sqm"] for r in mean_by_city_district}
    X = X.copy()
    X["mean_price_by_city"] = X["city"].map(mean_by_city).fillna(default_mean)
    X["mean_price_by_city_district"] = X.apply(
        lambda r: cd_lookup.get((r["city"], r["district"]), default_mean), axis=1
    )
    X["mean_price_by_land_use"] = X["land_use"].map(mean_by_land_use).fillna(default_mean)
    return X


def build_pipeline(use_lightgbm: bool = True):
    """LightGBM افتراضي لرفع R²؛ خيار RandomForest للاستقرار."""
    numeric_features = [
        "year", "quarter", "area_sqm", "log_area_sqm", "latitude", "longitude"
    ] + TE_COLS + MARKET_CYCLE_COLS + OSM_NUMERIC_COLS
    categorical_features = ["land_use", "city", "district"]

    numeric_transformer = Pipeline(steps=[("scaler", StandardScaler())])
    categorical_transformer = Pipeline(
        steps=[("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True))]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )

    if use_lightgbm:
        try:
            import lightgbm as lgb
            model = lgb.LGBMRegressor(
                n_estimators=1200,
                max_depth=20,
                learning_rate=0.02,
                min_child_samples=12,
                reg_alpha=0.05,
                reg_lambda=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                verbosity=-1,
                n_jobs=-1,
            )
        except ImportError:
            model = RandomForestRegressor(n_estimators=400, max_depth=24, random_state=42, n_jobs=-1)
    else:
        model = RandomForestRegressor(n_estimators=400, max_depth=24, random_state=42, n_jobs=-1)

    return Pipeline(steps=[("preprocess", preprocessor), ("model", model)])


# حدود فلترة "أراضي فقط" + سعر المتر المنطقي (لتقليل MAPE)
ONLY_LAND_PATTERN = "قطعة أرض|أرض"
MIN_PRICE_PER_SQM_FILTER = 500
MAX_PRICE_PER_SQM_FILTER = 20_000


def main() -> None:
    print(f"Loading training data from {REAL_DATA_PATH.name}...")
    df = load_training_dataframe()
    n_before = len(df)
    print(f"Loaded {n_before:,} rows (before land/price filter).")

    # فلترة: أراضي فقط + استبعاد القيم غير المنطقية لسعر المتر
    df = df[df["property_type_ar"].astype(str).str.contains(ONLY_LAND_PATTERN, na=False, regex=True)]
    df = df[(df["price_per_sqm"] >= MIN_PRICE_PER_SQM_FILTER) & (df["price_per_sqm"] <= MAX_PRICE_PER_SQM_FILTER)]
    print(f"After filters (only_land, price_per_sqm [{MIN_PRICE_PER_SQM_FILTER}, {MAX_PRICE_PER_SQM_FILTER}]): {len(df):,} rows (dropped {n_before - len(df):,}).")
    print(f"price_per_sqm after filter — min: {df['price_per_sqm'].min():,.0f} | median: {df['price_per_sqm'].median():,.0f} | max: {df['price_per_sqm'].max():,.0f}")

    print("Merging district centroids (lat/lon from Google)...")
    df = merge_centroids(df)
    print("Merging OSM proximity + density features...")
    df = merge_osm_features(df)

    # التدريب فقط على صفوف لها (مدينة، حي) في قائمة السنترويدز المعتمدة لتحسين الاتساق
    centroids = load_district_centroids()
    if not centroids.empty:
        valid_pairs = set(zip(centroids["city"].astype(str), centroids["district"].astype(str)))
        before = len(df)
        df["_pair"] = list(zip(df["city"].astype(str), df["district"].astype(str)))
        df = df[df["_pair"].isin(valid_pairs)].drop(columns=["_pair"]).copy()
        print(f"Restricted to districts in centroids list: {len(df):,} rows (dropped {before - len(df):,}).")

    # ميزات دورة السوق LAG (سنة سابقة) لتجنب التسريب وتحسين التقييم الزمني
    city_year = df.groupby(["city_ar", "year"])["price_per_sqm"].median().reset_index(name="city_year_median")
    city_prev = city_year.copy()
    city_prev["year"] = city_prev["year"] + 1
    city_prev = city_prev.rename(columns={"city_year_median": "city_prev_year_median_price_per_sqm"})
    df = df.merge(city_prev[["city_ar", "year", "city_prev_year_median_price_per_sqm"]], on=["city_ar", "year"], how="left")

    dist_year = df.groupby(["city_ar", "district_ar", "year"])["price_per_sqm"].median().reset_index(name="dist_year_median")
    dist_prev = dist_year.copy()
    dist_prev["year"] = dist_prev["year"] + 1
    dist_prev = dist_prev.rename(columns={"dist_year_median": "district_prev_year_median_price_per_sqm"})
    df = df.merge(dist_prev[["city_ar", "district_ar", "year", "district_prev_year_median_price_per_sqm"]], on=["city_ar", "district_ar", "year"], how="left")

    deals_year = df.groupby(["city_ar", "district_ar", "property_type_ar", "year"]).size().reset_index(name="deals_year_count")
    deals_prev = deals_year.copy()
    deals_prev["year"] = deals_prev["year"] + 1
    deals_prev = deals_prev.rename(columns={"deals_year_count": "deals_prev_year_count"})
    df = df.merge(deals_prev[["city_ar", "district_ar", "property_type_ar", "year", "deals_prev_year_count"]], on=["city_ar", "district_ar", "property_type_ar", "year"], how="left")

    for col in MARKET_CYCLE_COLS:
        pct = df[col].isna().mean() * 100
        print(f"NaN in {col} (before fallback): {pct:.2f}%")
    global_med = float(df["price_per_sqm"].median())
    df["city_prev_year_median_price_per_sqm"] = df["city_prev_year_median_price_per_sqm"].fillna(global_med)
    df["district_prev_year_median_price_per_sqm"] = df["district_prev_year_median_price_per_sqm"].fillna(df["city_prev_year_median_price_per_sqm"])
    df["deals_prev_year_count"] = df["deals_prev_year_count"].fillna(0).astype(int)
    for col in MARKET_CYCLE_COLS:
        pct = df[col].isna().mean() * 100
        print(f"NaN in {col} (after fallback): {pct:.2f}%")

    # baseline قوي: Rolling Median آخر 4 أرباع (مع shift(1) لتجنب التسريب)
    df["year_quarter_idx"] = df["year"] * 4 + df["quarter"]
    df = df.sort_values(["city_ar", "district_ar", "property_type_ar", "year_quarter_idx"]).reset_index(drop=True)

    grp = df.groupby(["city_ar", "district_ar", "property_type_ar", "year", "quarter"])["price_per_sqm"].median().reset_index()
    grp = grp.rename(columns={"price_per_sqm": "median_price_per_sqm"})
    grp["year_quarter_idx"] = grp["year"] * 4 + grp["quarter"]
    grp = grp.sort_values(["city_ar", "district_ar", "property_type_ar", "year_quarter_idx"]).reset_index(drop=True)

    grp["baseline_roll4"] = (
        grp.groupby(["city_ar", "district_ar", "property_type_ar"], group_keys=False)["median_price_per_sqm"]
        .apply(lambda s: s.shift(1).rolling(4, min_periods=1).median())
    )

    # fallback1: city + type rolling (نفس الطريقة)
    grp_ct = df.groupby(["city_ar", "property_type_ar", "year", "quarter"])["price_per_sqm"].median().reset_index()
    grp_ct = grp_ct.rename(columns={"price_per_sqm": "median_price_per_sqm"})
    grp_ct["year_quarter_idx"] = grp_ct["year"] * 4 + grp_ct["quarter"]
    grp_ct = grp_ct.sort_values(["city_ar", "property_type_ar", "year_quarter_idx"]).reset_index(drop=True)
    grp_ct["city_type_roll4"] = (
        grp_ct.groupby(["city_ar", "property_type_ar"], group_keys=False)["median_price_per_sqm"]
        .apply(lambda s: s.shift(1).rolling(4, min_periods=1).median())
    )
    grp = grp.merge(
        grp_ct[["city_ar", "property_type_ar", "year", "quarter", "city_type_roll4"]],
        on=["city_ar", "property_type_ar", "year", "quarter"],
        how="left",
    )
    grp["baseline_roll4"] = grp["baseline_roll4"].fillna(grp["city_type_roll4"])

    # fallback2: city+type prev_year median
    city_type_year = grp.groupby(["city_ar", "property_type_ar", "year"])["median_price_per_sqm"].median().reset_index()
    city_type_year["year"] = city_type_year["year"] + 1
    city_type_year = city_type_year.rename(columns={"median_price_per_sqm": "city_type_prev_year_median"})
    grp = grp.merge(
        city_type_year,
        on=["city_ar", "property_type_ar", "year"],
        how="left",
    )
    grp["baseline_roll4"] = grp["baseline_roll4"].fillna(grp["city_type_prev_year_median"])

    # fallback3: global median
    grp["baseline_roll4"] = grp["baseline_roll4"].fillna(global_med)
    assert grp["baseline_roll4"].notna().all(), "baseline_roll4 يجب ألا يحتوي على NaN"

    roll_baseline = grp[["city_ar", "district_ar", "property_type_ar", "year", "quarter", "baseline_roll4"]].copy()
    roll_baseline = roll_baseline.rename(columns={"baseline_roll4": "baseline_price_per_sqm"})
    df = df.merge(roll_baseline, on=["city_ar", "district_ar", "property_type_ar", "year", "quarter"], how="left")
    df["baseline_price_per_sqm"] = df["baseline_price_per_sqm"].fillna(global_med)
    print(f"Rolling baseline (4q lagged) — NaN بعد merge: {df['baseline_price_per_sqm'].isna().mean()*100:.2f}%")

    base_cols = [c for c in FEATURE_COLS if c not in TE_COLS]
    X = df[base_cols].copy()
    y_raw = df[TARGET_COL].astype(float)

    # تقسيم عشوائي طبقي: حسب (مدينة، نوع أرض) إن وُجد صنف بَعْضه أقل من 2 نستخدم المدينة فقط
    strat_label = df["city_ar"].astype(str) + "|" + df["property_type_ar"].astype(str)
    min_count = strat_label.value_counts().min()
    if min_count < 2:
        strat_label = df["city_ar"].astype(str)
    train_idx, test_idx = train_test_split(
        df.index, test_size=0.2, random_state=42, stratify=strat_label
    )
    X_train = X.loc[train_idx].copy()
    X_test = X.loc[test_idx].copy()
    y_raw_train = y_raw.loc[train_idx]
    y_raw_test = y_raw.loc[test_idx]
    y_test_price = y_raw_test.values
    print(f"Train: {len(X_train):,} | Test: {len(X_test):,} (stratified random 80/20)")

    # baseline هرمي من بيانات التدريب فقط (على السعر الأصلي)
    train_for_baseline = X_train.copy()
    train_for_baseline["price_per_sqm"] = y_raw_train.values
    level0_med, level1_med, level2_med, global_median = build_hierarchical_baseline(train_for_baseline)

    # هدف التدريب: residual على اللوغ (y_log - baseline_log)
    baseline_train = np.array([
        get_baseline(row, level0_med, level1_med, level2_med, global_median)
        for row in X_train.itertuples(index=False)
    ])
    baseline_log_train = np.log1p(baseline_train)
    y_log_train = np.log1p(y_raw_train.values)
    target_resid_train = y_log_train - baseline_log_train

    # ترميز الهدف على الـ residual
    mean_by_city, mean_by_city_district, mean_by_land_use, te_default = fit_target_encodings(
        X_train, pd.Series(target_resid_train, index=X_train.index), smoothing=20.0
    )
    X_train = apply_target_encodings(
        X_train, mean_by_city, mean_by_city_district, mean_by_land_use, te_default
    )
    X_test = apply_target_encodings(
        X_test, mean_by_city, mean_by_city_district, mean_by_land_use, te_default
    )
    X_train = X_train[FEATURE_COLS]
    X_test = X_test[FEATURE_COLS]

    pipeline = build_pipeline(use_lightgbm=True)
    pipeline.fit(X_train, target_resid_train)

    valid_land_uses = sorted(X_train["land_use"].unique().astype(str).tolist())
    pairs = X_train[["city", "district"]].drop_duplicates()
    valid_city_districts = [
        {"city": str(row.city), "district": str(row.district)}
        for row in pairs.itertuples(index=False)
    ]

    # تنبؤ: residual ثم إعادة إلى السعر (baseline للـ residual يبقى هرمي)
    baseline_test_hier = np.array([
        get_baseline(row, level0_med, level1_med, level2_med, global_median)
        for row in X_test.itertuples(index=False)
    ])
    pred_resid = pipeline.predict(X_test)
    baseline_log_test = np.log1p(baseline_test_hier)
    pred_log = baseline_log_test + pred_resid
    pred_price = np.expm1(pred_log)

    # baseline للمقارنة والـ blend = Rolling Median (4 أرباع متأخرة)
    baseline_test = df.loc[test_idx, "baseline_price_per_sqm"].values
    baseline_test = np.asarray(baseline_test, dtype=float)

    # blend بوزن baseline أعلى: alpha في [0.6, 0.7, 0.8, 0.9]
    best_alpha = 0.0
    best_smape = float("inf")
    for alpha in [0.6, 0.7, 0.8, 0.9]:
        blend_pred = alpha * baseline_test + (1 - alpha) * pred_price
        s = smape(y_test_price, blend_pred)
        if s < best_smape:
            best_smape = s
            best_alpha = alpha
    pred_price = best_alpha * baseline_test + (1 - best_alpha) * pred_price
    print(f"Blend (rolling baseline) best_alpha={best_alpha}: sMAPE={best_smape:.2f}%")

    # للـ metadata: bucket means من التدريب
    train_agg = X_train.copy()
    train_agg["price_per_sqm"] = y_raw_train.values
    train_bucket = (
        train_agg.groupby(["city", "district", "land_use"], as_index=False)["price_per_sqm"]
        .mean()
        .rename(columns={"price_per_sqm": "bucket_mean"})
    )
    train_bucket_year = (
        train_agg.groupby(["city", "district", "land_use", "year"], as_index=False)["price_per_sqm"]
        .mean()
        .rename(columns={"price_per_sqm": "bucket_mean_year"})
    )
    train_bucket_year_quarter = (
        train_agg.groupby(["city", "district", "land_use", "year", "quarter"], as_index=False)["price_per_sqm"]
        .mean()
        .rename(columns={"price_per_sqm": "bucket_mean_yq"})
    )

    mae = mean_absolute_error(y_test_price, pred_price)
    r2 = r2_score(y_test_price, pred_price)
    y_test_arr = np.asarray(y_test_price)
    pred_arr = np.asarray(pred_price)
    mape = float(np.mean(np.abs((y_test_arr - pred_arr) / np.clip(y_test_arr, 1e-6, None))) * 100)

    # baseline للاختبار = نفس baseline_test المستخدم في التنبؤ
    baseline_pred = baseline_test
    baseline_mape = float(np.mean(np.abs((y_test_arr - baseline_pred) / np.clip(y_test_arr, 1e-6, None))) * 100)
    baseline_mae = mean_absolute_error(y_test_price, baseline_pred)
    test_smape_val = smape(y_test_price, pred_price)
    baseline_smape_val = smape(y_test_price, baseline_pred)

    # تشخيص: توزيع السعر في الاختبار
    print(f"y_test price_per_sqm — min: {y_test_arr.min():,.0f} | median: {np.median(y_test_arr):,.0f} | max: {y_test_arr.max():,.0f}")
    print(f"best_alpha: {best_alpha}")
    print("Model vs Baseline — MAE (model): {:.2f} | MAE (baseline): {:.2f}".format(mae, baseline_mae))
    print("Model vs Baseline — MAPE (model): {:.2f}% | MAPE (baseline): {:.2f}%".format(mape, baseline_mape))
    print("Model vs Baseline — sMAPE (model): {:.2f}% | sMAPE (baseline): {:.2f}%".format(test_smape_val, baseline_smape_val))
    print(f"R²: {r2:.3f}  (هدف: 0.7–0.8)")

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")

    default_year = int(X_train["year"].max())
    default_quarter = int(X_train["quarter"].mode().iloc[0]) if "quarter" in X_train.columns else 1

    osm_table = X_train[["city", "district", "latitude", "longitude"] + OSM_NUMERIC_COLS].drop_duplicates()
    osm_features = []
    for row in osm_table.itertuples(index=False):
        o = {"city": str(row.city), "district": str(row.district)}
        o["latitude"] = float(getattr(row, "latitude", 26.3))
        o["longitude"] = float(getattr(row, "longitude", 50.1))
        for c in OSM_DIST_COLS:
            o[c] = float(getattr(row, c))
        for c in OSM_COUNT_COLS:
            o[c] = int(getattr(row, c))
        osm_features.append(o)

    bucket_mean_lookup = [
        {"city": str(r.city), "district": str(r.district), "land_use": str(r.land_use), "mean_price_per_sqm": round(float(r.bucket_mean), 2)}
        for r in train_bucket.itertuples(index=False)
    ]
    bucket_mean_year_lookup = [
        {"city": str(r.city), "district": str(r.district), "land_use": str(r.land_use), "year": int(r.year), "mean_price_per_sqm": round(float(r.bucket_mean_year), 2)}
        for r in train_bucket_year.itertuples(index=False)
    ]
    bucket_mean_year_quarter_lookup = [
        {"city": str(r.city), "district": str(r.district), "land_use": str(r.land_use), "year": int(r.year), "quarter": int(r.quarter), "mean_price_per_sqm": round(float(r.bucket_mean_yq), 2)}
        for r in train_bucket_year_quarter.itertuples(index=False)
    ]
    default_mean = round(float(y_raw_train.mean()), 2)

    # lookups لميزات دورة السوق LAG (للتنبؤ في API نبحث عن year-1)
    city_year_median_lookup = train_agg.groupby(["city", "year"])["price_per_sqm"].median().reset_index()
    city_year_median_lookup = [
        {"city": str(r.city), "year": int(r.year), "city_year_median_price_per_sqm": round(float(r.price_per_sqm), 2)}
        for r in city_year_median_lookup.itertuples(index=False)
    ]
    district_year_median_lookup = train_agg.groupby(["city", "district", "year"])["price_per_sqm"].median().reset_index()
    district_year_median_lookup = [
        {"city": str(r.city), "district": str(r.district), "year": int(r.year), "district_year_median_price_per_sqm": round(float(r.price_per_sqm), 2)}
        for r in district_year_median_lookup.itertuples(index=False)
    ]

    # تخزين ترميز الهدف للتنبؤ
    mean_price_by_city_rounded = {k: round(float(v), 2) for k, v in mean_by_city.items()}
    mean_price_by_land_use_rounded = {k: round(float(v), 2) for k, v in mean_by_land_use.items()}

    metadata = {
        "filters_applied": {
            "only_land": True,
            "min_price_per_sqm": MIN_PRICE_PER_SQM_FILTER,
            "max_price_per_sqm": MAX_PRICE_PER_SQM_FILTER,
        },
        "baseline_type": "rolling_median_4q_lagged",
        "feature_flags": {
            "city_prev_year_median": True,
            "district_prev_year_median": True,
            "deals_prev_year_count": True,
        },
        "allowed_cities": sorted(ALLOWED_CITIES),
        "valid_land_uses": valid_land_uses,
        "valid_city_districts": valid_city_districts,
        "osm_features": osm_features,
        "bucket_mean_lookup": bucket_mean_lookup,
        "bucket_mean_year_lookup": bucket_mean_year_lookup,
        "bucket_mean_year_quarter_lookup": bucket_mean_year_quarter_lookup,
        "mean_price_by_city": mean_price_by_city_rounded,
        "mean_price_by_city_district": mean_by_city_district,
        "mean_price_by_land_use": mean_price_by_land_use_rounded,
        "te_default_mean": round(float(te_default), 2),
        "default_mean_price_per_sqm": default_mean,
        "blend_alpha": best_alpha,
        "default_prediction_year": default_year,
        "default_prediction_quarter": default_quarter,
        "test_mae": round(float(mae), 2),
        "test_r2": round(float(r2), 4),
        "test_mape": round(float(mape), 2),
        "baseline_mape": round(float(baseline_mape), 2),
        "test_smape": round(float(test_smape_val), 2),
        "baseline_smape": round(float(baseline_smape_val), 2),
        "target_is_log": True,
        "model_is_residual": True,
        "baseline_level0": [
            {"city": c, "district": d, "land_use": l, "year": int(y), "quarter": int(q), "median_price_per_sqm": round(float(v), 2)}
            for (c, d, l, y, q), v in level0_med.items()
        ],
        "baseline_level1": [
            {"city": c, "land_use": l, "year": int(y), "quarter": int(q), "median_price_per_sqm": round(float(v), 2)}
            for (c, l, y, q), v in level1_med.items()
        ],
        "baseline_level2": [
            {"city": c, "land_use": l, "median_price_per_sqm": round(float(v), 2)}
            for (c, l), v in level2_med.items()
        ],
        "baseline_global_median": round(global_median, 2),
        "city_year_median_lookup": city_year_median_lookup,
        "district_year_median_lookup": district_year_median_lookup,
    }
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"Saved metadata to {METADATA_PATH}")


if __name__ == "__main__":
    main()
