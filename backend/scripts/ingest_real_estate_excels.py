#!/usr/bin/env python3
"""
سكربت لجلب بيانات حقيقية أكثر (من ملفات الإكسل التي عندك)
ويحولها إلى CSVs جاهزة للتدريب والتحليل داخل المشروع.

المصادر المتوقعة (كما ناقشنا سابقاً):
- /Users/sarah/Downloads/اجارات الخبر والدمام.xlsx
- /Users/sarah/Downloads/صفقات بيع هيئة العقار.xlsx

الناتج:
- data/real/real_rents_quarterly.csv
- data/real/real_sales_quarterly.csv

تشغيل (من جذر المشروع):
    python scripts/ingest_real_estate_excels.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "data" / "real"

# المدن المدعومة فقط (الدمام، الظهران، الخبر)
ALLOWED_CITIES = {"الدمام", "الظهران", "الخبر"}


def load_rents(path: Path) -> pd.DataFrame:
    """
    قراءة ملف الإيجارات وتحويله إلى شكل منظم.
    نتوقع أعمدة تقريبية مثل:
      - year, quarter, city_ar, category_ar, avg_rent_per_sqm (أو ما يشبهها)
    لو اختلفت الأسماء يمكنك تعديلها لاحقاً بسهولة.
    """
    print(f"تحميل بيانات الإيجارات من: {path}")
    df = pd.read_excel(path)

    # محاولات ذكية لإعادة تسمية الأعمدة إلى أسماء ثابتة
    rename_map = {}
    for col in df.columns:
        col_norm = str(col).strip().lower()
        if "year" in col_norm or "سنة" in col_norm or "عام" in col_norm:
            rename_map[col] = "year"
        elif "quarter" in col_norm or "ربع" in col_norm:
            rename_map[col] = "quarter"
        elif "city" in col_norm or "المدينة" in col_norm or "مدينة" in col_norm:
            rename_map[col] = "city_ar"
        elif "district" in col_norm or "حي" in col_norm:
            rename_map[col] = "district_ar"
        elif "category" in col_norm or "فئة" in col_norm or "نوع" in col_norm:
            rename_map[col] = "category_ar"
        elif "rent" in col_norm or "إيجار" in col_norm:
            rename_map[col] = "avg_rent"

    df = df.rename(columns=rename_map)

    keep_cols = [c for c in ["year", "quarter", "city_ar", "district_ar", "category_ar", "avg_rent"] if c in df.columns]
    df = df[keep_cols].copy()

    # تنظيف بسيط
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    if "quarter" in df.columns:
        df["quarter"] = df["quarter"].astype(str).str.strip()
    for col in ["city_ar", "district_ar", "category_ar"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    if "avg_rent" in df.columns:
        df["avg_rent"] = pd.to_numeric(df["avg_rent"], errors="coerce")

    df = df.dropna(subset=["year"])
    if "city_ar" in df.columns:
        df = df[df["city_ar"].isin(ALLOWED_CITIES)].copy()
    print(f"عدد سجلات الإيجار بعد التنظيف (الدمام+الظهران+الخبر): {len(df)}")
    return df


def load_sales(path: Path) -> pd.DataFrame:
    """
    قراءة ملف صفقات البيع وتحويله إلى شكل منظم.
    من وصفك السابق نتوقع أعمدة مثل:
      - city_ar, district_ar, typecategoryar, year, quarter,
        Meter_Price_W_Avg_IQR, deed_counts
    """
    print(f"تحميل بيانات الصفقات من: {path}")
    df = pd.read_excel(path)

    rename_map = {}
    for col in df.columns:
        col_norm = str(col).strip().lower()
        if col_norm in {"city_ar", "المدينة"} or "city" in col_norm:
            rename_map[col] = "city_ar"
        elif col_norm in {"district_ar", "الحي"} or "district" in col_norm or "حي" in col_norm:
            rename_map[col] = "district_ar"
        elif "typecategory" in col_norm or "فئة" in col_norm or "نوع" in col_norm:
            rename_map[col] = "type_category_ar"
        elif "year" in col_norm or "سنة" in col_norm or "عام" in col_norm:
            rename_map[col] = "year"
        elif "quarter" in col_norm or "ربع" in col_norm:
            rename_map[col] = "quarter"
        elif "meter_price" in col_norm or "meter_price_w_avg_iqr" in col_norm or "متوسط" in col_norm:
            rename_map[col] = "price_per_sqm"
        elif "deed" in col_norm or "deed_counts" in col_norm or "صفقات" in col_norm:
            rename_map[col] = "deed_counts"

    df = df.rename(columns=rename_map)

    keep_cols = [c for c in ["year", "quarter", "city_ar", "district_ar", "type_category_ar", "price_per_sqm", "deed_counts"] if c in df.columns]
    df = df[keep_cols].copy()

    # تنظيف
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    if "quarter" in df.columns:
        # أحياناً تكون الأعمدة مكررة أو ذات نوع خاص، لذلك نكتفي بالتحويل إلى نص
        df["quarter"] = df["quarter"].astype(str)
    for col in ["city_ar", "district_ar", "type_category_ar"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    if "price_per_sqm" in df.columns:
        df["price_per_sqm"] = pd.to_numeric(df["price_per_sqm"], errors="coerce")
    if "deed_counts" in df.columns:
        df["deed_counts"] = pd.to_numeric(df["deed_counts"], errors="coerce").astype("Int64")

    df = df.dropna(subset=["year"])
    if "city_ar" in df.columns:
        df = df[df["city_ar"].isin(ALLOWED_CITIES)].copy()
    print(f"عدد سجلات الصفقات بعد التنظيف (الدمام+الظهران+الخبر): {len(df)}")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest real estate Excel files into CSVs inside the project.")
    parser.add_argument(
        "--rents_excel",
        type=str,
        default="/Users/sarah/Downloads/اجارات الخبر والدمام.xlsx",
        help="مسار ملف إكسل للإيجارات.",
    )
    parser.add_argument(
        "--sales_excel",
        type=str,
        default="/Users/sarah/Downloads/صفقات بيع هيئة العقار.xlsx",
        help="مسار ملف إكسل لصفقات البيع.",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rents_path = Path(args.rents_excel)
    sales_path = Path(args.sales_excel)

    if rents_path.exists():
        rents_df = load_rents(rents_path)
        rents_out = OUT_DIR / "real_rents_quarterly.csv"
        rents_df.to_csv(rents_out, index=False, encoding="utf-8-sig")
        print(f"تم حفظ بيانات الإيجارات في: {rents_out}")
    else:
        print(f"تحذير: لم يتم العثور على ملف الإيجارات: {rents_path}")

    if sales_path.exists():
        sales_df = load_sales(sales_path)
        sales_out = OUT_DIR / "real_sales_quarterly.csv"
        sales_df.to_csv(sales_out, index=False, encoding="utf-8-sig")
        print(f"تم حفظ بيانات الصفقات في: {sales_out}")
    else:
        print(f"تحذير: لم يتم العثور على ملف الصفقات: {sales_path}")


if __name__ == "__main__":
    main()

