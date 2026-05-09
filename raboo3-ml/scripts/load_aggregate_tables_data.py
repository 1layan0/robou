#!/usr/bin/env python3
"""
تحميل بيانات جداول مودل السعر المجمع من الملفات إلى MySQL.

يشغّل بعد:
  1. docker compose up -d
  2. تطبيق db/schema_aggregate.sql

الاستخدام (من جذر المشروع):
  python scripts/load_aggregate_tables_data.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text
from db.base import engine

DISTRICT_CSV = PROJECT_ROOT / "data" / "raw" / "district_centroids.csv"
REAL_SALES_CSV = PROJECT_ROOT / "data" / "real" / "real_sales_merged.csv"
DISTRICT_QUARTER_CSV = PROJECT_ROOT / "data" / "features" / "district_quarter_md10.csv"
DISTRICT_GROWTH_CSV = PROJECT_ROOT / "data" / "features" / "district_growth_yoy.csv"
AGG_METADATA_JSON = PROJECT_ROOT / "artifacts" / "price_model_agg_residual_metadata.json"
AGG_ARTIFACT_PATH = "artifacts/price_model_agg_residual.pkl"


def _safe_float(v, default=None):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _safe_int(v, default=None):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return default
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _str(v, max_len=500):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v).strip()[:max_len].replace("\\", "\\\\").replace("'", "''")
    return s


def load_district(conn) -> int:
    """District من district_centroids.csv"""
    if not DISTRICT_CSV.exists():
        print(f"تحذير: {DISTRICT_CSV} غير موجود. تخطي District.")
        return 0
    df = pd.read_csv(DISTRICT_CSV, encoding="utf-8-sig")
    if df.empty:
        return 0
    # أعمدة الملف: city, district, latitude, longitude
    required = ["city", "district", "latitude", "longitude"]
    for c in required:
        if c not in df.columns:
            print(f"تحذير: عمود {c} غير موجود في {DISTRICT_CSV.name}")
            return 0
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df = df.dropna(subset=["latitude", "longitude"])
    count = 0
    for _, r in df.iterrows():
        city = _str(r["city"], 100)
        district = _str(r["district"], 150)
        if not city or not district:
            continue
        lat = _safe_float(r["latitude"], 26.3)
        lon = _safe_float(r["longitude"], 50.1)
        if lat is None or lon is None:
            continue
        conn.execute(
            text("""
                INSERT IGNORE INTO District (city_ar, district_ar, latitude, longitude, is_active)
                VALUES (:city_ar, :district_ar, :lat, :lon, 1)
            """),
            {"city_ar": city, "district_ar": district, "lat": lat, "lon": lon},
        )
        count += 1
    return count


def load_real_sale(conn) -> int:
    """RealSale من real_sales_merged.csv"""
    if not REAL_SALES_CSV.exists():
        print(f"تحذير: {REAL_SALES_CSV} غير موجود. تخطي RealSale.")
        return 0
    df = pd.read_csv(REAL_SALES_CSV, encoding="utf-8-sig", nrows=200_000)
    required = ["year", "quarter", "city_ar", "district_ar", "property_type_ar", "price_per_sqm"]
    for c in required:
        if c not in df.columns:
            print(f"تحذير: عمود {c} غير موجود في real_sales_merged.csv")
            return 0
    df["price_per_sqm"] = pd.to_numeric(df["price_per_sqm"], errors="coerce")
    df = df.dropna(subset=["price_per_sqm", "year", "quarter", "city_ar", "district_ar", "property_type_ar"])
    count = 0
    for _, r in df.iterrows():
        year = _safe_int(r["year"])
        quarter = _safe_int(r["quarter"])
        if year is None or quarter is None:
            continue
        city = _str(r["city_ar"], 100)
        district = _str(r["district_ar"], 150)
        ptype = _str(r["property_type_ar"], 100)
        price_sqm = _safe_float(r["price_per_sqm"])
        if not city or not ptype or price_sqm is None:
            continue
        region = _str(r.get("region_ar"), 100) if "region_ar" in r else ""
        price_total = _safe_float(r.get("price_total"))
        area_sqm = _safe_float(r.get("area_sqm"))
        deed_count = _safe_int(r.get("deed_count"), 1)
        source = _str(r.get("source"), 100) if "source" in r else ""
        tx_ref = _str(r.get("tx_reference"), 255) if "tx_reference" in r else ""
        conn.execute(
            text("""
                INSERT INTO RealSale (year, quarter, region_ar, city_ar, district_ar, property_type_ar,
                     price_per_sqm, price_total, area_sqm, deed_count, source, tx_reference)
                VALUES (:year, :quarter, :region_ar, :city_ar, :district_ar, :property_type_ar,
                     :price_per_sqm, :price_total, :area_sqm, :deed_count, :source, :tx_reference)
            """),
            {
                "year": year, "quarter": quarter, "region_ar": region or None,
                "city_ar": city, "district_ar": district, "property_type_ar": ptype,
                "price_per_sqm": price_sqm, "price_total": price_total, "area_sqm": area_sqm,
                "deed_count": deed_count, "source": source or None, "tx_reference": tx_ref or None,
            },
        )
        count += 1
    return count


def load_district_quarter_aggregate(conn) -> int:
    """DistrictQuarterAggregate من district_quarter_md10.csv"""
    if not DISTRICT_QUARTER_CSV.exists():
        print(f"تحذير: {DISTRICT_QUARTER_CSV} غير موجود. تخطي DistrictQuarterAggregate.")
        return 0
    df = pd.read_csv(DISTRICT_QUARTER_CSV, encoding="utf-8-sig")
    required = [
        "city_ar", "district_ar", "property_type_ar", "year", "quarter",
        "target_median_price_per_sqm", "deals_count", "baseline_price_per_sqm",
        "latitude", "longitude",
    ]
    for c in required:
        if c not in df.columns:
            print(f"تحذير: عمود {c} غير موجود في district_quarter_md10.csv")
            return 0
    count = 0
    for _, r in df.iterrows():
        city = _str(r["city_ar"], 100)
        district = _str(r["district_ar"], 150)
        ptype = _str(r["property_type_ar"], 100)
        year = _safe_int(r["year"])
        quarter = _safe_int(r["quarter"])
        if not city or not ptype or year is None or quarter is None:
            continue
        target_med = _safe_float(r["target_median_price_per_sqm"])
        deals = _safe_int(r["deals_count"], 1)
        baseline = _safe_float(r["baseline_price_per_sqm"], target_med)
        if target_med is None:
            continue
        lat = _safe_float(r["latitude"], 26.3)
        lon = _safe_float(r["longitude"], 50.1)
        if lat is None:
            lat = 26.3
        if lon is None:
            lon = 50.1
        conn.execute(
            text("""
                INSERT INTO DistrictQuarterAggregate (
                    city_ar, district_ar, property_type_ar, year, quarter,
                    target_median_price_per_sqm, deals_count, std_price, iqr_price, min_price, max_price,
                    prev_year_median_price_per_sqm, baseline_roll4, baseline_price_per_sqm,
                    baseline_log, target_log, target_resid,
                    latitude, longitude,
                    dist_school_km, dist_hospital_km, dist_mall_km,
                    count_school_3km, count_hospital_3km, count_mall_3km,
                    growth_pct, quarter_sin, quarter_cos, year_quarter_idx
                ) VALUES (
                    :city_ar, :district_ar, :property_type_ar, :year, :quarter,
                    :target_median_price_per_sqm, :deals_count, :std_price, :iqr_price, :min_price, :max_price,
                    :prev_year_median_price_per_sqm, :baseline_roll4, :baseline_price_per_sqm,
                    :baseline_log, :target_log, :target_resid,
                    :latitude, :longitude,
                    :dist_school_km, :dist_hospital_km, :dist_mall_km,
                    :count_school_3km, :count_hospital_3km, :count_mall_3km,
                    :growth_pct, :quarter_sin, :quarter_cos, :year_quarter_idx
                )
            """),
            {
                "city_ar": city, "district_ar": district, "property_type_ar": ptype,
                "year": year, "quarter": quarter,
                "target_median_price_per_sqm": target_med,
                "deals_count": max(1, deals or 1),
                "std_price": _safe_float(r.get("std_price")),
                "iqr_price": _safe_float(r.get("iqr_price")),
                "min_price": _safe_float(r.get("min_price")),
                "max_price": _safe_float(r.get("max_price")),
                "prev_year_median_price_per_sqm": _safe_float(r.get("prev_year_median_price_per_sqm")),
                "baseline_roll4": _safe_float(r.get("baseline_roll4")),
                "baseline_price_per_sqm": baseline if baseline is not None else target_med,
                "baseline_log": _safe_float(r.get("baseline_log")),
                "target_log": _safe_float(r.get("target_log")),
                "target_resid": _safe_float(r.get("target_resid")),
                "latitude": lat, "longitude": lon,
                "dist_school_km": _safe_float(r.get("dist_school_km")),
                "dist_hospital_km": _safe_float(r.get("dist_hospital_km")),
                "dist_mall_km": _safe_float(r.get("dist_mall_km")),
                "count_school_3km": _safe_int(r.get("count_school_3km"), 0),
                "count_hospital_3km": _safe_int(r.get("count_hospital_3km"), 0),
                "count_mall_3km": _safe_int(r.get("count_mall_3km"), 0),
                "growth_pct": _safe_float(r.get("growth_pct"), 0),
                "quarter_sin": _safe_float(r.get("quarter_sin")),
                "quarter_cos": _safe_float(r.get("quarter_cos")),
                "year_quarter_idx": _safe_int(r.get("year_quarter_idx")),
            },
        )
        count += 1
    return count


def load_district_growth_yoy(conn) -> int:
    """DistrictGrowthYoy من district_growth_yoy.csv"""
    if not DISTRICT_GROWTH_CSV.exists():
        print(f"تحذير: {DISTRICT_GROWTH_CSV} غير موجود. تخطي DistrictGrowthYoy.")
        return 0
    df = pd.read_csv(DISTRICT_GROWTH_CSV, encoding="utf-8-sig")
    required = ["city_ar", "district_ar", "property_type_ar", "growth_pct"]
    for c in required:
        if c not in df.columns:
            print(f"تحذير: عمود {c} غير موجود في district_growth_yoy.csv")
            return 0
    df["growth_pct"] = pd.to_numeric(df["growth_pct"], errors="coerce")
    df = df.dropna(subset=["growth_pct"])
    count = 0
    seen = set()
    for _, r in df.iterrows():
        city = _str(r["city_ar"], 100)
        district = _str(r["district_ar"], 150)
        ptype = _str(r["property_type_ar"], 100)
        growth = _safe_float(r["growth_pct"], 0)
        if not city or not district or not ptype:
            continue
        key = (city, district, ptype)
        if key in seen:
            continue
        seen.add(key)
        src = _str(r.get("growth_source"), 50) or "default"
        conf = _str(r.get("growth_confidence"), 20) or "low"
        conn.execute(
            text("""
                INSERT INTO DistrictGrowthYoy (city_ar, district_ar, property_type_ar, growth_pct, growth_source, growth_confidence)
                VALUES (:city_ar, :district_ar, :property_type_ar, :growth_pct, :growth_source, :growth_confidence)
                ON DUPLICATE KEY UPDATE growth_pct = VALUES(growth_pct), growth_source = VALUES(growth_source), growth_confidence = VALUES(growth_confidence)
            """),
            {"city_ar": city, "district_ar": district, "property_type_ar": ptype, "growth_pct": growth, "growth_source": src, "growth_confidence": conf},
        )
        count += 1
    return count


def load_aggregated_model_version(conn) -> int:
    """صف واحد في AggregatedPriceModelVersion من metadata المودل الحالي."""
    conn.execute(text("UPDATE AggregatedPriceModelVersion SET is_active = 0"))
    if not AGG_METADATA_JSON.exists():
        print(f"تحذير: {AGG_METADATA_JSON} غير موجود. إدراج نسخة افتراضية.")
        conn.execute(
            text("""
                INSERT INTO AggregatedPriceModelVersion (min_deals, artifact_path, is_active, notes)
                VALUES (10, :path, 1, 'افتراضي - لا metadata')
            """),
            {"path": AGG_ARTIFACT_PATH},
        )
        return 1
    with open(AGG_METADATA_JSON, encoding="utf-8") as f:
        meta = json.load(f)
    min_deals = _safe_int(meta.get("best_min_deals") or meta.get("min_deals"), 10)
    metrics = meta.get("metrics") or {}
    feature_cols = meta.get("feature_cols") or []
    metrics_json = json.dumps(metrics, ensure_ascii=False) if metrics else None
    feature_cols_json = json.dumps(feature_cols, ensure_ascii=False) if feature_cols else None
    conn.execute(
        text("""
            INSERT INTO AggregatedPriceModelVersion (min_deals, artifact_path, metrics_json, feature_cols, is_active, notes)
            VALUES (:min_deals, :artifact_path, :metrics_json, :feature_cols, 1, 'من price_model_agg_residual_metadata.json')
        """),
        {
            "min_deals": min_deals,
            "artifact_path": AGG_ARTIFACT_PATH,
            "metrics_json": metrics_json,
            "feature_cols": feature_cols_json,
        },
    )
    return 1


def main() -> None:
    print("تحميل جداول مودل السعر المجمع...")
    with engine.connect() as conn:
        conn.execute(text("SET NAMES utf8mb4"))
        n_district = load_district(conn)
        print(f"  District: {n_district:,}")
        n_sale = load_real_sale(conn)
        print(f"  RealSale: {n_sale:,}")
        n_agg = load_district_quarter_aggregate(conn)
        print(f"  DistrictQuarterAggregate: {n_agg:,}")
        n_growth = load_district_growth_yoy(conn)
        print(f"  DistrictGrowthYoy: {n_growth:,}")
        n_version = load_aggregated_model_version(conn)
        print(f"  AggregatedPriceModelVersion: {n_version}")
        conn.commit()
    print("تم.")


if __name__ == "__main__":
    main()
