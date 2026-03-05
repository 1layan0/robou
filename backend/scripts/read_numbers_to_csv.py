#!/usr/bin/env python3
"""
قراءة ملفات .numbers (منصة أرض) واستخراج الجداول إلى CSV بصيغة المشروع.
يتطلب: pip3 install numbers-parser ثم تشغيل بـ python3.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# استخدام python3 (مثلاً /usr/bin/python3) لأن numbers-parser قد يكون مثبتاً عليه
try:
    from numbers_parser import Document
except ImportError:
    print("شغّل: pip3 install numbers-parser")
    sys.exit(1)

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = PROJECT_ROOT / "data" / "raw" / "ard_platform_export.csv"

# مسارات المجلدات (صفقات + سجل عقاري)
ARD_DIRS = [
    Path("/Users/sarah/Desktop/بيانات ارض/صفقات عقارية"),
    Path("/Users/sarah/Desktop/بيانات ارض/السجل العقاري"),
]


def extract_number(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    s = str(s).strip()
    s = re.sub(r"[^\d.]", "", s)
    try:
        return float(s) if s else None
    except ValueError:
        return None


def parse_city_district(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "", ""
    s = str(val).strip()
    if "/" in s:
        parts = s.split("/", 1)
        return parts[0].strip(), parts[1].strip()
    return s, ""


def normalize_property_type(use, ptype):
    use = (use or "").strip()
    ptype = (ptype or "").strip()
    if "سكن" in use or "سكني" in use:
        return "قطعة أرض-سكنى"
    if "تجار" in use or "تجاري" in use:
        return "قطعة أرض-تجارى"
    if "زراع" in use:
        return "قطعة أرض-زراعي"
    if "قطعة أرض" in ptype:
        return "قطعة أرض-سكنى"  # افتراضي
    if "شقة" in ptype:
        return "شقة"
    if "فيلا" in ptype or "فيلا" in ptype:
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


def to_standard_row(raw: dict, year: int = 2024, quarter: int = 1) -> dict | None:
    """تحويل صف خام إلى صيغة المشروع."""
    # أسماء أعمدة محتملة
    city_dist = raw.get("المدينة / الحي") or raw.get("المدينة") or raw.get("مدينة/حي") or ""
    city, district = parse_city_district(city_dist)
    if not city:
        return None
    area_raw = raw.get("المساحة") or raw.get("المساحة (م2)") or raw.get("المساحة M2)") or ""
    area = extract_number(str(area_raw))
    price_sqm_raw = raw.get("سعر المتر") or raw.get("متوسط سعر المتر") or raw.get("سعر المتر") or ""
    price_sqm = extract_number(str(price_sqm_raw))
    price_total_raw = raw.get("سعر الصفقة") or raw.get("السعر") or raw.get("مجموع سعر العقار") or ""
    price_total = extract_number(str(price_total_raw))
    if price_sqm is None and price_total and area:
        price_sqm = price_total / area
    if price_total is None and price_sqm and area:
        price_total = price_sqm * area
    if not price_sqm or price_sqm <= 0 or not area or area <= 0:
        return None
    use = raw.get("الإستخدام") or raw.get("الاستخدام") or ""
    ptype = raw.get("نوع العقار") or raw.get("تصنيف العقار") or ""
    prop = normalize_property_type(use, ptype)
    date_val = raw.get("التاريخ")
    if date_val:
        try:
            from datetime import datetime
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


def main():
    ALLOWED = {"الدمام", "الظهران", "الخبر"}
    all_rows = []
    for d in ARD_DIRS:
        if not d.exists():
            print(f"تخطي (غير موجود): {d}")
            continue
        for path in sorted(d.glob("*.numbers")):
            print(f"قراءة: {path.name}")
            try:
                raw_rows = load_sheet_from_numbers(path)
                for raw in raw_rows:
                    row = to_standard_row(raw)
                    if row and row["city_ar"] in ALLOWED:
                        all_rows.append(row)
                print(f"  → {len(raw_rows)} صف خام")
            except Exception as e:
                print(f"  خطأ: {e}")

    if not all_rows:
        print("لا توجد صفوف صالحة.")
        return 1

    df = pd.DataFrame(all_rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    # تطبيق المفتاح الجديد على بيانات منصة أرض قبل الحفظ والدمج
    DEDUP_SUBSET = [
        "city_ar", "district_ar", "property_type_ar", "price_total", "area_sqm",
        "source", "year", "quarter",
    ]
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    df["quarter"] = pd.to_numeric(df["quarter"], errors="coerce").fillna(0).astype(int)
    before_dedup = len(df)
    removed_df = df[df.duplicated(subset=DEDUP_SUBSET, keep="first")]
    df = df.drop_duplicates(subset=DEDUP_SUBSET, keep="first")
    if len(removed_df) > 0:
        print(f"من بيانات منصة أرض: حُذف {len(removed_df)} صف مكرر (مفتاح: سنة+ربع)")

    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\nتم الحفظ: {len(df)} صف → {OUT_CSV}")

    # دمج مع real_sales_merged (مفتاح تكرار يشمل السنة والربع)
    merged_path = PROJECT_ROOT / "data" / "real" / "real_sales_merged.csv"
    report_path = PROJECT_ROOT / "data" / "real" / "dedup_report.txt"
    target_cols = list(df.columns)
    if merged_path.exists():
        existing = pd.read_csv(merged_path, encoding="utf-8-sig")
        for c in target_cols:
            if c not in existing.columns:
                existing[c] = pd.NA
        combined = pd.concat([existing, df], ignore_index=True)
        for c in DEDUP_SUBSET:
            if c not in combined.columns:
                combined[c] = pd.NA
        combined["year"] = pd.to_numeric(combined["year"], errors="coerce").fillna(0).astype(int)
        combined["quarter"] = pd.to_numeric(combined["quarter"], errors="coerce").fillna(0).astype(int)
        before_count = len(combined)
        removed = combined[combined.duplicated(subset=DEDUP_SUBSET, keep="first")]
        combined = combined.drop_duplicates(subset=DEDUP_SUBSET, keep="first")
        removed_count = len(removed)
        report_lines = [
            "تقرير إزالة التكرار (dedup)",
            f"مفتاح التكرار: {', '.join(DEDUP_SUBSET)}",
            f"قبل الحذف: {before_count} صف | بعد الحذف: {len(combined)} صف | المحذوف: {removed_count} صف",
            "",
            "--- عدد الصفوف المحذوفة لكل مدينة ---",
        ]
        if removed_count > 0:
            for city, n in removed.groupby("city_ar", dropna=False).size().items():
                report_lines.append(f"  {city}: {n}")
            report_lines.append("")
            report_lines.append("--- عدد الصفوف المحذوفة لكل حي (مدينة - حي) ---")
            for (city, district), n in removed.groupby(["city_ar", "district_ar"], dropna=False).size().sort_values(ascending=False).items():
                report_lines.append(f"  {city} | {district}: {n}")
            report_lines.append("")
            report_lines.append("ملاحظة: إذا ظهر حي بعدد حذف كبير، راجع rounding السعر/المساحة أو مفاتيح الزمن (سنة/ربع).")
        else:
            report_lines.append("  لا يوجد صفوف محذوفة.")
        report_path.write_text("\n".join(report_lines), encoding="utf-8")
        print(report_lines[2])
        print(f"تم حفظ التقرير: {report_path}")
        combined = combined.sort_values(["year", "quarter", "city_ar", "district_ar"], ignore_index=True)
        combined.to_csv(merged_path, index=False, encoding="utf-8-sig")
        print(f"تم الدمج مع real_sales_merged: {len(combined)} صف إجمالاً → {merged_path}")
    else:
        df.to_csv(merged_path, index=False, encoding="utf-8-sig")
        print(f"تم إنشاء: {merged_path} ({len(df)} صف)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
