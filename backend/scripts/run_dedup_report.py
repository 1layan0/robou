#!/usr/bin/env python3
"""
تطبيق مفتاح التكرار الجديد (مع السنة والربع) على real_sales_merged وإخراج تقرير الحذف.

شغّل مرة واحدة بعد تعديل منطق الـ dedup:
  python scripts/run_dedup_report.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MERGED_PATH = PROJECT_ROOT / "data" / "real" / "real_sales_merged.csv"
REPORT_PATH = PROJECT_ROOT / "data" / "real" / "dedup_report.txt"

DEDUP_SUBSET = [
    "city_ar", "district_ar", "property_type_ar", "price_total", "area_sqm",
    "source", "year", "quarter",
]


def main() -> None:
    if not MERGED_PATH.exists():
        print(f"الملف غير موجود: {MERGED_PATH}")
        return
    df = pd.read_csv(MERGED_PATH, encoding="utf-8-sig")
    for c in DEDUP_SUBSET:
        if c not in df.columns:
            df[c] = pd.NA
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    df["quarter"] = pd.to_numeric(df["quarter"], errors="coerce").fillna(0).astype(int)

    before_count = len(df)
    removed = df[df.duplicated(subset=DEDUP_SUBSET, keep="first")]
    removed_count = len(removed)
    df = df.drop_duplicates(subset=DEDUP_SUBSET, keep="first")
    df = df.sort_values(["year", "quarter", "city_ar", "district_ar"], ignore_index=True)

    report_lines = [
        "تقرير إزالة التكرار (dedup) — مفتاح مع السنة والربع",
        f"مفتاح التكرار: {', '.join(DEDUP_SUBSET)}",
        f"قبل الحذف: {before_count} صف | بعد الحذف: {len(df)} صف | المحذوف: {removed_count} صف",
        "",
        "--- عدد الصفوف المحذوفة لكل مدينة ---",
    ]
    if removed_count > 0:
        for city, n in removed.groupby("city_ar", dropna=False).size().items():
            report_lines.append(f"  {city}: {n}")
        report_lines.append("")
        report_lines.append("--- عدد الصفوف المحذوفة لكل حي (مدينة - حي) ---")
        by_dist = removed.groupby(["city_ar", "district_ar"], dropna=False).size().sort_values(ascending=False)
        for (city, district), n in by_dist.items():
            report_lines.append(f"  {city} | {district}: {n}")
        report_lines.append("")
        report_lines.append("ملاحظة: إذا ظهر حي بعدد حذف كبير، راجع rounding السعر/المساحة أو مفاتيح الزمن (سنة/ربع).")
    else:
        report_lines.append("  لا يوجد صفوف محذوفة.")

    report_text = "\n".join(report_lines)
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    print(report_text)
    print(f"\nتم حفظ التقرير: {REPORT_PATH}")

    MERGED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(MERGED_PATH, index=False, encoding="utf-8-sig")
    print(f"تم تحديث الملف: {MERGED_PATH} ({len(df)} صف)")


if __name__ == "__main__":
    main()
