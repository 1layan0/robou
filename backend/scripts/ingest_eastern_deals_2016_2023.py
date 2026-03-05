#!/usr/bin/env python3
"""
استيراد بيانات صفقات شرقية 2016–2023 من ملف Excel ودمجها مع real_sales_merged.

- لا يُعدّل الملف الأصلي ولا يُحذف منه أي شيء؛ القراءة فقط.
- الدمج: إلحاق الصفوف المستوردة إلى real_sales_merged (بدون حذف صفوف موجودة).
- إزالة تكرار داخل الملف الجديد فقط (نفس رقم الصفقة).

الاستخدام:
  python scripts/ingest_eastern_deals_2016_2023.py
  python scripts/ingest_eastern_deals_2016_2023.py "/path/to/2016-2023_eastern_deals.xlsx"
  python scripts/ingest_eastern_deals_2016_2023.py --no-merge   # حفظ المستورد فقط
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "data" / "real"
MERGED_PATH = OUT_DIR / "real_sales_merged.csv"
SOURCE_TAG = "2016-2023_eastern"
ALLOWED_CITIES = {"الدمام", "الظهران", "الخبر"}

TARGET_COLS = [
    "year", "quarter", "region_ar", "city_ar", "district_ar",
    "property_type_ar", "deed_count", "price_total", "area_sqm",
    "price_per_sqm", "source", "tx_reference",
]

# الربع النصي → رقم
QUARTER_MAP = {
    "الربع الأول": 1,
    "الربع الثاني": 2,
    "الربع الثالث": 3,
    "الربع الرابع": 4,
}

# توحيد نوع العقار مع الصيغة المستخدمة في التدريب (نوع العقار + التصنيف)
def _norm_property_type(row: pd.Series) -> str:
    kind = (row.get("نوع العقار") or "").strip()
    cat = (row.get("التصنيف") or "").strip()
    if not kind:
        return "أخرى"
    kind_lower = kind.lower() if hasattr(kind, "lower") else str(kind)
    if "قطعة أرض" in kind or kind == "قطعة أرض":
        if cat == "تجاري":
            return "قطعة أرض-تجارى"
        if cat == "زراعي":
            return "قطعة أرض-زراعي"
        return "قطعة أرض-سكنى"
    if kind in ("شقة", "وحدة سكنية", "وحدة عقارية"):
        return "شقة"
    if kind in ("فيلا", "بيت", "عمارة", "إستراحة"):
        return "فيلا"
    if "تجار" in kind or "معرض" in kind or "محل" in kind:
        return "قطعة أرض-تجارى"
    if "زراع" in kind:
        return "قطعة أرض-زراعي"
    return "أخرى"


def load_excel(path: Path) -> pd.DataFrame:
    """قراءة شيت الكل فقط؛ لا تعديل على الملف."""
    if not path.exists():
        raise FileNotFoundError(f"الملف غير موجود: {path}")
    xl = pd.ExcelFile(path)
    if "الكل" in xl.sheet_names:
        return pd.read_excel(path, sheet_name="الكل")
    sheets = [s for s in xl.sheet_names if s in ALLOWED_CITIES]
    if not sheets:
        sheets = xl.sheet_names[:1]
    dfs = [pd.read_excel(path, sheet_name=s) for s in sheets]
    return pd.concat(dfs, ignore_index=True)


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """تحويل أعمدة الملف إلى الصيغة المعيارية."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    out = pd.DataFrame()
    out["year"] = pd.to_numeric(df.get("السنة"), errors="coerce")
    quarter_ar = df.get("الربع", pd.Series(dtype=object)).astype(str).str.strip()
    out["quarter"] = quarter_ar.map(QUARTER_MAP)
    out["region_ar"] = df.get("المنطقة", pd.Series(dtype=object)).fillna("").astype(str).str.strip().replace("nan", "")
    out["city_ar"] = df.get("المدينة", pd.Series(dtype=object)).fillna("").astype(str).str.strip().replace("nan", "")
    out["district_ar"] = df.get("الحي", pd.Series(dtype=object)).fillna("").astype(str).str.strip().replace("nan", "")
    out["property_type_ar"] = df.apply(_norm_property_type, axis=1)
    out["deed_count"] = pd.to_numeric(df.get("عدد العقارات"), errors="coerce").fillna(1).astype("Int64")
    out["price_total"] = pd.to_numeric(df.get("السعر"), errors="coerce")
    out["area_sqm"] = pd.to_numeric(df.get("المساحة"), errors="coerce")
    out["price_per_sqm"] = pd.to_numeric(df.get("سعر المتر"), errors="coerce")
    # إن لم يكن سعر المتر موجوداً نحسبه
    miss = out["price_per_sqm"].isna() | (out["price_per_sqm"] <= 0)
    out.loc[miss, "price_per_sqm"] = (
        out.loc[miss, "price_total"] / out.loc[miss, "area_sqm"].replace(0, pd.NA)
    )
    out["source"] = SOURCE_TAG
    out["tx_reference"] = df.get("رقم الصفقة", pd.Series(dtype=object)).astype(str).str.strip()

    if out["region_ar"].eq("").all():
        out["region_ar"] = "الشرقية"
    return out


def main() -> None:
    default_path = Path("/Users/sarah/Desktop/بيانات ارض/صفقات عقارية/2016-2023_eastern_deals.xlsx")
    parser = argparse.ArgumentParser(
        description="استيراد صفقات 2016–2023 شرقية ودمجها مع real_sales_merged (بدون حذف من الملف الأصلي)."
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=str,
        default=str(default_path),
        help=f"مسار ملف Excel (افتراضي: {default_path})",
    )
    parser.add_argument("--no-merge", action="store_true", help="حفظ المستورد فقط دون دمج مع الملف الحالي")
    parser.add_argument("--train", action="store_true", help="إعادة تدريب موديل السعر بعد الدمج")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    print(f"جاري قراءة الملف (قراءة فقط، لا حذف): {path.name}...")
    raw = load_excel(path)
    print(f"  عدد الصفوف الخام: {len(raw):,}")

    std = normalize(raw)
    std = std[std["city_ar"].isin(ALLOWED_CITIES)].copy()
    std = std[
        std["price_per_sqm"].notna()
        & (std["price_per_sqm"] > 0)
        & std["area_sqm"].notna()
        & (std["area_sqm"] > 0)
    ].copy()
    std = std[TARGET_COLS] if all(c in std.columns for c in TARGET_COLS) else std

    before_dedup = len(std)
    std = std.drop_duplicates(subset=["tx_reference"], keep="first")
    n_dup = before_dedup - len(std)
    if n_dup > 0:
        print(f"  داخل الملف: حُذف {n_dup} صف مكرر (نفس رقم الصفقة)")
    print(f"  بعد التنظيف والفلترة: {len(std):,} صف")

    if args.no_merge:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUT_DIR / "real_sales_2016_2023_only.csv"
        std.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"\nتم حفظ المستورد فقط: {len(std):,} صف → {out_path}")
        return

    existing = pd.DataFrame()
    if MERGED_PATH.exists():
        existing = pd.read_csv(MERGED_PATH, encoding="utf-8-sig")
        for c in TARGET_COLS:
            if c not in existing.columns:
                existing[c] = pd.NA
        existing = existing[[c for c in TARGET_COLS if c in existing.columns]]
        print(f"\nالملف الحالي (المرجَع): {len(existing):,} صف")
    else:
        existing = pd.DataFrame(columns=TARGET_COLS)

    merged = pd.concat([existing, std], ignore_index=True)
    merged = merged.sort_values(["year", "quarter", "city_ar", "district_ar"], ignore_index=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    merged.to_csv(MERGED_PATH, index=False, encoding="utf-8-sig")
    print(f"\nتم الدمج (إلحاق فقط، بدون حذف من المرجَع): {len(merged):,} صف → {MERGED_PATH}")
    print(f"  منها 2016–2023 شرقية: {(merged['source'] == SOURCE_TAG).sum():,} صف")

    if args.train:
        print("\nإعادة تدريب موديل السعر...")
        import subprocess
        r = subprocess.run(["python", "-m", "scripts.train_price_model"], cwd=PROJECT_ROOT)
        if r.returncode != 0:
            print("تحذير: انتهى التدريب بخطأ.")


if __name__ == "__main__":
    main()
