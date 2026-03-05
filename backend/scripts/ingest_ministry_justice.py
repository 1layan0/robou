#!/usr/bin/env python3
"""
استيراد بيانات وزارة العدل (صفقات عقارية) ودمجها مع real_sales_merged.

- لا يُطبَّق حذف تكرار عام (مفتاح مدينة+حي+نوع+سعر+مساحة...) لأن البيانات غالباً غير مكررة.
- يُحذف داخل الملف فقط إذا تكرر الرقم المرجعي نفسه (نفس الصفقة مكررة).
- الدمج: إلحاق الصفوف بالملف الحالي دون حذف صفوف من بيانات الوزارة.

الاستخدام:
  python scripts/ingest_ministry_justice.py "/Users/sarah/Desktop/بيانات ارض/وزارة العدل/وزارة العدل 36 الف.xlsx"
  python scripts/ingest_ministry_justice.py "path/to/file.xlsx" --no-merge   # حفظ المستورد فقط
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "data" / "real"
MERGED_PATH = OUT_DIR / "real_sales_merged.csv"
SOURCE_TAG = "وزارة العدل"
ALLOWED_CITIES = {"الدمام", "الظهران", "الخبر"}

TARGET_COLS = [
    "year", "quarter", "region_ar", "city_ar", "district_ar",
    "property_type_ar", "deed_count", "price_total", "area_sqm",
    "price_per_sqm", "source", "tx_reference",
]

# توحيد تصنيف العقار مع الصيغة المستخدمة في التدريب
PROPERTY_TYPE_MAP = {
    "سكني": "قطعة أرض-سكنى",
    "تجاري": "قطعة أرض-تجارى",
    "زراعي": "قطعة أرض-زراعي",
}


def load_ministry_excel(path: Path) -> pd.DataFrame:
    """قراءة ملف Excel وزارة العدل (شيت الكل أو دمج الشيتات)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"الملف غير موجود: {path}")
    xl = pd.ExcelFile(path)
    if "الكل" in xl.sheet_names:
        df = pd.read_excel(path, sheet_name="الكل")
    else:
        # دمج شيتات المدن إن وُجدت
        sheets = [s for s in xl.sheet_names if s in ALLOWED_CITIES or s == "الكل"]
        if not sheets:
            sheets = xl.sheet_names[:1]
        dfs = [pd.read_excel(path, sheet_name=s) for s in sheets]
        df = pd.concat(dfs, ignore_index=True)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def normalize_ministry(df: pd.DataFrame) -> pd.DataFrame:
    """تحويل أعمدة وزارة العدل إلى الصيغة المعيارية."""
    # أسماء الأعمدة في الملف
    col_map = {
        "المنطقة": "region_ar",
        "المدينة": "city_ar",
        "الحي": "district_ar",
        "الرقم المرجعي": "tx_reference",
        "التاريخ ميلادي": "date_col",
        "تصنيف العقار": "property_type_ar",
        "السعر": "price_total",
        "المساحة": "area_sqm",
        "عدد العقارات": "deed_count",
    }
    out = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    if "date_col" not in out.columns:
        out["year"] = pd.NA
        out["quarter"] = pd.NA
    else:
        dt = pd.to_datetime(out["date_col"], errors="coerce")
        out["year"] = dt.dt.year
        out["quarter"] = dt.dt.quarter
        out = out.drop(columns=["date_col"])
    out["region_ar"] = out.get("region_ar", pd.Series(dtype=object)).fillna("").astype(str).str.strip()
    out["city_ar"] = out.get("city_ar", pd.Series(dtype=object)).fillna("").astype(str).str.strip()
    out["district_ar"] = out.get("district_ar", pd.Series(dtype=object)).fillna("").astype(str).str.strip().replace("nan", "")
    out["property_type_ar"] = (
        out.get("property_type_ar", pd.Series(dtype=object))
        .fillna("")
        .astype(str)
        .str.strip()
        .replace(PROPERTY_TYPE_MAP)
    )
    out["tx_reference"] = out.get("tx_reference", pd.Series(dtype=object)).astype(str).str.strip()
    out["deed_count"] = pd.to_numeric(out.get("deed_count"), errors="coerce").fillna(1).astype("Int64")
    out["price_total"] = pd.to_numeric(out.get("price_total"), errors="coerce")
    out["area_sqm"] = pd.to_numeric(out.get("area_sqm"), errors="coerce")
    out["price_per_sqm"] = out["price_total"] / out["area_sqm"].replace(0, pd.NA)
    out["source"] = SOURCE_TAG
    if "region_ar" not in out.columns or out["region_ar"].eq("").all():
        out["region_ar"] = "الشرقية"
    out["quarter"] = pd.to_numeric(out["quarter"], errors="coerce").fillna(0).astype(int)
    out["year"] = pd.to_numeric(out["year"], errors="coerce").fillna(0).astype(int)
    return out


def to_standard_frame(df: pd.DataFrame) -> pd.DataFrame:
    """إخراج إطار بالصيغة المعيارية (أعمدة TARGET_COLS فقط)."""
    out = pd.DataFrame()
    for c in TARGET_COLS:
        if c in df.columns:
            out[c] = df[c]
        else:
            out[c] = pd.NA
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="استيراد بيانات وزارة العدل ودمجها مع real_sales_merged (بدون حذف تكرار عام)."
    )
    parser.add_argument("file", type=str, help="مسار ملف Excel (وزارة العدل 36 الف.xlsx)")
    parser.add_argument("--no-merge", action="store_true", help="حفظ المستورد فقط دون دمج مع الملف الحالي")
    parser.add_argument("--train", action="store_true", help="إعادة تدريب موديل السعر بعد الدمج")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    print(f"جاري قراءة: {path.name}...")
    raw = load_ministry_excel(path)
    print(f"  عدد الصفوف الخام: {len(raw):,}")

    std = normalize_ministry(raw)
    # فلترة: الدمام، الظهران، الخبر فقط
    std = std[std["city_ar"].isin(ALLOWED_CITIES)].copy()
    std = std[std["price_per_sqm"].notna() & (std["price_per_sqm"] > 0) & std["area_sqm"].notna() & (std["area_sqm"] > 0)]
    std = to_standard_frame(std)
    std["district_ar"] = std["district_ar"].replace("", "_غير_محدد")

    # إزالة تكرار داخل الملف فقط: نفس الرقم المرجعي = نفس الصفقة
    before_dedup = len(std)
    std = std.drop_duplicates(subset=["tx_reference"], keep="first")
    n_dup_ref = before_dedup - len(std)
    if n_dup_ref > 0:
        print(f"  داخل الملف: حُذف {n_dup_ref} صف مكرر (نفس الرقم المرجعي)")
    print(f"  بعد التنظيف والفلترة: {len(std):,} صف")

    if args.no_merge:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUT_DIR / "real_sales_ministry_only.csv"
        std.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"\nتم حفظ المستورد فقط: {len(std):,} صف → {out_path}")
        return

    # دمج مع الملف الحالي: إلحاق فقط، بدون حذف تكرار عام
    existing = pd.DataFrame()
    if MERGED_PATH.exists():
        existing = pd.read_csv(MERGED_PATH, encoding="utf-8-sig")
        for c in TARGET_COLS:
            if c not in existing.columns:
                existing[c] = pd.NA
        existing = existing[TARGET_COLS]
        print(f"\nالملف الحالي: {len(existing):,} صف")
    else:
        existing = pd.DataFrame(columns=TARGET_COLS)

    merged = pd.concat([existing, std], ignore_index=True)
    merged = merged.sort_values(["year", "quarter", "city_ar", "district_ar"], ignore_index=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    merged.to_csv(MERGED_PATH, index=False, encoding="utf-8-sig")
    print(f"\nتم الدمج (إلحاق فقط، بدون حذف تكرار عام): {len(merged):,} صف → {MERGED_PATH}")
    print(f"  منها وزارة العدل: {(merged['source'] == SOURCE_TAG).sum():,} صف")

    if args.train:
        print("\nإعادة تدريب موديل السعر...")
        import subprocess
        r = subprocess.run(["python", "-m", "scripts.train_price_model"], cwd=PROJECT_ROOT)
        if r.returncode != 0:
            print("تحذير: انتهى التدريب بخطأ.")


if __name__ == "__main__":
    main()
