#!/usr/bin/env python3
"""استخراج جداول من .numbers إلى CSV بدون pandas. شغّل: python3 scripts/read_numbers_minimal.py"""
import csv
import re
import sys
from pathlib import Path

try:
    from numbers_parser import Document
except ImportError:
    print("شغّل: pip3 install numbers-parser")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = PROJECT_ROOT / "data" / "raw" / "ard_platform_export.csv"
ARD_DIRS = [
    Path("/Users/sarah/Desktop/بيانات ارض/صفقات عقارية"),
    Path("/Users/sarah/Desktop/بيانات ارض/السجل العقاري"),
]


def extract_number(s):
    if s is None: return None
    s = str(s).strip()
    s = re.sub(r"[^\d.]", "", s).rstrip(".")
    try:
        return float(s) if s else None
    except ValueError:
        return None


def parse_city_district(val):
    if val is None: return "", ""
    s = str(val).strip()
    if "/" in s:
        a, b = s.split("/", 1)
        return a.strip(), b.strip()
    return s, ""


def load_all():
    rows = []
    for d in ARD_DIRS:
        if not d.exists():
            continue
        for path in sorted(d.glob("*.numbers")):
            try:
                doc = Document(str(path))
                for sheet in doc.sheets:
                    for table in sheet.tables:
                        rlist = list(table.iter_rows())
                        if not rlist:
                            continue
                        headers = [str(c.value).strip() if c.value is not None else "" for c in rlist[0]]
                        for r in rlist[1:]:
                            cells = [c.value for c in r]
                            row_dict = dict(zip(headers, cells))
                            rows.append((path.name, headers, row_dict))
            except Exception as e:
                print(path.name, e)
    return rows


def main():
    all_raw = load_all()
    if not all_raw:
        print("لا توجد بيانات.")
        return 1

    out_cols = ["year", "quarter", "region_ar", "city_ar", "district_ar", "property_type_ar",
                "deed_count", "price_total", "area_sqm", "price_per_sqm", "source", "tx_reference"]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=out_cols, extrasaction="ignore")
        w.writeheader()
        count = 0
        for _fname, headers, raw in all_raw:
            city_dist = raw.get("المدينة / الحي") or raw.get("المدينة") or ""
            city, district = parse_city_district(city_dist)
            if not city or city not in ("الدمام", "الظهران", "الخبر"):
                continue
            area = extract_number(raw.get("المساحة"))
            price_sqm = extract_number(raw.get("سعر المتر") or raw.get("متوسط سعر المتر"))
            price_t = extract_number(raw.get("سعر الصفقة") or raw.get("السعر") or raw.get("مجموع سعر العقار"))
            if price_sqm is None and price_t and area:
                price_sqm = price_t / area
            if price_t is None and price_sqm and area:
                price_t = price_sqm * area
            if not price_sqm or price_sqm <= 0 or not area or area <= 0:
                continue
            use = (raw.get("الإستخدام") or raw.get("الاستخدام") or "").strip()
            ptype = (raw.get("نوع العقار") or "").strip()
            if "تجار" in use: prop = "قطعة أرض-تجارى"
            elif "سكن" in use: prop = "قطعة أرض-سكنى"
            elif "زراع" in use: prop = "قطعة أرض-زراعي"
            elif "شقة" in ptype: prop = "شقة"
            elif "فيلا" in ptype: prop = "فيلا"
            else: prop = "قطعة أرض-سكنى"
            w.writerow({
                "year": 2024, "quarter": 1, "region_ar": "الشرقية",
                "city_ar": city, "district_ar": district or "_غير_محدد",
                "property_type_ar": prop, "deed_count": 1,
                "price_total": round(price_t, 2), "area_sqm": round(area, 2),
                "price_per_sqm": round(price_sqm, 2), "source": "منصة ارض",
                "tx_reference": str(raw.get("رقم الصفقة") or raw.get("الرقم المرجعي") or ""),
            })
            count += 1
    print(f"تم: {count} صف → {OUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
