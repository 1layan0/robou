#!/usr/bin/env python3
"""
توليد db/loaded_aggregate_pg.sql لـ Supabase (PostgreSQL): نفس مصادر CSV/JSON كـ generate_aggregate_sql.py
لكن أعمدة مُطبّعة (district_id بدل تكرار المدينة/الحي/الإحداثيات في الجداول الفرعية).

الاستخدام من مجلد raboo3-ml:
  python scripts/build_supabase_aggregate_sql.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.district_id_map import get_district_id  # noqa: E402

DISTRICT_CSV = PROJECT_ROOT / "data" / "raw" / "district_centroids.csv"
REAL_SALES_CSV = PROJECT_ROOT / "data" / "real" / "real_sales_merged.csv"
DISTRICT_QUARTER_CSV = PROJECT_ROOT / "data" / "features" / "district_quarter_md10.csv"
DISTRICT_GROWTH_CSV = PROJECT_ROOT / "data" / "features" / "district_growth_yoy.csv"
AGG_METADATA_JSON = PROJECT_ROOT / "artifacts" / "price_model_agg_residual_metadata.json"
OUT_SQL = PROJECT_ROOT / "db" / "loaded_aggregate_pg.sql"


def escape_sql(v, max_len=500):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "NULL"
    if isinstance(v, str):
        s = str(v).strip()[:max_len].replace("\\", "\\\\").replace("'", "''")
        return f"'{s}'"
    if isinstance(v, (int, float)):
        return str(v)
    return f"'{str(v)}'"


def main() -> None:
    lines: list[str] = [
        "-- PostgreSQL load for Supabase (مُولَّد بـ build_supabase_aggregate_sql.py)",
        "BEGIN;",
        "",
    ]

    # 1) District
    if DISTRICT_CSV.exists():
        df = pd.read_csv(DISTRICT_CSV, encoding="utf-8-sig")
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        df = df.dropna(subset=["latitude", "longitude"])
        if not df.empty:
            lines.append("-- District")
            lines.append("INSERT INTO District (city_ar, district_ar, latitude, longitude, is_active) VALUES")
            rows = []
            for _, r in df.iterrows():
                c = escape_sql(r.get("city", ""), 100)
                d = escape_sql(r.get("district", ""), 150)
                if c == "''" or d == "''":
                    continue
                rows.append(f"  ({c}, {d}, {float(r['latitude']):.6f}, {float(r['longitude']):.6f}, 1)")
            if rows:
                lines.append(",\n".join(rows))
                lines.append("ON CONFLICT (city_ar, district_ar) DO NOTHING;")
                lines.append("")
                print(f"District: {len(rows)} صف")
    else:
        print(f"تحذير: {DISTRICT_CSV} غير موجود")

    # 2) RealSale
    if REAL_SALES_CSV.exists():
        df = pd.read_csv(REAL_SALES_CSV, encoding="utf-8-sig", nrows=50_000)
        df["price_per_sqm"] = pd.to_numeric(df["price_per_sqm"], errors="coerce")
        df = df.dropna(subset=["price_per_sqm", "year", "quarter", "city_ar", "district_ar", "property_type_ar"])
        if not df.empty:
            lines.append("-- RealSale")
            lines.append(
                "INSERT INTO RealSale (district_id, year, quarter, region_ar, property_type_ar, "
                "price_per_sqm, price_total, area_sqm, deed_count, source, tx_reference) VALUES"
            )
            rows = []
            skipped = 0
            for _, r in df.iterrows():
                city = str(r["city_ar"]).strip()
                dist = str(r["district_ar"]).strip()
                did = get_district_id(city, dist)
                if did is None:
                    skipped += 1
                    continue
                y, q = int(r["year"]), int(r["quarter"])
                reg = escape_sql(r.get("region_ar")) if pd.notna(r.get("region_ar")) else "NULL"
                ptype = escape_sql(r["property_type_ar"], 100)
                psqm = float(r["price_per_sqm"])
                ptot = r.get("price_total")
                ptot_s = f"{float(ptot):.2f}" if pd.notna(ptot) and str(ptot) != "nan" else "NULL"
                area = r.get("area_sqm")
                area_s = f"{float(area):.2f}" if pd.notna(area) and str(area) != "nan" else "NULL"
                deed = int(r["deed_count"]) if pd.notna(r.get("deed_count")) else 1
                src = escape_sql(r.get("source"), 100) if pd.notna(r.get("source")) else "NULL"
                txr = escape_sql(r.get("tx_reference"), 255) if pd.notna(r.get("tx_reference")) else "NULL"
                rows.append(
                    f"  ({did}, {y}, {q}, {reg}, {ptype}, {psqm:.2f}, {ptot_s}, {area_s}, {deed}, {src}, {txr})"
                )
            if skipped:
                print(f"RealSale: تخطي {skipped} صف بدون district_id")
            if rows:
                lines.append(",\n".join(rows))
                lines.append(";")
                lines.append("")
                print(f"RealSale: {len(rows)} صف")
    else:
        print(f"تحذير: {REAL_SALES_CSV} غير موجود")

    # 3) DistrictQuarterAggregate
    if DISTRICT_QUARTER_CSV.exists():
        df = pd.read_csv(DISTRICT_QUARTER_CSV, encoding="utf-8-sig")
        required = [
            "city_ar",
            "district_ar",
            "property_type_ar",
            "year",
            "quarter",
            "target_median_price_per_sqm",
            "deals_count",
            "baseline_price_per_sqm",
            "latitude",
            "longitude",
        ]
        if all(c in df.columns for c in required):
            lines.append("-- DistrictQuarterAggregate")
            lines.append(
                """INSERT INTO DistrictQuarterAggregate (
    district_id, property_type_ar, year, quarter,
    target_median_price_per_sqm, deals_count, std_price, iqr_price, min_price, max_price, prev_year_median_price_per_sqm,
    baseline_roll4, baseline_price_per_sqm, baseline_log, target_log, target_resid,
    dist_school_km, dist_hospital_km, dist_mall_km,     count_school_3km, count_hospital_3km, count_mall_3km,
    quarter_feature_growth_pct, quarter_sin, quarter_cos, year_quarter_idx) VALUES"""
            )
            rows = []
            skipped = 0

            def fl(row, k, d=None):
                v = row.get(k)
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    return "NULL" if d is None else str(d)
                try:
                    return f"{float(v):.6f}" if isinstance(v, (int, float)) else escape_sql(v, 150)
                except (TypeError, ValueError):
                    return "NULL" if d is None else str(d)

            def in_(row, k, d=0):
                v = row.get(k)
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    return str(d)
                try:
                    return str(int(float(v)))
                except (TypeError, ValueError):
                    return str(d)

            for _, r in df.iterrows():
                city = str(r["city_ar"]).strip()
                dist = str(r["district_ar"]).strip()
                did = get_district_id(city, dist)
                if did is None:
                    skipped += 1
                    continue
                ptype = escape_sql(r["property_type_ar"], 100)
                y, q = int(r["year"]), int(r["quarter"])
                bl = float(r.get("baseline_price_per_sqm") or r["target_median_price_per_sqm"])
                rows.append(
                    f"  ({did}, {ptype}, {y}, {q}, {fl(r, 'target_median_price_per_sqm')}, {in_(r, 'deals_count', 1)}, "
                    f"{fl(r, 'std_price')}, {fl(r, 'iqr_price')}, {fl(r, 'min_price')}, {fl(r, 'max_price')}, "
                    f"{fl(r, 'prev_year_median_price_per_sqm')}, {fl(r, 'baseline_roll4')}, {bl:.2f}, "
                    f"{fl(r, 'baseline_log')}, {fl(r, 'target_log')}, {fl(r, 'target_resid')}, "
                    f"{fl(r, 'dist_school_km')}, {fl(r, 'dist_hospital_km')}, {fl(r, 'dist_mall_km')}, "
                    f"{in_(r, 'count_school_3km')}, {in_(r, 'count_hospital_3km')}, {in_(r, 'count_mall_3km')}, "
                    f"{fl(r, 'growth_pct', 0)}, {fl(r, 'quarter_sin')}, {fl(r, 'quarter_cos')}, {in_(r, 'year_quarter_idx')})"
                )
            if skipped:
                print(f"DistrictQuarterAggregate: تخطي {skipped} صف بدون district_id")
            if rows:
                lines.append(",\n".join(rows))
                lines.append(
                    "ON CONFLICT (district_id, property_type_ar, year, quarter) DO NOTHING;"
                )
                lines.append("")
                print(f"DistrictQuarterAggregate: {len(rows)} صف")
    else:
        print(f"تحذير: {DISTRICT_QUARTER_CSV} غير موجود")

    # 4) DistrictGrowthYoy
    if DISTRICT_GROWTH_CSV.exists():
        df = pd.read_csv(DISTRICT_GROWTH_CSV, encoding="utf-8-sig")
        df["growth_pct"] = pd.to_numeric(df["growth_pct"], errors="coerce")
        df = df.dropna(subset=["growth_pct", "city_ar", "district_ar", "property_type_ar"])
        df = df.drop_duplicates(subset=["city_ar", "district_ar", "property_type_ar"], keep="first")
        if not df.empty:
            lines.append("-- DistrictGrowthYoy")
            lines.append(
                "INSERT INTO DistrictGrowthYoy (district_id, property_type_ar, yoy_growth_pct, growth_source, growth_confidence) VALUES"
            )
            rows = []
            skipped = 0
            for _, r in df.iterrows():
                city = str(r["city_ar"]).strip()
                dist = str(r["district_ar"]).strip()
                did = get_district_id(city, dist)
                if did is None:
                    skipped += 1
                    continue
                ptype = escape_sql(r["property_type_ar"], 100)
                g = float(r["growth_pct"])
                src = escape_sql(r.get("growth_source") or "default", 50)
                conf = escape_sql(r.get("growth_confidence") or "low", 20)
                rows.append(f"  ({did}, {ptype}, {g:.2f}, {src}, {conf})")
            if skipped:
                print(f"DistrictGrowthYoy: تخطي {skipped} صف بدون district_id")
            if rows:
                lines.append(",\n".join(rows))
                lines.append(
                    """ON CONFLICT (district_id, property_type_ar)
DO UPDATE SET yoy_growth_pct = EXCLUDED.yoy_growth_pct,
  growth_source = EXCLUDED.growth_source,
  growth_confidence = EXCLUDED.growth_confidence,
  updated_at = CURRENT_TIMESTAMP;"""
                )
                lines.append("")
                print(f"DistrictGrowthYoy: {len(rows)} صف")
    else:
        print(f"تحذير: {DISTRICT_GROWTH_CSV} غير موجود")

    # 5) Model version
    min_deals = 10
    metrics_json = "NULL"
    feature_cols_json = "NULL"
    if AGG_METADATA_JSON.exists():
        with open(AGG_METADATA_JSON, encoding="utf-8") as f:
            meta = json.load(f)
        min_deals = int(meta.get("best_min_deals") or meta.get("min_deals") or 10)
        metrics_json = escape_sql(json.dumps(meta.get("metrics") or {}, ensure_ascii=False), 2000)
        feature_cols_json = escape_sql(json.dumps(meta.get("feature_cols") or [], ensure_ascii=False), 2000)
    lines.append("-- AggregatedPriceModelVersion")
    lines.append("UPDATE AggregatedPriceModelVersion SET is_active = 0;")
    lines.append(
        f"INSERT INTO AggregatedPriceModelVersion (min_deals, artifact_path, metrics_json, feature_cols, is_active, notes) "
        f"VALUES ({min_deals}, 'artifacts/price_model_agg_residual.pkl', {metrics_json}, {feature_cols_json}, 1, 'من metadata');"
    )
    lines.append("")
    print("AggregatedPriceModelVersion: 1 صف")

    lines.append("COMMIT;")
    lines.append("")

    OUT_SQL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_SQL, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"تم الكتابة إلى {OUT_SQL}")


if __name__ == "__main__":
    main()
