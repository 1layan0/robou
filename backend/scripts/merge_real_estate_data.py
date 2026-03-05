#!/usr/bin/env python3
"""
دمج بيانات العقار الحقيقية: EP 2024 (4 أرباع) + صفقات 2025.
التركيز: الدمام، الظهران، الخبر فقط.

الاستخدام: python scripts/merge_real_estate_data.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "data" / "real"

# المدن المدعومة فقط
ALLOWED_CITIES = {"الدمام", "الظهران", "الخبر"}

# EP 2024 - أربعة ملفات (بدون المكرر)
EP_2024_FILES = [
    "/Users/sarah/Downloads/Sales transaction indicators in the EP Q 2024E.xlsx",
    "/Users/sarah/Downloads/Sales transaction indicators in the EP 2nd Q 2024E.xlsx",
    "/Users/sarah/Downloads/Sales transaction indicators in the EP 3rd Q 2024E.xlsx",
    "/Users/sarah/Downloads/Sales transaction indicators in the EP 4th Q 2024E.xlsx",
]
EP_2024_QUARTERS = [1, 2, 3, 4]

# صفقات 2025
FILE_2025 = "/Users/sarah/Desktop/الصفقات العقاريه ٢٠٢٥.xlsx"


def load_ep2024(path: str, quarter: int) -> pd.DataFrame:
    """تحميل ملف ربع واحد من EP 2024."""
    xl = pd.ExcelFile(path)
    sheet = xl.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet)
    df = df.loc[:, ~df.columns.duplicated(keep="first")]
    df["year"] = 2024
    df["quarter"] = quarter
    return df


def normalize_ep2024(df: pd.DataFrame) -> pd.DataFrame:
    """توحيد أعمدة EP 2024."""
    rename = {
        "السنة": "year",
        "الربع": "quarter",
        "المنطقة": "region_ar",
        "المدينة": "city_ar",
        "الحي": "district_ar",
        "نوع العقار": "property_type_ar",
        "عدد الصكوك ": "deed_count",
        "عدد الصكوك": "deed_count",
        "مجموع سعر العقار": "price_total",
        "المساحة M2": "area_sqm",
        "متوسط سعر المتر": "price_per_sqm",
    }
    out = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    out["source"] = "EP2024"
    out["tx_reference"] = ""
    out["region_ar"] = out.get("region_ar", "")
    return out


def load_2025(path: str) -> pd.DataFrame:
    """تحميل صفقات 2025 (هيدر في السطر 7)."""
    df = pd.read_excel(path, sheet_name=0, header=7)
    df["source"] = "2025"
    df["year"] = pd.to_datetime(df.get("تاريخ الصفقة ميلادي"), errors="coerce").dt.year
    df["quarter"] = pd.to_datetime(df.get("تاريخ الصفقة ميلادي"), errors="coerce").dt.quarter
    return df


def normalize_2025(df: pd.DataFrame) -> pd.DataFrame:
    """توحيد أعمدة 2025."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    cols = {
        "المنطقة": "region_ar",
        "المدينة": "city_ar",
        "المدينة / الحي": "district_ar",
        "الرقم المرجعي للصفقة": "tx_reference",
        "تاريخ الصفقة ميلادي": "tx_date",
        "تصنيف العقار": "property_type_ar",
        "عدد العقارات": "deed_count",
        "السعر": "price_total",
        "المساحة": "area_sqm",
    }
    out = df.rename(columns={k: v for k, v in cols.items() if k in df.columns})
    if "area_sqm" in out.columns and "price_total" in out.columns:
        out["price_per_sqm"] = pd.to_numeric(out["price_total"], errors="coerce") / pd.to_numeric(out["area_sqm"], errors="coerce").replace(0, pd.NA)
    else:
        out["price_per_sqm"] = pd.NA
    pt = out.get("property_type_ar", pd.Series(dtype=object)).astype(str)
    out["property_type_ar"] = pt.replace({
        "سكني": "قطعة أرض-سكنى", "تجاري": "قطعة أرض-تجارى", "زراعي": "قطعة أرض-زراعي",
        "سكني تجاري": "قطعة أرض-تجارى"
    })
    # استخراج الحي من "المدينة / الحي" إن وُجد
    if "district_ar" in out.columns:
        def _extract_district(x):
            if pd.isna(x) or "/" not in str(x):
                return "" if pd.isna(x) else str(x).strip()
            return str(x).split("/", 1)[1].strip()
        out["district_ar"] = out["district_ar"].apply(_extract_district)
    return out


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """عمود موحّد للتدريب."""
    keep = ["year", "quarter", "region_ar", "city_ar", "district_ar", "property_type_ar", "deed_count", "price_total", "area_sqm", "price_per_sqm", "source", "tx_reference"]
    out = pd.DataFrame()
    for c in keep:
        if c in df.columns:
            val = df[c]
            out[c] = val.iloc[:, 0] if isinstance(val, pd.DataFrame) else val
        else:
            out[c] = pd.NA
    return out


def expand_aggregated(df: pd.DataFrame) -> pd.DataFrame:
    """توسيع الصفوف المجمّعة إلى صفوف فردية (أكبر قدر بيانات)."""
    rows = []
    for _, r in df.iterrows():
        ppq = pd.to_numeric(r.get("price_per_sqm"), errors="coerce")
        if pd.isna(ppq) or ppq <= 0:
            continue
        n = int(pd.to_numeric(r.get("deed_count"), errors="coerce") or 1)
        n = max(1, min(n, 100))
        area = pd.to_numeric(r.get("area_sqm"), errors="coerce")
        total = pd.to_numeric(r.get("price_total"), errors="coerce")
        area_avg = (total / (ppq * n)) if ppq and n and total else 500
        if pd.isna(area_avg) or area_avg <= 0:
            area_avg = 500
        for _ in range(n):
            rows.append({
                "year": r.get("year"),
                "quarter": r.get("quarter"),
                "region_ar": r.get("region_ar", ""),
                "city_ar": r.get("city_ar", ""),
                "district_ar": r.get("district_ar", ""),
                "property_type_ar": r.get("property_type_ar", ""),
                "deed_count": 1,
                "price_total": (ppq * area_avg) if not pd.isna(area_avg) else ppq * 500,
                "area_sqm": area_avg,
                "price_per_sqm": ppq,
                "source": r.get("source", "EP2024"),
                "tx_reference": r.get("tx_reference", ""),
            })
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_dfs = []

    # 1) EP 2024
    for path, q in zip(EP_2024_FILES, EP_2024_QUARTERS):
        p = Path(path)
        if p.exists():
            try:
                df = load_ep2024(str(p), q)
                df = normalize_ep2024(df)
                df = standardize_columns(df)
                all_dfs.append(df)
                print(f"EP 2024 Q{q}: {len(df)} صف")
            except Exception as e:
                print(f"خطأ في {p.name}: {e}")
        else:
            print(f"غير موجود: {path}")

    # 2) 2025
    if Path(FILE_2025).exists():
        try:
            df = load_2025(FILE_2025)
            df = normalize_2025(df)
            df = standardize_columns(df)
            df = df[df["price_per_sqm"].notna() & (df["price_per_sqm"] > 0)]
            all_dfs.append(df)
            print(f"2025: {len(df)} صف")
        except Exception as e:
            print(f"خطأ في 2025: {e}")

    if not all_dfs:
        print("لا توجد بيانات للدمج.")
        return

    # دمج (أعمدة موحّدة)
    target_cols = ["year","quarter","region_ar","city_ar","district_ar","property_type_ar","deed_count","price_total","area_sqm","price_per_sqm","source","tx_reference"]
    clean_dfs = []
    for d in all_dfs:
        d = d.copy()
        d = d.loc[:, ~d.columns.duplicated()]
        for c in target_cols:
            if c not in d.columns:
                d[c] = pd.NA
        clean_dfs.append(d[target_cols])
    merged = pd.concat(clean_dfs, ignore_index=True)

    # تنضيف
    merged["city_ar"] = merged["city_ar"].fillna("").astype(str).str.strip()
    merged["district_ar"] = merged["district_ar"].fillna("").astype(str).str.strip().replace("nan", "")
    merged["property_type_ar"] = merged["property_type_ar"].fillna("").astype(str).str.strip()
    merged["price_per_sqm"] = pd.to_numeric(merged["price_per_sqm"], errors="coerce")
    merged = merged[merged["city_ar"].str.len() > 0]

    # فلترة: الدمام، الظهران، الخبر فقط
    merged = merged[merged["city_ar"].isin(ALLOWED_CITIES)].copy()
    print(f"بعد الفلترة (الدمام+الظهران+الخبر): {len(merged)} صف")

    # إزالة التكرار بمفتاح (مدينة، حي، نوع، سعر، مساحة، مصدر، سنة، ربع)
    DEDUP_SUBSET = [
        "city_ar", "district_ar", "property_type_ar", "price_total", "area_sqm",
        "source", "year", "quarter",
    ]
    merged["year"] = pd.to_numeric(merged["year"], errors="coerce").fillna(0).astype(int)
    merged["quarter"] = pd.to_numeric(merged["quarter"], errors="coerce").fillna(0).astype(int)
    before_dedup = len(merged)
    removed = merged[merged.duplicated(subset=DEDUP_SUBSET, keep="first")]
    merged = merged.drop_duplicates(subset=DEDUP_SUBSET, keep="first")
    n_removed = len(removed)
    if n_removed > 0:
        print(f"إزالة تكرار (EP2024+2025): حُذف {n_removed} صف")
        report_path = OUT_DIR / "dedup_report_merge.txt"
        lines = [
            "تقرير إزالة التكرار — merge_real_estate_data (EP2024 + 2025)",
            f"مفتاح: {', '.join(DEDUP_SUBSET)}",
            f"قبل: {before_dedup} | بعد: {len(merged)} | محذوف: {n_removed}",
            "",
            "--- محذوف لكل مدينة ---",
        ]
        for city, c in removed.groupby("city_ar", dropna=False).size().items():
            lines.append(f"  {city}: {c}")
        lines.append("")
        lines.append("--- محذوف لكل حي ---")
        for (c, d), n in removed.groupby(["city_ar", "district_ar"], dropna=False).size().sort_values(ascending=False).items():
            lines.append(f"  {c} | {d}: {n}")
        report_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  تقرير: {report_path}")

    # حفظ الموحّد (بدون توسيع)
    merged_out = OUT_DIR / "real_sales_merged.csv"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    merged.to_csv(merged_out, index=False, encoding="utf-8-sig")
    print(f"\nتم الدمج: {len(merged)} صف → {merged_out}")


if __name__ == "__main__":
    main()
