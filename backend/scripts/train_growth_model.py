"""Train annual growth model — كل البيانات، ميزات زمنية وسوقية، تدريب على آلاف الصفوف.

- المصادر: real_sales_merged (٢٠١٦–٢٠٢٦) + quarter_report إن وُجد.
- التدريب على كل صفوف النمو (~4k) مع ميزات: سنة، قرب مرافق، عدد صفقات، متوسط سعر السنة السابقة.
- تقييم: Cross-validation + تقسيمة زمنية. مقارنة RF، LightGBM، XGBoost، Ridge واختيار الأفضل.

Usage (from project root):
    python -m scripts.train_growth_model
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.base import clone
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from models.osm_features import build_osm_features_table

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REAL_SALES_MERGED_PATH = PROJECT_ROOT / "data" / "real" / "real_sales_merged.csv"
REAL_SALES_2016_2023_PATH = PROJECT_ROOT / "data" / "real" / "real_sales_2016_2023_only.csv"
QUARTER_REPORT_PATH = PROJECT_ROOT / "data" / "real" / "quarter_report_si.csv"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "growth_model.pkl"
METADATA_PATH = ARTIFACTS_DIR / "growth_model_metadata.json"

ALLOWED_CITIES = {"الدمام", "الظهران", "الخبر"}
TARGET_COL = "growth_rate"
RESIDUAL_COL = "growth_residual"  # growth_rate - baseline_growth (الهدف بعد التغيير الجذري)
MIN_YEARS_PER_TRIPLET = 3  # استبعاد تراكيب لها أقل من 3 سنوات بيانات
GROWTH_WINSORIZE = (-0.20, 0.30)  # قص النمو الشاذ
OSM_NUMERIC_COLS = [
    "dist_school_km", "dist_hospital_km", "dist_mall_km",
    "count_school_3km", "count_hospital_3km", "count_mall_3km",
]

LAND_USE_NORMALIZE = {
    "قطعة أرض- زراعي": "قطعة أرض-زراعي",
    "قطعة أرض-سكنى": "قطعة أرض-سكنى",
    "قطعة أرض-تجارى": "قطعة أرض-تجارى",
    "قطعة أرض-زراعي": "قطعة أرض-زراعي",
    "أخرى": "أخرى",
    "شقة": "شقة",
    "فيلا": "فيلا",
    "عمارة": "عمارة",
}
EASTERN_REGION_VARIANTS = {"المنطقة الشرقية", "منطقة الشرقية", "الشرقية"}


def load_raw_for_growth(path: Path) -> pd.DataFrame:
    """تحميل صفقات مع deed_count إن وُجد، فلترة الشرقية والمدن الثلاث."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["price_per_sqm"] = pd.to_numeric(df["price_per_sqm"], errors="coerce")
    df["city_ar"] = df["city_ar"].fillna("").astype(str).str.strip()
    df["district_ar"] = df["district_ar"].fillna("").astype(str).str.strip().replace("nan", "")
    if "property_type_ar" in df.columns:
        df["type_category_ar"] = df["property_type_ar"].fillna("").astype(str).str.strip()
    elif "type_category_ar" not in df.columns:
        df["type_category_ar"] = ""
    if "deed_count" in df.columns:
        df["deed_count"] = pd.to_numeric(df["deed_count"], errors="coerce").fillna(1)
    else:
        df["deed_count"] = 1

    if "region_ar" in df.columns:
        df = df[df["region_ar"].astype(str).str.strip().isin(EASTERN_REGION_VARIANTS)].copy()
    df = df[df["city_ar"].isin(ALLOWED_CITIES)].copy()
    df = df[df["price_per_sqm"].notna() & (df["price_per_sqm"] > 0)].copy()
    return df


def build_market_agg(df: pd.DataFrame) -> pd.DataFrame:
    """(سنة، مدينة، حي، نوع) → متوسط سعر المتر، مجموع عدد الصفقات."""
    df = df.copy()
    df["land_use"] = df["type_category_ar"].replace(LAND_USE_NORMALIZE)
    df["city"] = df["city_ar"]
    df["district"] = df["district_ar"].replace("", "_غير_محدد")
    agg = (
        df.groupby(["year", "city", "district", "land_use"], as_index=False)
        .agg(
            avg_price_per_sqm=("price_per_sqm", "mean"),
            deed_count=("deed_count", "sum"),
        )
    )
    return agg


def build_growth_target_with_features(market_agg: pd.DataFrame) -> pd.DataFrame:
    """نمو سنوي + lagged + baseline + سيولة + تقلب + نمو مدينة/منطقة + نمو تراكمي 2س + ميل الاتجاه السعري."""
    market_agg = market_agg.sort_values(["city", "district", "land_use", "year"])
    rows = []
    for (city, district, land_use), sub in market_agg.groupby(["city", "district", "land_use"]):
        sub = sub.sort_values("year")
        if len(sub) < MIN_YEARS_PER_TRIPLET:
            continue
        years = sub["year"].values
        prices = sub["avg_price_per_sqm"].values
        deeds = sub["deed_count"].values
        year_to_price = dict(zip(years.astype(int), prices))
        for i in range(len(sub) - 1):
            r0, r1 = sub.iloc[i], sub.iloc[i + 1]
            p0, p1 = r0["avg_price_per_sqm"], r1["avg_price_per_sqm"]
            if p0 <= 0:
                continue
            y0 = int(r0["year"])
            growth = (p1 - p0) / p0
            # سيولة: مجموع صفقات السنتين السابقتين
            mask_2y = (years >= y0 - 2) & (years < y0)
            liquidity_2y = int(np.sum(deeds[mask_2y])) if np.any(mask_2y) else int(r0["deed_count"]) if not pd.isna(r0["deed_count"]) else 0
            # تقلب سعر
            mask_vol = years <= y0
            vol = float(np.nanstd(prices[mask_vol])) if np.sum(mask_vol) >= 2 else 0.0
            # نمو تراكمي سنتين: (سعر y0 - سعر y0-2) / سعر y0-2
            p_2y = year_to_price.get(y0 - 2)
            growth_2y = (p0 - p_2y) / p_2y if (p_2y and p_2y > 0) else np.nan
            # ميل الاتجاه السعري: انحدار خطي لسعر المتر على آخر 3 سنوات (حتى y0)، معادلته سنوية → نقسم على متوسط السعر ليكون بمقياس قريب من النمو السنوي
            mask_trend = (years >= y0 - 2) & (years <= y0)
            y_sub = years[mask_trend]
            p_sub = prices[mask_trend]
            if len(y_sub) >= 2:
                slope = float(np.polyfit(y_sub, p_sub, 1)[0])
                mean_p = float(np.mean(p_sub))
                price_trend_slope = (slope / mean_p) if mean_p > 0 else 0.0
            else:
                price_trend_slope = np.nan
            rows.append({
                "city": city,
                "district": district,
                "land_use": land_use,
                "year_start": y0,
                "growth_rate": growth,
                "avg_price_prev": p0,
                "deed_count_prev": int(r0["deed_count"]) if not pd.isna(r0["deed_count"]) else 0,
                "liquidity_2y": liquidity_2y,
                "price_volatility": vol,
                "growth_2y": growth_2y,
                "price_trend_slope": price_trend_slope,
            })
    if not rows:
        raise ValueError("No growth target computed. Check data has enough years.")
    df = pd.DataFrame(rows)
    df["growth_rate"] = df["growth_rate"].clip(lower=GROWTH_WINSORIZE[0], upper=GROWTH_WINSORIZE[1])
    baseline = df.groupby(["city", "district", "land_use"], as_index=False)["growth_rate"].mean().rename(
        columns={"growth_rate": "baseline_growth"}
    )
    df = df.merge(baseline, on=["city", "district", "land_use"], how="left")
    df = df.sort_values(["city", "district", "land_use", "year_start"])
    df["lagged_growth"] = np.nan
    for (city, district, land_use), g in df.groupby(["city", "district", "land_use"]):
        idx = g.index
        if len(idx) < 2:
            continue
        df.loc[idx[1:], "lagged_growth"] = g["growth_rate"].values[:-1]
    df["lagged_growth"] = df["lagged_growth"].fillna(df["growth_rate"].median())
    # نمو المدينة في نفس السنة
    city_year_avg = df.groupby(["city", "year_start"], as_index=False)["growth_rate"].mean().rename(
        columns={"growth_rate": "city_avg_growth"}
    )
    df = df.merge(city_year_avg, on=["city", "year_start"], how="left")
    df["city_avg_growth"] = df["city_avg_growth"].fillna(df["growth_rate"].median())
    # نمو المنطقة (كل الشرقية) في نفس السنة
    region_year_avg = df.groupby("year_start", as_index=False)["growth_rate"].mean().rename(
        columns={"growth_rate": "region_avg_growth"}
    )
    df = df.merge(region_year_avg, on="year_start", how="left")
    df["region_avg_growth"] = df["region_avg_growth"].fillna(df["growth_rate"].median())
    # تعبئة growth_2y و price_trend_slope
    df["growth_2y"] = df["growth_2y"].clip(lower=-0.25, upper=0.35).fillna(df["growth_rate"].median())
    df["price_trend_slope"] = df["price_trend_slope"].clip(lower=-0.15, upper=0.25).fillna(0.0)
    return df


def load_all_sources_as_market_agg() -> pd.DataFrame:
    """إرجاع market_agg موحّد من كل المصادر."""
    parts = []
    if REAL_SALES_MERGED_PATH.exists():
        raw = load_raw_for_growth(REAL_SALES_MERGED_PATH)
        parts.append(build_market_agg(raw))
    elif REAL_SALES_2016_2023_PATH.exists():
        raw = load_raw_for_growth(REAL_SALES_2016_2023_PATH)
        parts.append(build_market_agg(raw))
    if QUARTER_REPORT_PATH.exists():
        qr = pd.read_csv(QUARTER_REPORT_PATH, encoding="utf-8-sig")
        qr["year"] = pd.to_numeric(qr["year"], errors="coerce")
        qr["price_per_sqm"] = pd.to_numeric(qr["price_per_sqm"], errors="coerce")
        qr["city_ar"] = qr["city_ar"].fillna("").astype(str).str.strip()
        qr["district_ar"] = qr["district_ar"].fillna("").astype(str).str.strip().replace("nan", "")
        qr["type_category_ar"] = qr["type_category_ar"].fillna("").astype(str).str.strip()
        qr = qr[qr["region_ar"] == "المنطقة الشرقية"]
        qr = qr[qr["city_ar"].isin(ALLOWED_CITIES)]
        qr = qr[qr["price_per_sqm"].notna() & (qr["price_per_sqm"] > 0)]
        qr["deed_count"] = 1
        qr["land_use"] = qr["type_category_ar"].replace(LAND_USE_NORMALIZE)
        qr["city"] = qr["city_ar"]
        qr["district"] = qr["district_ar"].replace("", "_غير_محدد")
        qr_agg = qr.groupby(["year", "city", "district", "land_use"], as_index=False).agg(
            avg_price_per_sqm=("price_per_sqm", "mean"),
            deed_count=("deed_count", "sum"),
        )
        parts.append(qr_agg)
    if not parts:
        raise FileNotFoundError("No growth data found.")
    combined = pd.concat(parts, ignore_index=True)
    combined = combined.groupby(["year", "city", "district", "land_use"], as_index=False).agg(
        avg_price_per_sqm=("avg_price_per_sqm", "mean"),
        deed_count=("deed_count", "sum"),
    )
    return combined


def add_osm_and_area(growth_df: pd.DataFrame) -> pd.DataFrame:
    """إضافة ميزات OSM (مسافات + كثافة مرافق 3كم) و area_sqm."""
    dist_cols = [c for c in OSM_NUMERIC_COLS if c.startswith("dist_")]
    count_cols = [c for c in OSM_NUMERIC_COLS if c.startswith("count_")]
    pairs = growth_df[["city", "district"]].drop_duplicates().to_numpy().tolist()
    pair_tuples = [tuple(p) for p in pairs]
    osm_df = build_osm_features_table(pair_tuples)
    if osm_df.empty:
        for c in dist_cols:
            growth_df[c] = 99.0
        for c in count_cols:
            growth_df[c] = 0
    else:
        growth_df = growth_df.merge(osm_df, on=["city", "district"], how="left")
        for c in dist_cols:
            if c not in growth_df.columns:
                growth_df[c] = 99.0
            growth_df[c] = pd.to_numeric(growth_df[c], errors="coerce").fillna(99.0)
        for c in count_cols:
            if c not in growth_df.columns:
                growth_df[c] = 0
            growth_df[c] = pd.to_numeric(growth_df[c], errors="coerce").fillna(0).astype(int)
    growth_df["area_sqm"] = 400.0
    return growth_df


# أعمدة الميزات (+ نمو تراكمي 2س، ميل الاتجاه السعري، نمو المنطقة)
NUMERIC_FEATURES = [
    "year_start", "area_sqm", "avg_price_prev", "deed_count_prev", "lagged_growth",
    "liquidity_2y", "price_volatility", "city_avg_growth", "region_avg_growth",
    "growth_2y", "price_trend_slope",
    "dist_school_km", "dist_hospital_km", "dist_mall_km",
    "count_school_3km", "count_hospital_3km", "count_mall_3km",
]
CATEGORICAL_FEATURES = ["land_use", "city", "district"]
FEATURE_COLS = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def build_rf_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("scaler", StandardScaler())]), NUMERIC_FEATURES),
            ("cat", Pipeline([("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True))]), CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline(steps=[
        ("preprocess", preprocessor),
        ("model", RandomForestRegressor(n_estimators=200, max_depth=12, random_state=42, n_jobs=-1)),
    ])


def build_lgbm_pipeline() -> Pipeline | None:
    try:
        import lightgbm as lgb
    except ImportError:
        return None
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("scaler", StandardScaler())]), NUMERIC_FEATURES),
            ("cat", Pipeline([("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True))]), CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline(steps=[
        ("preprocess", preprocessor),
        ("model", lgb.LGBMRegressor(n_estimators=200, max_depth=8, learning_rate=0.05, random_state=42, verbosity=-1, n_jobs=-1)),
    ])


def build_xgb_pipeline() -> Pipeline | None:
    try:
        import xgboost as xgb
    except ImportError:
        return None
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("scaler", StandardScaler())]), NUMERIC_FEATURES),
            ("cat", Pipeline([("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True))]), CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline(steps=[
        ("preprocess", preprocessor),
        ("model", xgb.XGBRegressor(n_estimators=200, max_depth=8, learning_rate=0.05, random_state=42, n_jobs=-1)),
    ])


def build_ridge_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("scaler", StandardScaler())]), NUMERIC_FEATURES),
            ("cat", Pipeline([("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True))]), CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline(steps=[
        ("preprocess", preprocessor),
        ("model", Ridge(alpha=1.0, random_state=42)),
    ])


def main() -> None:
    print("Loading all sources (real_sales_merged 2016–2026 + quarter_report if present)...")
    market_agg = load_all_sources_as_market_agg()
    print(f"Market agg rows: {len(market_agg):,} | Years: {sorted(market_agg['year'].dropna().unique().astype(int).tolist())}")

    print("Building growth target with year + market features...")
    growth_df = build_growth_target_with_features(market_agg)
    print(f"Growth target rows: {len(growth_df):,}")

    print("Adding OSM proximity features...")
    growth_df = add_osm_and_area(growth_df)

    X = growth_df[FEATURE_COLS].copy()
    X["deed_count_prev"] = X["deed_count_prev"].clip(upper=500)
    X["liquidity_2y"] = X["liquidity_2y"].clip(upper=1000)
    X["avg_price_prev"] = np.log1p(X["avg_price_prev"])
    X["price_volatility"] = np.log1p(X["price_volatility"].fillna(0).clip(lower=0))
    X["growth_2y"] = X["growth_2y"].fillna(X["growth_2y"].median()).clip(-0.25, 0.35)
    X["price_trend_slope"] = X["price_trend_slope"].fillna(0).clip(-0.15, 0.25)
    # الهدف: انحراف النمو عن الـ baseline (المودل يوقّع الانحراف ثم نضيف الـ baseline عند الاستدعاء)
    y = (growth_df[TARGET_COL].astype(float) - growth_df["baseline_growth"].astype(float)).clip(-0.15, 0.15)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"Train: {len(X_train):,} | Test: {len(X_test):,}")

    # مقارنة مودلز: RF، LightGBM، XGBoost، Ridge — 5-fold CV
    candidates: list[tuple[str, Pipeline]] = [
        ("RandomForest", build_rf_pipeline()),
        ("Ridge", build_ridge_pipeline()),
    ]
    lgb_pipe = build_lgbm_pipeline()
    if lgb_pipe is not None:
        candidates.append(("LightGBM", lgb_pipe))
    xgb_pipe = build_xgb_pipeline()
    if xgb_pipe is not None:
        candidates.append(("XGBoost", xgb_pipe))

    print("5-fold CV MAE (أقل = أفضل):")
    results: list[tuple[str, float, float, Pipeline]] = []
    for name, pipe in candidates:
        cv_scores = cross_val_score(pipe, X_train, y_train, cv=5, scoring="neg_mean_absolute_error", n_jobs=1)
        cv_mae = -cv_scores.mean()
        cv_std = cv_scores.std()
        results.append((name, cv_mae, cv_std, pipe))
        print(f"  {name:12} {cv_mae:.4f} ± {cv_std:.4f}")
    results.sort(key=lambda x: x[1])
    best_name, best_cv_mae, _, best_pipeline = results[0]
    print(f"الأفضل حسب CV: {best_name} (MAE={best_cv_mae:.4f})")

    # Temporal split: train on year_start < max_year-1, test on last transitions
    max_year = int(X["year_start"].max())
    temporal_test = (X["year_start"] >= max_year - 1)
    X_temporal_test = X[temporal_test]
    y_temporal_test = y[temporal_test]
    if len(X_temporal_test) >= 10:
        X_temp_train = X[~temporal_test]
        y_temp_train = y[~temporal_test]
        temp_pipe = clone(best_pipeline)
        temp_pipe.fit(X_temp_train, y_temp_train)
        pred_temp = temp_pipe.predict(X_temporal_test)
        mae_temporal = mean_absolute_error(y_temporal_test, pred_temp)
        print(f"Temporal eval (test on year_start>={max_year-1}): n={len(X_temporal_test)}, MAE={mae_temporal:.4f}")

    # مقارنة مع baseline: توقّع الانحراف = 0 (أي النمو = baseline_growth)
    y_test_full = growth_df.loc[X_test.index, TARGET_COL].astype(float)
    baseline_test = growth_df.loc[X_test.index, "baseline_growth"].astype(float)
    mae_baseline = mean_absolute_error(y_test_full, baseline_test)
    print(f"Baseline (متوسط نمو تاريخي) على Test: MAE(growth) = {mae_baseline:.4f}")

    # تقييم زمني ثابت: تدريب على year_start <= 2021، اختبار على year_start >= 2022
    TRAIN_MAX_YEAR, TEST_MIN_YEAR = 2021, 2022
    mask_train_t = X["year_start"] <= TRAIN_MAX_YEAR
    mask_test_t = X["year_start"] >= TEST_MIN_YEAR
    if mask_test_t.sum() >= 10 and mask_train_t.sum() >= 50:
        X_temp_train, y_temp_train = X[mask_train_t], y[mask_train_t]
        X_temp_test, y_temp_test = X[mask_test_t], y[mask_test_t]
        y_full_temp_test = growth_df.loc[X_temp_test.index, TARGET_COL].astype(float)
        baseline_temp_test = growth_df.loc[X_temp_test.index, "baseline_growth"].astype(float)
        temp_pipe = clone(best_pipeline)
        temp_pipe.fit(X_temp_train, y_temp_train)
        pred_temp = temp_pipe.predict(X_temp_test)
        pred_full_temp = baseline_temp_test.values + np.clip(pred_temp, -0.15, 0.15)
        mae_temp_model = mean_absolute_error(y_full_temp_test, pred_full_temp)
        mae_temp_baseline = mean_absolute_error(y_full_temp_test, baseline_temp_test)
        print(f"Temporal eval (train ≤{TRAIN_MAX_YEAR}, test ≥{TEST_MIN_YEAR}): n_test={mask_test_t.sum()}, MAE(model)={mae_temp_model:.4f}, MAE(baseline)={mae_temp_baseline:.4f}")

    print(f"Training best model ({best_name})...")
    best_pipeline.fit(X_train, y_train)
    y_pred = best_pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    print(f"Test MAE (residual): {mae:.4f} | R²: {r2:.3f}")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_pipeline, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")

    median_deed = float(X_train["deed_count_prev"].median())
    median_price = float(np.expm1(X_train["avg_price_prev"].median()))
    median_lagged = float(X_train["lagged_growth"].median())
    median_liquidity_2y = float(X_train["liquidity_2y"].median())
    median_price_volatility_log = float(X_train["price_volatility"].median())
    median_city_avg_growth = float(X_train["city_avg_growth"].median())
    median_region_avg_growth = float(X_train["region_avg_growth"].median())
    median_growth_2y = float(X_train["growth_2y"].median())
    median_price_trend_slope = float(X_train["price_trend_slope"].median())
    baseline_lookup = (
        growth_df[["city", "district", "land_use", "baseline_growth"]]
        .drop_duplicates()
        .assign(baseline_growth=lambda d: d["baseline_growth"].astype(float))
    )
    default_baseline_growth = float(baseline_lookup["baseline_growth"].median())
    baseline_list = [
        {"city": str(r.city), "district": str(r.district), "land_use": str(r.land_use), "baseline_growth": round(r.baseline_growth, 6)}
        for r in baseline_lookup.itertuples(index=False)
    ]
    valid_land_uses = sorted(X_train["land_use"].unique().astype(str).tolist())
    pairs = X_train[["city", "district"]].drop_duplicates()
    valid_city_districts = [{"city": str(r.city), "district": str(r.district)} for r in pairs.itertuples(index=False)]
    osm_table = X_train[["city", "district"] + OSM_NUMERIC_COLS].drop_duplicates()
    osm_features = []
    for r in osm_table.itertuples(index=False):
        o = {"city": str(r.city), "district": str(r.district)}
        for c in OSM_NUMERIC_COLS:
            if hasattr(r, c):
                o[c] = float(getattr(r, c)) if c.startswith("dist_") else int(getattr(r, c))
        osm_features.append(o)
    metadata = {
        "allowed_cities": sorted(ALLOWED_CITIES),
        "valid_land_uses": valid_land_uses,
        "valid_city_districts": valid_city_districts,
        "osm_features": osm_features,
        "default_prediction_year": max_year,
        "median_deed_count_prev": median_deed,
        "median_avg_price_prev": median_price,
        "median_lagged_growth": median_lagged,
        "median_liquidity_2y": median_liquidity_2y,
        "median_price_volatility_log": median_price_volatility_log,
        "median_city_avg_growth": median_city_avg_growth,
        "median_region_avg_growth": median_region_avg_growth,
        "median_growth_2y": median_growth_2y,
        "median_price_trend_slope": median_price_trend_slope,
        "default_baseline_growth": default_baseline_growth,
        "baseline_growth_lookup": baseline_list,
        "predicts_residual": True,
        "feature_cols": FEATURE_COLS,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "chosen_model": best_name,
    }
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"Saved metadata to {METADATA_PATH}")
    print("\nلتحسين دقة قرب المرافق (مدارس، مستشفيات، مولات): شغّلي من جذر المشروع:")
    print("  python scripts/fetch_district_centroids_google.py   # يحتاج GOOGLE_MAPS_API_KEY في .env")
    print("  python scripts/fetch_google_places_services.py")
    print("ثم أعدّي تشغيل هذا السكربت.")


if __name__ == "__main__":
    main()
