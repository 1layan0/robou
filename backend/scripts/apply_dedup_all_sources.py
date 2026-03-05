#!/usr/bin/env python3
"""
تحميل الملفات المحددة، تطبيق مفتاح التكرار (سنة+ربع) على كل مصدر قبل الدمج،
ثم دمج الكل وتطبيق المفتاح على الناتج النهائي.

مفتاح التكرار: city_ar, district_ar, property_type_ar, price_total, area_sqm, source, year, quarter

الاستخدام: python scripts/apply_dedup_all_sources.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "data" / "real"
ALLOWED_CITIES = {"الدمام", "الظهران", "الخبر"}

DEDUP_SUBSET = [
    "city_ar", "district_ar", "property_type_ar", "price_total", "area_sqm",
    "source", "year", "quarter",
]
TARGET_COLS = [
    "year", "quarter", "region_ar", "city_ar", "district_ar",
    "property_type_ar", "deed_count", "price_total", "area_sqm",
    "price_per_sqm", "source", "tx_reference",
]

# مسارات الملفات (مجلد بيانات ارض على سطح المكتب)
BASE = Path("/Users/sarah/Desktop/بيانات ارض")
INPUT_FILES = [
    BASE / "الصفقات العقاريه ٢٠٢٥.xlsx",
    BASE / "صفقات عقارية" / "صفقات عقارية الخبر.numbers",
    BASE / "صفقات عقارية" / "صفقات عقارية الخبر ٢٢.numbers",
    BASE / "صفقات عقارية" / "صفقات عقارية الدمام.numbers",
    BASE / "صفقات عقارية" / "صفقات عقارية الدمام 22.numbers",
    BASE / "صفقات عقارية" / "صفقات عقارية الظهران ١.numbers",
    BASE / "صفقات عقارية" / "صفقات عقارية الظهران ٢.numbers",
    BASE / "السجل العقاري" / "سجل عقاري الدمام.numbers",
    # الخبر قد يظهر باسم "الخبر السجل العقاري .numbers" أو مشابه؛ نضيف أي .numbers في المجلد لاحقاً
    BASE / "Sales transaction indicators in the EP Q 2024E.xlsx",
    BASE / "Sales transaction indicators in the EP Q 2024E (1).xlsx",
    BASE / "Sales transaction indicators in the EP 2nd Q 2024E.xlsx",
    BASE / "Sales transaction indicators in the EP 2nd Q 2024E (1).xlsx",
    BASE / "Sales transaction indicators in the EP 3rd Q 2024E.xlsx",
    BASE / "Sales transaction indicators in the EP 3rd Q 2024E (1).xlsx",
    BASE / "Sales transaction indicators in the EP 4th Q 2024E.xlsx",
    BASE / "Sales transaction indicators in the EP 4th Q 2024E (1).xlsx",
    BASE / "اجارات الخبر والدمام (6).xlsx",
    BASE / "صفقات بيع هيئة العقار (11).xlsx",
    BASE / "صفقات بيع هيئة العقار (12).xlsx",
]
# إضافة ملف سجل عقاري الخبر إن وُجد (أسماء قد تحتوي مسافات أو حروف خاصة)
def _safelist_dir(d):
    if not d.exists():
        return []
    try:
        return list(d.iterdir())
    except Exception:
        return []


def _ep2024_quarter_from_path(path: Path) -> int:
    name = path.stem.upper()
    if "2ND" in name or "ثاني" in path.stem:
        return 2
    if "3RD" in name or "ثالث" in path.stem:
        return 3
    if "4TH" in name or "رابع" in path.stem:
        return 4
    return 1


# --- تحميل EP 2024 ---
def load_ep2024(path: Path, quarter: int) -> pd.DataFrame:
    xl = pd.ExcelFile(path)
    sheet = xl.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet)
    df = df.loc[:, ~df.columns.duplicated(keep="first")]
    df["year"] = 2024
    df["quarter"] = quarter
    return df


def normalize_ep2024(df: pd.DataFrame) -> pd.DataFrame:
    rename = {
        "السنة": "year", "الربع": "quarter", "المنطقة": "region_ar",
        "المدينة": "city_ar", "الحي": "district_ar", "نوع العقار": "property_type_ar",
        "عدد الصكوك ": "deed_count", "عدد الصكوك": "deed_count",
        "مجموع سعر العقار": "price_total", "المساحة M2": "area_sqm",
        "متوسط سعر المتر": "price_per_sqm",
    }
    out = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    out["source"] = "EP2024"
    out["tx_reference"] = ""
    out["region_ar"] = out.get("region_ar", pd.Series(dtype=object)).fillna("")
    return out


# --- تحميل 2025 ---
def load_2025(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=0, header=7)
    df["source"] = "2025"
    df["year"] = pd.to_datetime(df.get("تاريخ الصفقة ميلادي"), errors="coerce").dt.year
    df["quarter"] = pd.to_datetime(df.get("تاريخ الصفقة ميلادي"), errors="coerce").dt.quarter
    return df


def normalize_2025(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    cols = {
        "المنطقة": "region_ar", "المدينة": "city_ar", "المدينة / الحي": "district_ar",
        "الرقم المرجعي للصفقة": "tx_reference", "تاريخ الصفقة ميلادي": "tx_date",
        "تصنيف العقار": "property_type_ar", "عدد العقارات": "deed_count",
        "السعر": "price_total", "المساحة": "area_sqm",
    }
    out = df.rename(columns={k: v for k, v in cols.items() if k in df.columns})
    if "area_sqm" in out.columns and "price_total" in out.columns:
        out["price_per_sqm"] = pd.to_numeric(out["price_total"], errors="coerce") / pd.to_numeric(out["area_sqm"], errors="coerce").replace(0, pd.NA)
    else:
        out["price_per_sqm"] = pd.NA
    pt = out.get("property_type_ar", pd.Series(dtype=object)).astype(str)
    out["property_type_ar"] = pt.replace({
        "سكني": "قطعة أرض-سكنى", "تجاري": "قطعة أرض-تجارى", "زراعي": "قطعة أرض-زراعي",
        "سكني تجاري": "قطعة أرض-تجارى",
    })
    if "district_ar" in out.columns:
        def _extract_district(x):
            if pd.isna(x) or "/" not in str(x):
                return "" if pd.isna(x) else str(x).strip()
            return str(x).split("/", 1)[1].strip()
        out["district_ar"] = out["district_ar"].apply(_extract_district)
    return out


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    for c in TARGET_COLS:
        if c in df.columns:
            val = df[c]
            out[c] = val.iloc[:, 0] if isinstance(val, pd.DataFrame) else val
        else:
            out[c] = pd.NA
    return out


# --- تحميل .numbers (منصة أرض) ---
try:
    from numbers_parser import Document
except ImportError:
    Document = None


def _extract_number(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    s = str(s).strip()
    s = re.sub(r"[^\d.]", "", s)
    try:
        return float(s) if s else None
    except ValueError:
        return None


def _parse_city_district(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "", ""
    s = str(val).strip()
    if "/" in s:
        parts = s.split("/", 1)
        return parts[0].strip(), parts[1].strip()
    return s, ""


def _normalize_property_type(use, ptype):
    use = (use or "").strip()
    ptype = (ptype or "").strip()
    if "سكن" in use or "سكني" in use:
        return "قطعة أرض-سكنى"
    if "تجار" in use or "تجاري" in use:
        return "قطعة أرض-تجارى"
    if "زراع" in use:
        return "قطعة أرض-زراعي"
    if "قطعة أرض" in ptype:
        return "قطعة أرض-سكنى"
    if "شقة" in ptype:
        return "شقة"
    if "فيلا" in ptype:
        return "فيلا"
    return ptype or "قطعة أرض-سكنى"


def load_sheet_from_numbers(path: Path) -> list[dict]:
    doc = Document(str(path))
    rows_out = []
    for sheet in doc.sheets:
        for table in sheet.tables:
            rows = list(table.iter_rows())
            if not rows:
                continue
            headers = [str(c.value).strip() if c.value is not None else "" for c in rows[0]]
            for r in rows[1:]:
                cells = [c.value for c in r]
                row_dict = dict(zip(headers, cells))
                if not any(v is not None and str(v).strip() for v in row_dict.values()):
                    continue
                rows_out.append(row_dict)
    return rows_out


def to_standard_row_numbers(raw: dict, year: int = 2024, quarter: int = 1) -> dict | None:
    city_dist = raw.get("المدينة / الحي") or raw.get("المدينة") or raw.get("مدينة/حي") or ""
    city, district = _parse_city_district(city_dist)
    if not city:
        return None
    area_raw = raw.get("المساحة") or raw.get("المساحة (م2)") or raw.get("المساحة M2)") or ""
    area = _extract_number(str(area_raw))
    price_sqm_raw = raw.get("سعر المتر") or raw.get("متوسط سعر المتر") or ""
    price_sqm = _extract_number(str(price_sqm_raw))
    price_total_raw = raw.get("سعر الصفقة") or raw.get("السعر") or raw.get("مجموع سعر العقار") or ""
    price_total = _extract_number(str(price_total_raw))
    if price_sqm is None and price_total and area:
        price_sqm = price_total / area
    if price_total is None and price_sqm and area:
        price_total = price_sqm * area
    if not price_sqm or price_sqm <= 0 or not area or area <= 0:
        return None
    use = raw.get("الإستخدام") or raw.get("الاستخدام") or ""
    ptype = raw.get("نوع العقار") or raw.get("تصنيف العقار") or ""
    prop = _normalize_property_type(use, ptype)
    date_val = raw.get("التاريخ")
    if date_val:
        try:
            if isinstance(date_val, (int, float)):
                y = int(date_val)
                year = y if 2000 <= y <= 2030 else year
            else:
                dt = pd.to_datetime(date_val, errors="coerce")
                if pd.notna(dt):
                    year = dt.year
                    quarter = (dt.month - 1) // 3 + 1
        except Exception:
            pass
    return {
        "year": year,
        "quarter": quarter,
        "region_ar": "الشرقية",
        "city_ar": city,
        "district_ar": district or "_غير_محدد",
        "property_type_ar": prop,
        "deed_count": 1,
        "price_total": round(price_total, 2),
        "area_sqm": round(area, 2),
        "price_per_sqm": round(price_sqm, 2),
        "source": "منصة ارض",
        "tx_reference": str(raw.get("رقم الصفقة") or raw.get("الرقم المرجعي") or ""),
    }


# --- Excel عام (هيئة العقار / أجارات) ---
COLUMN_ALIASES = {
    "year": ["السنة", "year", "سنة"],
    "quarter": ["الربع", "quarter", "ربع"],
    "region_ar": ["المنطقة", "region", "المنطقة "],
    "city_ar": ["المدينة", "city", "مدينة"],
    "district_ar": ["الحي", "district", "حي", "المدينة / الحي", "الحي / المنطقة"],
    "property_type_ar": ["نوع العقار", "تصنيف العقار", "property_type", "type_category_ar"],
    "deed_count": ["عدد الصكوك", "عدد الصكوك ", "عدد العقارات", "deed_count", "deed_counts"],
    "price_total": ["مجموع سعر العقار", "السعر", "price_total", "السعر الإجمالي"],
    "area_sqm": ["المساحة M2", "المساحة", "area_sqm", "المساحة م٢", "المساحة (م2)"],
    "price_per_sqm": ["متوسط سعر المتر", "سعر المتر", "price_per_sqm", "Meter_Price_W_Avg_IQR"],
    "tx_reference": ["الرقم المرجعي", "tx_reference", "رقم الصفقة", "الرقم المرجعي للصفقة"],
}


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    rename = {}
    for std_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df.columns:
                rename[alias] = std_name
                break
    return df.rename(columns=rename)


def load_generic_excel(path: Path, source_tag: str) -> pd.DataFrame | None:
    try:
        df = pd.read_excel(path, sheet_name=0)
    except Exception as e:
        print(f"  تحذير: تعذر قراءة {path.name}: {e}")
        return None
    if df.empty or len(df.columns) < 3:
        return None
    df = normalize_column_names(df)
    out = pd.DataFrame()
    for c in TARGET_COLS:
        if c in df.columns:
            out[c] = df[c]
        else:
            out[c] = pd.NA
    out["source"] = source_tag
    out["region_ar"] = out.get("region_ar", pd.Series(dtype=object)).fillna("الشرقية")
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out["quarter"] = pd.to_numeric(out["quarter"], errors="coerce")
    out["deed_count"] = pd.to_numeric(out["deed_count"], errors="coerce").fillna(1).astype("Int64")
    out["price_total"] = pd.to_numeric(out["price_total"], errors="coerce")
    out["area_sqm"] = pd.to_numeric(out["area_sqm"], errors="coerce")
    if out["price_per_sqm"].isna().all() and "price_total" in out.columns and "area_sqm" in out.columns:
        out["price_per_sqm"] = out["price_total"] / out["area_sqm"].replace(0, pd.NA)
    else:
        out["price_per_sqm"] = pd.to_numeric(out["price_per_sqm"], errors="coerce")
    out["property_type_ar"] = out.get("property_type_ar", pd.Series(dtype=object)).astype(str).replace({
        "سكني": "قطعة أرض-سكنى", "تجاري": "قطعة أرض-تجارى", "زراعي": "قطعة أرض-زراعي",
        "سكني تجاري": "قطعة أرض-تجارى", "nan": "",
    })
    return out


def apply_dedup(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """تطبيق المفتاح الجديد وإرجاع (إطار بعد الحذف، عدد المحذوف)."""
    for c in DEDUP_SUBSET:
        if c not in df.columns:
            df = df.copy()
            df[c] = pd.NA
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    df["quarter"] = pd.to_numeric(df["quarter"], errors="coerce").fillna(0).astype(int)
    before = len(df)
    df = df.drop_duplicates(subset=DEDUP_SUBSET, keep="first")
    return df, before - len(df)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_dfs = []
    report_per_source = []

    # إضافة ملفات سجل عقاري الخبر إن وُجدت
    extra_numbers = []
    sjel_dir = BASE / "السجل العقاري"
    for f in _safelist_dir(sjel_dir):
        if f.suffix.lower() == ".numbers" and "الخبر" in f.stem:
            extra_numbers.append(f)
    for p in extra_numbers:
        if p not in INPUT_FILES:
            INPUT_FILES.append(p)

    for path in INPUT_FILES:
        if not path.exists():
            print(f"تخطي (غير موجود): {path}")
            continue
        suf = path.suffix.lower()
        name = path.name

        # --- EP 2024 ---
        if "2024" in name and "EP" in name and suf == ".xlsx":
            q = _ep2024_quarter_from_path(path)
            try:
                df = load_ep2024(path, q)
                df = normalize_ep2024(df)
                df = standardize_columns(df)
            except Exception as e:
                print(f"خطأ في {name}: {e}")
                continue
            df["city_ar"] = df["city_ar"].fillna("").astype(str).str.strip()
            df = df[df["city_ar"].isin(ALLOWED_CITIES)]
            if df.empty:
                continue
            df, n_rem = apply_dedup(df)
            all_dfs.append(df)
            report_per_source.append((f"EP2024 Q{q} ({name})", len(df), n_rem))
            print(f"EP2024 Q{q} ({name}): {len(df)} صف (حُذف {n_rem} مكرر)")
            continue

        # --- 2025 ---
        if "٢٠٢٥" in name or "2025" in name:
            if suf != ".xlsx":
                continue
            try:
                df = load_2025(path)
                df = normalize_2025(df)
                df = standardize_columns(df)
                df = df[df["price_per_sqm"].notna() & (df["price_per_sqm"] > 0)]
            except Exception as e:
                print(f"خطأ في {name}: {e}")
                continue
            df["city_ar"] = df["city_ar"].fillna("").astype(str).str.strip()
            df = df[df["city_ar"].isin(ALLOWED_CITIES)]
            if df.empty:
                continue
            df, n_rem = apply_dedup(df)
            all_dfs.append(df)
            report_per_source.append((f"2025 ({name})", len(df), n_rem))
            print(f"2025 ({name}): {len(df)} صف (حُذف {n_rem} مكرر)")
            continue

        # --- .numbers (منصة أرض) ---
        if suf == ".numbers":
            if Document is None:
                print("تخطي .numbers (ثبّت: pip install numbers-parser)")
                continue
            try:
                raw_rows = load_sheet_from_numbers(path)
                rows = []
                for raw in raw_rows:
                    row = to_standard_row_numbers(raw)
                    if row and row["city_ar"] in ALLOWED_CITIES:
                        rows.append(row)
                if not rows:
                    continue
                df = pd.DataFrame(rows)
            except Exception as e:
                print(f"خطأ في {name}: {e}")
                continue
            df, n_rem = apply_dedup(df)
            all_dfs.append(df)
            report_per_source.append((f"منصة ارض ({name})", len(df), n_rem))
            print(f"منصة ارض ({name}): {len(df)} صف (حُذف {n_rem} مكرر)")
            continue

        # --- هيئة العقار / أجارات (Excel عام) ---
        if suf in (".xlsx", ".xls"):
            tag = "هيئة العقار" if "هيئة" in name or "صفقات بيع" in name else "أجارات"
            df = load_generic_excel(path, tag)
            if df is None:
                continue
            df["city_ar"] = df["city_ar"].fillna("").astype(str).str.strip()
            df = df[df["city_ar"].isin(ALLOWED_CITIES)]
            df = df[df["price_per_sqm"].notna() & (df["price_per_sqm"] > 0) & df["area_sqm"].notna() & (df["area_sqm"] > 0)]
            if df.empty:
                print(f"  {name}: لا صفوف صالحة بعد الفلترة")
                continue
            df["district_ar"] = df["district_ar"].fillna("").astype(str).str.strip().replace("nan", "")
            df.loc[df["district_ar"] == "", "district_ar"] = "_غير_محدد"
            df, n_rem = apply_dedup(df)
            all_dfs.append(df)
            report_per_source.append((f"{tag} ({name})", len(df), n_rem))
            print(f"{tag} ({name}): {len(df)} صف (حُذف {n_rem} مكرر)")

    if not all_dfs:
        print("لا توجد بيانات للدمج.")
        return 1

    # دمج كل المصادر
    for c in TARGET_COLS:
        for d in all_dfs:
            if c not in d.columns:
                d[c] = pd.NA
    merged = pd.concat([d[TARGET_COLS] for d in all_dfs], ignore_index=True)
    merged["city_ar"] = merged["city_ar"].fillna("").astype(str).str.strip()
    merged["district_ar"] = merged["district_ar"].fillna("").astype(str).str.strip().replace("nan", "")
    merged["property_type_ar"] = merged["property_type_ar"].fillna("").astype(str).str.strip()
    merged["price_per_sqm"] = pd.to_numeric(merged["price_per_sqm"], errors="coerce")
    merged = merged[merged["city_ar"].str.len() > 0]
    merged = merged[merged["city_ar"].isin(ALLOWED_CITIES)]

    before_final = len(merged)
    merged, n_removed_final = apply_dedup(merged)
    merged = merged.sort_values(["year", "quarter", "city_ar", "district_ar"], ignore_index=True)

    out_csv = OUT_DIR / "real_sales_merged.csv"
    merged.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"\nتم الدمج: {len(merged)} صف → {out_csv}")

    report_lines = [
        "تقرير إزالة التكرار (dedup) — apply_dedup_all_sources",
        f"مفتاح التكرار: {', '.join(DEDUP_SUBSET)}",
        "",
        "--- كل مصدر (قبل الدمج النهائي) ---",
    ]
    for label, count, rem in report_per_source:
        report_lines.append(f"  {label}: {count} صف بعد حذف {rem} مكرر")
    report_lines.extend([
        "",
        "--- الدمج النهائي ---",
        f"قبل الحذف النهائي: {before_final} صف | بعد: {len(merged)} صف | المحذوف: {n_removed_final} صف",
    ])
    report_path = OUT_DIR / "dedup_report.txt"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"تقرير: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
