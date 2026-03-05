#!/usr/bin/env python3
"""
استيراد تقرير الربع السنوي (quarter_report SI.csv) إلى المشروع.

- الملف الأصلي يُقرأ من data/raw/quarter_report_SI.csv (أو --input).
- الناتج: data/real/quarter_report_si.csv. مع --eastern-only يُحفظ فقط صفوف المنطقة الشرقية (الدمام، الخبر، الظهران).

تشغيل:
  python scripts/ingest_quarter_report_si.py
  python scripts/ingest_quarter_report_si.py --input "/path/to/quarter_report SI.csv"
  python scripts/ingest_quarter_report_si.py --eastern-only   # الشرقية فقط (للمستودع)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUT_DIR = PROJECT_ROOT / "data" / "real"
DEFAULT_INPUT = RAW_DIR / "quarter_report_SI.csv"
OUT_PATH = OUT_DIR / "quarter_report_si.csv"
EASTERN_REGION = "المنطقة الشرقية"
EASTERN_CITIES = ["الدمام", "الخبر", "الظهران"]

# ربط أسماء أعمدة التقرير بالأسماء المعيارية في المشروع (بدون حذف أي عمود أصلي)
COLUMN_RENAME = {
    "yearnumber": "year",
    "quarternumber": "quarter",
    "quarternamear": "quarter_name_ar",
    "quarterid": "quarter_id",
    "region_ar": "region_ar",
    "city_ar": "city_ar",
    "district_ar": "district_ar",
    "typecategoryar": "type_category_ar",
    "deed_counts": "deed_counts",
    "RealEstatePrice_SUM": "price_total_sum",
    "Meter_Price_W_Avg_IQR": "price_per_sqm",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="استيراد quarter_report SI.csv مع توحيد الأعمدة دون حذف صفوف.")
    parser.add_argument(
        "--input",
        type=str,
        default=str(DEFAULT_INPUT),
        help="مسار ملف CSV للتقرير الربع سنوي.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="عرض الإحصائيات فقط دون حفظ الناتج.",
    )
    parser.add_argument(
        "--eastern-only",
        action="store_true",
        help="حفظ صفوف المنطقة الشرقية (الدمام، الخبر، الظهران) فقط.",
    )
    args = parser.parse_args()

    path = Path(args.input)
    if not path.exists():
        print(f"خطأ: الملف غير موجود: {path}")
        return

    df = pd.read_csv(path, encoding="utf-8-sig")
    n_before = len(df)
    cols_before = set(df.columns)

    # توحيد أسماء الأعمدة (فقط الأعمدة الموجودة)
    rename = {c: COLUMN_RENAME[c] for c in df.columns if c in COLUMN_RENAME}
    df = df.rename(columns=rename)

    # تحويل أنواع حيث يلزم
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    if "quarter" in df.columns:
        df["quarter"] = pd.to_numeric(df["quarter"], errors="coerce").astype("Int64")
    if "deed_counts" in df.columns:
        df["deed_counts"] = pd.to_numeric(df["deed_counts"], errors="coerce").astype("Int64")
    if "price_total_sum" in df.columns:
        df["price_total_sum"] = pd.to_numeric(df["price_total_sum"], errors="coerce")
    if "price_per_sqm" in df.columns:
        df["price_per_sqm"] = pd.to_numeric(df["price_per_sqm"], errors="coerce")

    for c in ["region_ar", "city_ar", "district_ar", "type_category_ar"]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str).str.strip()

    if args.eastern_only and "region_ar" in df.columns and "city_ar" in df.columns:
        df = df[
            (df["region_ar"] == EASTERN_REGION) & (df["city_ar"].isin(EASTERN_CITIES))
        ].copy()
        print(f"فلترة الشرقية فقط: {len(df):,} صف (الدمام، الخبر، الظهران).")

    n_after = len(df)
    if n_before != n_after:
        print(f"تحذير: تغير عدد الصفوف من {n_before} إلى {n_after} (لم يكن متوقعاً).")
    else:
        print(f"تم تحويل {n_after:,} صف دون حذف أي صف.")

    # إحصائيات سريعة
    if "region_ar" in df.columns:
        print("\nعدد الصفوف حسب المنطقة:")
        print(df["region_ar"].value_counts(dropna=False).head(15).to_string())
    if "region_ar" in df.columns and (df["region_ar"] == "المنطقة الشرقية").any():
        east = df[df["region_ar"] == "المنطقة الشرقية"]
        print(f"\nالمنطقة الشرقية: {len(east):,} صف")
        if "city_ar" in east.columns:
            print("  حسب المدينة:")
            for city, cnt in east["city_ar"].value_counts(dropna=False).items():
                print(f"    {city}: {cnt}")

    if not args.no_save:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
        print(f"\nتم الحفظ: {OUT_PATH} ({len(df):,} صف)")


if __name__ == "__main__":
    main()
