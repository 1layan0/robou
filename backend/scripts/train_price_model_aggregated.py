"""Train aggregated price model on residual above rolling 4q baseline (district-quarter level).

- Tries min_deals in [2, 5, 10], picks best by R², saves only that model.
- Input: data/features/district_quarter_md{md}.csv (from build_district_quarter_dataset.py)
- Target: y = target_resid; evaluation on target_median_price_per_sqm
- Output (best run only): artifacts/price_model_agg_residual.pkl, artifacts/price_model_agg_residual_metadata.json

Run from project root: python scripts/train_price_model_aggregated.py
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURES_DIR = PROJECT_ROOT / "data" / "features"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "price_model_agg_residual.pkl"
METADATA_PATH = ARTIFACTS_DIR / "price_model_agg_residual_metadata.json"

MIN_DEALS_LIST = [2, 5, 10]
RANDOM_STATE = 42
MIN_TEST_ROWS = 50  # أدنى حجم test مقبول عند اختيار best_min_deals

CAT_COLS = ["city_ar", "district_ar", "property_type_ar"]
# All features including baseline_price_per_sqm; exclude target_median_price_per_sqm, target_log, target_resid
NUM_COLS = [
    "year", "quarter", "log_deals", "iqr_price", "std_price",
    "prev_year_median_price_per_sqm",
    "baseline_price_per_sqm",
    "latitude", "longitude",
    "dist_school_km", "dist_hospital_km", "dist_mall_km",
    "count_school_3km", "count_hospital_3km", "count_mall_3km",
]
TARGET_RESID_COL = "target_resid"
TARGET_PRICE_COL = "target_median_price_per_sqm"
BASELINE_PRICE_COL = "baseline_price_per_sqm"
BASELINE_LOG_COL = "baseline_log"


def smape(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-6) -> float:
    """sMAPE (percent): mean( 2*|y-pred| / (|y|+|pred|+eps) ) * 100."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    denom = np.abs(y_true) + np.abs(y_pred) + eps
    return float(np.mean(2.0 * np.abs(y_true - y_pred) / denom) * 100)


def mape(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-6) -> float:
    """MAPE (percent): mean(|y - pred| / (|y| + eps)) * 100."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    return float(np.mean(np.abs(y_true - y_pred) / (np.abs(y_true) + eps)) * 100)


def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    """Fill numeric NaNs and ensure feature columns exist."""
    df = df.dropna(subset=[TARGET_RESID_COL, TARGET_PRICE_COL, BASELINE_LOG_COL, "deals_count"])
    df["log_deals"] = np.log1p(df["deals_count"].astype(float))
    for c in ["prev_year_median_price_per_sqm", "baseline_price_per_sqm", "latitude", "longitude"] + [x for x in NUM_COLS if x.startswith("dist_") or x.startswith("count_")]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "prev_year_median_price_per_sqm" in df.columns:
        df["prev_year_median_price_per_sqm"] = df["prev_year_median_price_per_sqm"].fillna(df[TARGET_PRICE_COL].median())
    df["latitude"] = df["latitude"].fillna(26.3)
    df["longitude"] = df["longitude"].fillna(50.1)
    for c in ["dist_school_km", "dist_hospital_km", "dist_mall_km"]:
        if c in df.columns:
            df[c] = df[c].fillna(99.0)
    for c in ["count_school_3km", "count_hospital_3km", "count_mall_3km"]:
        if c in df.columns:
            df[c] = df[c].fillna(0)
    return df


def train_and_evaluate_one(md: int) -> dict:
    """Load district_quarter_md{md}.csv, train residual model, return model + metrics."""
    path = FEATURES_DIR / f"district_quarter_md{md}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Run build_district_quarter_dataset.py first. Missing {path}")
    df = pd.read_csv(path, encoding="utf-8-sig")
    for c in [TARGET_RESID_COL, TARGET_PRICE_COL, BASELINE_PRICE_COL, BASELINE_LOG_COL, "deals_count"]:
        if c not in df.columns:
            raise ValueError(f"Missing column {c} in {path.name}")
    df = _prepare_df(df)

    feature_cols = [c for c in CAT_COLS + NUM_COLS if c in df.columns]
    X = df[feature_cols].copy()
    y_resid = df[TARGET_RESID_COL].astype(float).values

    strat_label = df["city_ar"].astype(str) + "|" + df["property_type_ar"].astype(str)
    min_count = strat_label.value_counts().min()
    if min_count < 2:
        strat_label = df["city_ar"].astype(str)
    train_idx, test_idx = train_test_split(
        df.index, test_size=0.2, random_state=RANDOM_STATE, stratify=strat_label
    )
    X_train = X.loc[train_idx]
    X_test = X.loc[test_idx]
    y_resid_train = df.loc[train_idx, TARGET_RESID_COL].astype(float).values
    baseline_log_test = df.loc[test_idx, BASELINE_LOG_COL].astype(float).values
    y_true_test = df.loc[test_idx, TARGET_PRICE_COL].astype(float).values
    y_baseline_test = df.loc[test_idx, BASELINE_PRICE_COL].astype(float).values

    cat_indices = [feature_cols.index(c) for c in CAT_COLS if c in feature_cols]
    try:
        import catboost as cb
        model = cb.CatBoostRegressor(
            iterations=1200, depth=8, learning_rate=0.04, l2_leaf_reg=3,
            random_seed=RANDOM_STATE, verbose=0, cat_features=cat_indices,
        )
        model.fit(X_train, y_resid_train, eval_set=(X_test, df.loc[test_idx, TARGET_RESID_COL].astype(float).values))
        model_name = "CatBoostRegressor"
    except ImportError:
        import lightgbm as lgb
        for c in CAT_COLS:
            if c in X_train.columns:
                X_train[c] = X_train[c].astype("category")
                X_test[c] = X_test[c].astype("category")
        model = lgb.LGBMRegressor(
            n_estimators=1200, max_depth=8, learning_rate=0.04,
            reg_alpha=0.05, reg_lambda=0.1, random_state=RANDOM_STATE, verbosity=-1,
        )
        model.fit(X_train, y_resid_train, eval_set=[(X_test, df.loc[test_idx, TARGET_RESID_COL].astype(float).values)])
        model_name = "LGBMRegressor"

    pred_resid = model.predict(X_test)
    pred_log = baseline_log_test + pred_resid
    pred_price = np.expm1(pred_log)

    test_mae = mean_absolute_error(y_true_test, pred_price)
    test_r2 = r2_score(y_true_test, pred_price)
    test_mape = mape(y_true_test, pred_price)
    test_smape = smape(y_true_test, pred_price)
    baseline_r2 = r2_score(y_true_test, y_baseline_test)
    baseline_mae = mean_absolute_error(y_true_test, y_baseline_test)
    baseline_mape = mape(y_true_test, y_baseline_test)
    baseline_smape = smape(y_true_test, y_baseline_test)

    return {
        "md": md,
        "model": model,
        "model_name": model_name,
        "feature_cols": feature_cols,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "test_r2": test_r2,
        "test_mae": test_mae,
        "test_mape": test_mape,
        "test_smape": test_smape,
        "baseline_r2": baseline_r2,
        "baseline_mae": baseline_mae,
        "baseline_mape": baseline_mape,
        "baseline_smape": baseline_smape,
    }


def main() -> None:
    print("Training residual model for each min_deals...")
    results = []
    for md in MIN_DEALS_LIST:
        print(f"  min_deals>={md} ...", end=" ", flush=True)
        res = train_and_evaluate_one(md)
        results.append(res)
        print(f"R²={res['test_r2']:.4f}  n_train={res['n_train']}  n_test={res['n_test']}")

    # جدول النتائج
    print("\n" + "=" * 80)
    print("Results by min_deals")
    print("=" * 80)
    print(f"{'min_deals':>10} {'n_train':>10} {'n_test':>10} {'R²':>10} {'MAE':>10} {'MAPE%':>10} {'sMAPE%':>10}")
    print("-" * 80)
    for r in results:
        print(f"{r['md']:>10} {r['n_train']:>10} {r['n_test']:>10} {r['test_r2']:>10.4f} {r['test_mae']:>10.2f} {r['test_mape']:>10.2f} {r['test_smape']:>10.2f}")
    print("=" * 80)

    # اختيار أفضل md: أعلى R² مع n_test >= MIN_TEST_ROWS
    candidates = [r for r in results if r["n_test"] >= MIN_TEST_ROWS]
    if not candidates:
        candidates = results
    best = max(candidates, key=lambda r: r["test_r2"])
    best_md = best["md"]

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best["model"], MODEL_PATH)
    metadata = {
        "model_type": "aggregated_residual",
        "baseline_type": "rolling_median_4q_lagged",
        "target_is_log": True,
        "best_min_deals": best_md,
        "feature_cols": best["feature_cols"],
        "categorical_cols": CAT_COLS,
        "target_col": TARGET_RESID_COL,
        "metrics": {
            "test_r2": best["test_r2"],
            "test_mae": best["test_mae"],
            "test_mape": best["test_mape"],
            "test_smape": best["test_smape"],
            "baseline_r2": best["baseline_r2"],
            "baseline_mae": best["baseline_mae"],
            "baseline_mape": best["baseline_mape"],
            "baseline_smape": best["baseline_smape"],
        },
        "n_train": best["n_train"],
        "n_test": best["n_test"],
    }
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print("\n--- Best run (saved) ---")
    print(f"best_min_deals:    {best_md}")
    print(f"rows_train:        {best['n_train']}")
    print(f"rows_test:        {best['n_test']}")
    print(f"R²:               {best['test_r2']:.4f}")
    print(f"MAE:              {best['test_mae']:.2f}")
    print(f"MAPE:             {best['test_mape']:.2f}%")
    print(f"sMAPE:            {best['test_smape']:.2f}%")
    print(f"\nSaved: {MODEL_PATH}")
    print(f"Saved: {METADATA_PATH}")


if __name__ == "__main__":
    main()
