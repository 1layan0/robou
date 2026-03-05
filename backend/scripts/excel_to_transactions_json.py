#!/usr/bin/env python3
"""
تحويل ملف Excel (صفقات من سكرابنق) إلى JSON لعرضه في صفحة صفقات الأراضي.

الاستخدام:
  pip install pandas openpyxl   # مرة واحدة إذا لم يكن مثبتاً
  python backend/scripts/excel_to_transactions_json.py "مسار/ملفك.xlsx"
  python backend/scripts/excel_to_transactions_json.py "مسار/ملفك.xlsx" -o frontend/public/data/transactions.json

الأعمدة المتوقعة في الإكسل (أي منها يكفي، بأي اسم قريب):
  - التاريخ: تاريخ، التاريخ، date، Date
  - المدينة: مدينة، المدينة، city، City
  - الحي: حي، الحي، حي/الحي، district، Hai
  - التصنيف: تصنيف، التصنيف، سكني/تجاري، category
  - النوع: نوع العقار، نوع، dtype، DType
  - المساحة: مساحة، المساحة، area، Area (بالمتر المربع)
  - قيمة الصفقة: سعر، السعر، سعر الصفقة، price، Deal_price
  - سعر المتر: سعر المتر، meter_price، Meter_price
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

# مسار الحفظ الافتراضي (ضمن مشروع frontend)
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND.parent
DEFAULT_OUT = PROJECT_ROOT / "frontend" / "public" / "data" / "transactions.json"

# أسماء أعمدة محتملة بالعربي والإنجليزي → اسم موحد
COL_DATE = ["تاريخ", "التاريخ", "date", "Date", "transaction_date"]
COL_YEAR = ["transaction_year", "year", "السنة", "سنة"]
COL_QUARTER = ["transaction_quarter", "quarter", "الربع"]
COL_CITY = ["مدينة", "المدينة", "city", "City", "city_name", "المدينة"]
COL_HAI = ["حي", "الحي", "district", "Hai", "district_name", "الحي"]
COL_CATEGORY = ["تصنيف", "التصنيف", "category", "Category"]
COL_DTYPE = ["نوع العقار", "نوع", "dtype", "DType", "Dtype", "property_type"]
COL_AREA = ["مساحة", "المساحة", "area", "Area", "المساحة", "land_area_sqm"]
COL_DEAL_PRICE = ["سعر", "السعر", "سعر الصفقة", "قيمة الصفقة", "price", "Deal_price", "Deal price", "land_price_sar"]
COL_METER_PRICE = ["سعر المتر", "سعر المتر", "meter_price", "Meter_price", "price_per_sqm", "unit_price_sar_per_sqm"]


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """أول عمود يوجد في الإطار من قائمة الأسماء."""
    cols = [str(c).strip() for c in df.columns]
    for name in candidates:
        for c in cols:
            if c == name or (name in c):
                return c
    return None


def excel_to_deals(path: Path, limit: int | None = 5000) -> list[dict]:
    """قراءة Excel وإرجاع قائمة صفقات بالصيغة المطلوبة للواجهة. limit: أقصى عدد صفوف (لتجنب ملف ضخم)."""
    if not path.exists():
        raise FileNotFoundError(f"الملف غير موجود: {path}")
    df = pd.read_excel(path, sheet_name=0)
    df.columns = [str(c).strip() for c in df.columns]

    date_col = find_column(df, COL_DATE)
    year_col = find_column(df, COL_YEAR)
    quarter_col = find_column(df, COL_QUARTER)
    city_col = find_column(df, COL_CITY)
    hai_col = find_column(df, COL_HAI)
    category_col = find_column(df, COL_CATEGORY)
    dtype_col = find_column(df, COL_DTYPE)
    area_col = find_column(df, COL_AREA)
    deal_col = find_column(df, COL_DEAL_PRICE)
    meter_col = find_column(df, COL_METER_PRICE)

    if not city_col:
        raise ValueError("لم يتم العثور على عمود المدينة. تأكد من وجود عمود مثل: مدينة، المدينة، city، city_name")

    if limit and len(df) > limit:
        df = df.tail(limit)  # آخر limit صف (الأحدث عادة)

    deals = []
    for _, row in df.iterrows():
        city = row.get(city_col)
        if pd.isna(city) or str(city).strip() == "":
            continue
        city = str(city).strip()

        area_val = None
        if area_col:
            try:
                area_val = float(row.get(area_col))
            except (TypeError, ValueError):
                pass

        deal_val = None
        if deal_col:
            try:
                deal_val = float(row.get(deal_col))
            except (TypeError, ValueError):
                pass

        meter_val = None
        if meter_col:
            try:
                meter_val = float(row.get(meter_col))
            except (TypeError, ValueError):
                pass
        if meter_val is None and deal_val is not None and area_val and area_val > 0:
            meter_val = deal_val / area_val

        date_str = ""
        if date_col:
            v = row.get(date_col)
            if pd.notna(v):
                if hasattr(v, "strftime"):
                    date_str = v.strftime("%Y-%m-%d")
                else:
                    date_str = str(v).strip()
        if not date_str and year_col and quarter_col:
            y, q = row.get(year_col), row.get(quarter_col)
            if pd.notna(y) and pd.notna(q):
                try:
                    y, q = int(float(y)), int(float(q))
                    month = (q - 1) * 3 + 1
                    date_str = f"{y}-{month:02d}-01"
                except (TypeError, ValueError):
                    date_str = f"{y}-Q{q}"

        deal = {
            "Date": date_str or None,
            "City": city,
            "Hai": str(row.get(hai_col, "")).strip() if hai_col else None,
            "Category": str(row.get(category_col, "")).strip() if category_col else None,
            "DType": str(row.get(dtype_col, "")).strip() if dtype_col else None,
            "Area": round(area_val, 2) if area_val is not None else None,
            "Deal_price": int(deal_val) if deal_val is not None else None,
            "Meter_price": round(meter_val, 2) if meter_val is not None else None,
        }
        deals.append(deal)

    return deals


def main():
    parser = argparse.ArgumentParser(description="تحويل Excel صفقات إلى transactions.json")
    parser.add_argument("excel_path", type=str, help="مسار ملف Excel")
    parser.add_argument("-o", "--output", type=str, default=str(DEFAULT_OUT), help="مسار ملف JSON الناتج")
    parser.add_argument("--list-columns", action="store_true", help="عرض أسماء الأعمدة فقط ثم خروج")
    parser.add_argument("--limit", type=int, default=5000, help="أقصى عدد صفقات في الملف الناتج (افتراضي 5000)")
    args = parser.parse_args()

    path = Path(args.excel_path)
    if not path.exists():
        print(f"الملف غير موجود: {path}")
        return 1

    if args.list_columns:
        df = pd.read_excel(path, sheet_name=0)
        print("الأعمدة:", list(df.columns))
        print("عدد الصفوف:", len(df))
        return 0

    out_path = Path(args.output)

    deals = excel_to_deals(path, limit=args.limit)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(deals, f, ensure_ascii=False, indent=2)

    print(f"تم تحويل {len(deals)} صفقة إلى: {out_path}")
    return 0


if __name__ == "__main__":
    exit(main() or 0)
