#!/usr/bin/env python3
"""
استيراد بيانات منصة أرض (صفقات عقارية + سجل عقاري) ودمجها مع real_sales_merged.

الملفات الأصلية .numbers — صدّرها أولاً إلى Excel أو CSV من Numbers:
  File → Export To → Excel أو CSV، ثم ضع الملفات في مجلد واحد.

الاستخدام:
  python scripts/ingest_ard_platform_data.py --dir "/Users/sarah/Desktop/بيانات ارض/صفقات عقارية"
  python scripts/ingest_ard_platform_data.py --dir data/raw/ard_export
  python scripts/ingest_ard_platform_data.py --files file1.xlsx file2.csv

المصدر في العمود source يُحفظ كـ "منصة ارض".
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "data" / "real"
MERGED_PATH = OUT_DIR / "real_sales_merged.csv"
SOURCE_TAG = "منصة ارض"
ALLOWED_CITIES = {"الدمام", "الظهران", "الخبر"}
TARGET_COLS = [
    "year", "quarter", "region_ar", "city_ar", "district_ar",
    "property_type_ar", "deed_count", "price_total", "area_sqm",
    "price_per_sqm", "source", "tx_reference",
]

# مفتاح التكرار: نفس الصفقة = نفس (مدينة، حي، نوع، سعر، مساحة، مصدر، سنة، ربع)
DEDUP_SUBSET = [
    "city_ar", "district_ar", "property_type_ar", "price_total", "area_sqm",
    "source", "year", "quarter",
]
REPORT_PATH = OUT_DIR / "dedup_report.txt"

# توحيد أسماء الأعمدة المحتملة من منصة أرض أو تصدير Numbers
COLUMN_ALIASES = {
    "year": ["السنة", "year", "سنة"],
    "quarter": ["الربع", "quarter", "ربع"],
    "region_ar": ["المنطقة", "region", "المنطقة "],
    "city_ar": ["المدينة", "city", "مدينة"],
    "district_ar": ["الحي", "district", "حي", "المدينة / الحي", "الحي / المنطقة"],
    "property_type_ar": ["نوع العقار", "تصنيف العقار", "property_type", "نوع العقار"],
    "deed_count": ["عدد الصكوك", "عدد الصكوك ", "عدد العقارات", "deed_count"],
    "price_total": ["مجموع سعر العقار", "السعر", "price_total", "السعر الإجمالي"],
    "area_sqm": ["المساحة M2", "المساحة", "area_sqm", "المساحة م٢", "المساحة (م2)"],
    "price_per_sqm": ["متوسط سعر المتر", "سعر المتر", "price_per_sqm"],
    "tx_reference": ["الرقم المرجعي", "tx_reference", "رقم الصفقة", "الرقم المرجعي للصفقة"],
}


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """ربط أعمدة الملف بأسماءنا المعيارية."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    rename = {}
    for std_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df.columns:
                rename[alias] = std_name
                break
    df = df.rename(columns=rename)
    return df


def is_ard_coded_headers(df: pd.DataFrame) -> bool:
    """هل الأعمدة بصيغة رموز منصة أرض (p-1, p-1 2, ...)؟"""
    cols = [str(c).strip() for c in df.columns]
    # نعتبر الملف «مشفر» إذا وجد عمود مثل p-1 2 أو p-1 3 وليس لدينا أسماء عربية معروفة
    has_p_style = any(re.match(r"^p-1(\s+\d+)?$", c) for c in cols)
    known_arabic = any(
        a in cols
        for aliases in COLUMN_ALIASES.values()
        for a in aliases
        if isinstance(a, str) and any("\u0600" <= ch <= "\u06FF" for ch in a)
    )
    return bool(has_p_style and not known_arabic)


def _parse_number_from_text(val, _pattern: str = "") -> float | None:
    """استخراج رقم من نص مثل '161 م²' أو '1361 ر.س'."""
    if pd.isna(val):
        return None
    s = str(val).strip()
    # إزالة الآلاف (فواصل أو مسافات) ثم استخراج الرقم
    s = re.sub(r"[\s,]+\d{3}(?=\d|\s|$)", "", s)  # لا نحذف كل المسافات
    m = re.search(r"[\d.]+", s)
    if m:
        try:
            return float(m.group().replace(",", "."))
        except ValueError:
            return None
    return None


def _parse_date_to_year_quarter(val) -> tuple[int | None, int | None]:
    """من '2023/01/01' أو '2023-01-15' نرجع (سنة، ربع)."""
    if pd.isna(val):
        return None, None
    s = str(val).strip()
    m = re.match(r"(\d{4})[/-](\d{1,2})", s)
    if m:
        y = int(m.group(1))
        month = int(m.group(2))
        q = (month - 1) // 3 + 1
        return y, q
    return None, None


def _split_city_district(val) -> tuple[str, str]:
    """من 'الدمام / الخليج' نرجع (الدمام، الخليج)."""
    if pd.isna(val):
        return "", ""
    s = str(val).strip()
    if " / " in s:
        parts = s.split(" / ", 1)
        return parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "")
    return s, ""


def _normalize_property_type(val) -> str:
    """توحيد نوع العقار مع التصنيف المعتمد."""
    if pd.isna(val):
        return ""
    s = str(val).strip().lower()
    mapping = {
        "سكني": "قطعة أرض-سكنى",
        "تجاري": "قطعة أرض-تجارى",
        "زراعي": "قطعة أرض-زراعي",
    }
    for key, out in mapping.items():
        if key in s or key.replace("ي", "ى") in s:
            return out
    return "قطعة أرض-سكنى" if s else ""


def ard_coded_to_standard(df: pd.DataFrame, source: str = SOURCE_TAG) -> pd.DataFrame:
    """
    تحويل ملف منصة أرض ذي هيدرز رموز (p-1, p-1 2, ...) إلى الصيغة المعيارية.
    لا يحذف صفوفاً؛ الفلترة (مدن مسموحة، سعر/مساحة موجب) تُطبّق لاحقاً في main.
    """
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # إبقاء الأعمدة ذات الصلة فقط (تجاهل disabled:grayscale src وغيرها)
    main_cols = [c for c in df.columns if re.match(r"^p-1(\s+\d+)?$", c)]
    if not main_cols:
        return pd.DataFrame(columns=TARGET_COLS)

    df = df[main_cols].copy()

    # تسمية موحدة حسب الموضع: قد يكون الملف فيه منطقة (p-1) أو بدونه (أول عمود = مدينة/حي)
    has_region = "p-1" in df.columns and "p-1 2" in df.columns
    idx_region = main_cols.index("p-1") if has_region else None
    idx_city_district = main_cols.index("p-1 2")
    idx_date = main_cols.index("p-1 3") if "p-1 3" in main_cols else None
    idx_tx_ref = main_cols.index("p-1 4") if "p-1 4" in main_cols else None
    idx_property_type = main_cols.index("p-1 7") if "p-1 7" in main_cols else None
    idx_area = main_cols.index("p-1 9") if "p-1 9" in main_cols else None
    idx_price_sqm = main_cols.index("p-1 10") if "p-1 10" in main_cols else None
    idx_price_total = main_cols.index("p-1 11") if "p-1 11" in main_cols else None

    out = pd.DataFrame()
    n = len(df)
    default_region = "الشرقية"

    if idx_region is not None:
        out["region_ar"] = df.iloc[:, idx_region].fillna("").astype(str).str.strip().replace("", default_region).tolist()
    else:
        out["region_ar"] = [default_region] * n

    city_district = df.iloc[:, idx_city_district].fillna("").astype(str)
    out["city_ar"] = city_district.apply(lambda v: _split_city_district(v)[0])
    out["district_ar"] = city_district.apply(lambda v: _split_city_district(v)[1])

    if idx_date is not None:
        dates = df.iloc[:, idx_date]
        out["year"] = [_parse_date_to_year_quarter(v)[0] for v in dates]
        out["quarter"] = [_parse_date_to_year_quarter(v)[1] for v in dates]
    else:
        out["year"] = [None] * n
        out["quarter"] = [None] * n

    out["tx_reference"] = df.iloc[:, idx_tx_ref].astype(object) if idx_tx_ref is not None else [None] * n
    out["property_type_ar"] = (
        df.iloc[:, idx_property_type].apply(_normalize_property_type)
        if idx_property_type is not None
        else [""] * n
    )
    out["deed_count"] = 1

    if idx_area is not None:
        out["area_sqm"] = [_parse_number_from_text(v, "area") for v in df.iloc[:, idx_area]]
    else:
        out["area_sqm"] = [None] * n
    if idx_price_sqm is not None:
        out["price_per_sqm"] = [_parse_number_from_text(v, "price") for v in df.iloc[:, idx_price_sqm]]
    else:
        out["price_per_sqm"] = [None] * n
    if idx_price_total is not None:
        out["price_total"] = [_parse_number_from_text(v, "price") for v in df.iloc[:, idx_price_total]]
    else:
        out["price_total"] = [None] * n

    # حساب سعر المتر إذا كان مفقوداً والمساحة والسعر الإجمالي موجودان
    for i in range(n):
        pq = out["price_per_sqm"].iloc[i]
        pt = out["price_total"].iloc[i]
        ar = out["area_sqm"].iloc[i]
        if (pq is None or pq == 0) and pt and ar and ar > 0:
            out.iat[i, out.columns.get_loc("price_per_sqm")] = pt / ar

    out["source"] = source

    for c in TARGET_COLS:
        if c not in out.columns:
            out[c] = pd.NA
    out = out[TARGET_COLS]
    return out


def load_file(path: Path) -> pd.DataFrame | None:
    """تحميل ملف Excel أو CSV."""
    path = Path(path)
    if not path.exists():
        return None
    suf = path.suffix.lower()
    try:
        if suf == ".csv":
            df = pd.read_csv(path, encoding="utf-8-sig")
        elif suf in (".xlsx", ".xls"):
            df = pd.read_excel(path, sheet_name=0)
        else:
            return None
    except Exception as e:
        print(f"  تحذير: تعذر قراءة {path.name}: {e}")
        return None
    if df.empty or len(df.columns) < 3:
        return None
    return df


def to_standard_schema(df: pd.DataFrame, source: str = SOURCE_TAG) -> pd.DataFrame:
    """تحويل إلى الصيغة المعيارية مع إضافة المصدر."""
    df = normalize_column_names(df)
    out = pd.DataFrame()
    for c in TARGET_COLS:
        if c in df.columns:
            out[c] = df[c]
        else:
            out[c] = pd.NA
    out["source"] = source
    if "region_ar" not in df.columns or out["region_ar"].isna().all():
        out["region_ar"] = "الشرقية"
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out["quarter"] = pd.to_numeric(out["quarter"], errors="coerce")
    out["deed_count"] = pd.to_numeric(out["deed_count"], errors="coerce").fillna(1).astype("Int64")
    out["price_total"] = pd.to_numeric(out["price_total"], errors="coerce")
    out["area_sqm"] = pd.to_numeric(out["area_sqm"], errors="coerce")
    if out["price_per_sqm"].isna().all() and "price_total" in out.columns and "area_sqm" in out.columns:
        out["price_per_sqm"] = out["price_total"] / out["area_sqm"].replace(0, pd.NA)
    else:
        out["price_per_sqm"] = pd.to_numeric(out["price_per_sqm"], errors="coerce")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="استيراد بيانات منصة أرض ودمجها مع real_sales_merged")
    parser.add_argument("--dir", type=str, help="مجلد يحتوي ملفات Excel أو CSV (بعد التصدير من Numbers)")
    parser.add_argument("--files", nargs="+", type=str, help="قائمة مسارات ملفات")
    parser.add_argument("--no-merge", action="store_true", help="حفظ المستورد فقط دون دمج مع الملف الحالي")
    parser.add_argument("--train", action="store_true", help="إعادة تدريب الموديل بعد الدمج")
    args = parser.parse_args()

    paths = []
    if args.dir:
        d = Path(args.dir)
        if d.is_dir():
            for ext in ("*.xlsx", "*.xls", "*.csv"):
                paths.extend(d.glob(ext))
    if args.files:
        for f in args.files:
            p = Path(f)
            if p.is_absolute() or not p.exists():
                p = PROJECT_ROOT / f
            if p.exists():
                paths.append(p)

    paths = sorted(set(paths))
    if not paths:
        print("لم يُعثر على ملفات. استخدم --dir أو --files.")
        print("تذكير: صدّر ملفات .numbers إلى Excel أو CSV من Numbers ثم حدد المجلد.")
        return

    print(f"جاري قراءة {len(paths)} ملف...")
    frames = []
    for p in paths:
        df = load_file(p)
        if df is not None:
            if is_ard_coded_headers(df):
                std = ard_coded_to_standard(df)
                print(f"  {p.name}: هيدرز رموز (p-1…) → تم التحويل بالموقع")
            else:
                std = to_standard_schema(df)
            std = std[std["city_ar"].fillna("").astype(str).str.strip().isin(ALLOWED_CITIES)]
            std = std[std["price_per_sqm"].notna() & (std["price_per_sqm"] > 0) & std["area_sqm"].notna() & (std["area_sqm"] > 0)]
            if len(std) > 0:
                frames.append(std)
                print(f"  {p.name}: {len(std)} صف صالح")
    if not frames:
        print("لا توجد صفوف صالحة بعد الفلترة.")
        return

    combined = pd.concat(frames, ignore_index=True)
    combined["city_ar"] = combined["city_ar"].fillna("").astype(str).str.strip()
    combined["district_ar"] = combined["district_ar"].fillna("").astype(str).str.strip().replace("nan", "")
    combined["property_type_ar"] = combined["property_type_ar"].fillna("").astype(str).str.strip()
    combined["property_type_ar"] = combined["property_type_ar"].replace({
        "سكني": "قطعة أرض-سكنى", "تجاري": "قطعة أرض-تجارى", "زراعي": "قطعة أرض-زراعي",
        "سكني تجاري": "قطعة أرض-تجارى",
    })
    combined.loc[combined["district_ar"] == "", "district_ar"] = "_غير_محدد"

    # تطبيق المفتاح الجديد على البيانات المستوردة فقط (قبل الدمج)
    combined["year"] = pd.to_numeric(combined["year"], errors="coerce").fillna(0).astype(int)
    combined["quarter"] = pd.to_numeric(combined["quarter"], errors="coerce").fillna(0).astype(int)
    before_incoming = len(combined)
    removed_incoming = combined[combined.duplicated(subset=DEDUP_SUBSET, keep="first")]
    combined = combined.drop_duplicates(subset=DEDUP_SUBSET, keep="first")
    n_removed_incoming = len(removed_incoming)
    if n_removed_incoming > 0:
        print(f"\nمن البيانات المستوردة فقط: حُذف {n_removed_incoming} صف مكرر (مفتاح: سنة+ربع)")

    if args.no_merge:
        out_path = OUT_DIR / "real_sales_ard_only.csv"
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        combined.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"\nتم حفظ المستورد فقط: {len(combined)} صف → {out_path}")
        return

    # دمج مع الملف الحالي
    existing = pd.DataFrame()
    if MERGED_PATH.exists():
        existing = pd.read_csv(MERGED_PATH, encoding="utf-8-sig")
        print(f"\nالملف الحالي: {len(existing)} صف")
    for c in TARGET_COLS:
        if c not in existing.columns:
            existing[c] = pd.NA

    merged = pd.concat([existing, combined], ignore_index=True)
    for c in DEDUP_SUBSET:
        if c not in merged.columns:
            merged[c] = pd.NA
    merged["year"] = pd.to_numeric(merged["year"], errors="coerce")
    merged["quarter"] = pd.to_numeric(merged["quarter"], errors="coerce")
    merged["year"] = merged["year"].fillna(0).astype(int)
    merged["quarter"] = merged["quarter"].fillna(0).astype(int)

    before_count = len(merged)
    removed = merged[merged.duplicated(subset=DEDUP_SUBSET, keep="first")]
    merged = merged.drop_duplicates(subset=DEDUP_SUBSET, keep="first")
    removed_count = len(removed)

    # تقرير الحذف (يشمل: من المستورد فقط + من الدمج الكامل)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report_lines = [
        "تقرير إزالة التكرار (dedup) — ingest_ard_platform_data",
        f"مفتاح التكرار: {', '.join(DEDUP_SUBSET)}",
        "",
        "1) من البيانات المستوردة فقط (قبل الدمج):",
        f"   قبل: {before_incoming} صف | بعد: {len(combined)} صف | محذوف: {n_removed_incoming} صف",
    ]
    if n_removed_incoming > 0:
        report_lines.append("   --- محذوف لكل مدينة ---")
        for city, n in removed_incoming.groupby("city_ar", dropna=False).size().items():
            report_lines.append(f"     {city}: {n}")
        report_lines.append("   --- محذوف لكل حي ---")
        for (city, district), n in removed_incoming.groupby(["city_ar", "district_ar"], dropna=False).size().sort_values(ascending=False).items():
            report_lines.append(f"     {city} | {district}: {n}")
    report_lines.extend([
        "",
        "2) من الدمج الكامل (موجود + مستورد):",
        f"   قبل الحذف: {before_count} صف | بعد الحذف: {len(merged)} صف | المحذوف: {removed_count} صف",
        "",
        "--- عدد الصفوف المحذوفة لكل مدينة ---",
    ])
    if removed_count > 0:
        by_city = removed.groupby("city_ar", dropna=False).size()
        for city, n in by_city.items():
            report_lines.append(f"  {city}: {n}")
        report_lines.append("")
        report_lines.append("--- عدد الصفوف المحذوفة لكل حي (مدينة - حي) ---")
        by_district = removed.groupby(["city_ar", "district_ar"], dropna=False).size().sort_values(ascending=False)
        for (city, district), n in by_district.items():
            report_lines.append(f"  {city} | {district}: {n}")
        report_lines.append("")
        report_lines.append("ملاحظة: إذا ظهر حي بعدد حذف كبير، راجع rounding السعر/المساحة أو مفاتيح الزمن (سنة/ربع).")
    else:
        report_lines.append("  لا يوجد صفوف محذوفة.")
    report_text = "\n".join(report_lines)
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    print(report_text)
    print(f"\nتم حفظ التقرير: {REPORT_PATH}")

    merged = merged.sort_values(["year", "quarter", "city_ar", "district_ar"], ignore_index=True)
    merged.to_csv(MERGED_PATH, index=False, encoding="utf-8-sig")
    print(f"\nتم الدمج: {len(merged)} صف إجمالاً → {MERGED_PATH}")
    print(f"  منها منصة أرض: {(merged['source'] == SOURCE_TAG).sum()} صف")

    if args.train:
        print("\nإعادة تدريب الموديل...")
        import subprocess
        r = subprocess.run(["python", "-m", "scripts.train_price_model"], cwd=PROJECT_ROOT)
        if r.returncode != 0:
            print("تحذير: انتهى التدريب بخطأ.")


if __name__ == "__main__":
    main()
