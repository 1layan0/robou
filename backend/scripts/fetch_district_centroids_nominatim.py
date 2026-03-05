#!/usr/bin/env python3
"""
جلب إحداثيات (مركز) كل حي من Nominatim (OpenStreetMap) تلقائياً.

يقرأ الأحياء من config/city_districts.json ويرسل طلب Geocoding لكل (مدينة، حي)
ويحفظ النتيجة في data/raw/district_centroids.json و .csv للاستخدام في الخريطة (Pin + دائرة).

الاستخدام: python scripts/fetch_district_centroids_nominatim.py
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "city_districts.json"
OUT_DIR = PROJECT_ROOT / "data" / "raw"
OUT_JSON = OUT_DIR / "district_centroids.json"
OUT_CSV = OUT_DIR / "district_centroids.csv"
OUT_OVERRIDES = OUT_DIR / "district_centroids_overrides.json"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Nominatim يطلب User-Agent يحدد التطبيق
HEADERS = {"User-Agent": "Raboo3-ML/1.0 (district centroids for map)"}


def load_city_districts() -> list[tuple[str, str]]:
    """(مدينة، حي) من config."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = json.load(f)
    pairs = []
    for city, districts in data.items():
        for district in districts:
            district = (district or "").strip()
            if district:
                pairs.append((city.strip(), district))
    return pairs


def normalise_district_for_query(district: str) -> str:
    """تصحيح الاسم للاستعلام: شمالي→الشمالية، جنوبي→الجنوبية ليتعرف Nominatim."""
    s = district.strip()
    if s.endswith("شمالي"):
        s = s[:-5] + "الشمالية"
    elif s.endswith("جنوبي"):
        s = s[:-5] + "الجنوبية"
    s = s.replace(" شمالي", " الشمالية").replace(" جنوبي", " الجنوبية")
    return s.strip()


def geocode_nominatim(query: str) -> tuple[float, float] | None:
    """يرجع (lat, lon) أو None إذا لم يُعثر."""
    try:
        r = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers=HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            return None
        first = data[0]
        lat = float(first.get("lat"))
        lon = float(first.get("lon"))
        return (lat, lon)
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="جلب إحداثيات مراكز الأحياء من Nominatim")
    parser.add_argument("--missing-only", action="store_true", help="إعادة طلب الأحياء التي لم تُرجع إحداثيات فقط (يحتاج district_centroids.json موجود)")
    parser.add_argument("--apply-overrides-only", action="store_true", help="تطبيق ملف التكميلات على district_centroids.json الحالي وحفظه (بدون طلبات شبكة)")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pairs = load_city_districts()

    if args.apply_overrides_only:
        if not OUT_JSON.exists():
            print("لا يوجد ملف district_centroids.json. شغّلي السكربت بدون --apply-overrides-only أولاً.")
            return
        with open(OUT_JSON, encoding="utf-8") as f:
            data = json.load(f)
        results = data["centroids"]
        if OUT_OVERRIDES.exists():
            with open(OUT_OVERRIDES, encoding="utf-8") as f:
                overrides_data = json.load(f)
            override_list = overrides_data.get("overrides", [])
            override_by = {(o["city"], o["district"]): (round(float(o["latitude"]), 6), round(float(o["longitude"]), 6)) for o in override_list}
            filled = 0
            for r in results:
                key_norm = (r["city"], normalise_district_for_query(r["district"]))
                if key_norm in override_by and r.get("latitude") is None:
                    lat, lon = override_by[key_norm]
                    r["latitude"], r["longitude"] = lat, lon
                    filled += 1
            print(f"تم تطبيق {filled} إحداثيات من التكميلات.")
        for r in results:
            r["district"] = normalise_district_for_query(r["district"])
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump({"source": data.get("source", "Nominatim"), "centroids": results}, f, ensure_ascii=False, indent=2)
        import pandas as pd
        pd.DataFrame(results).to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
        ok = sum(1 for r in results if r["latitude"] is not None)
        print(f"حفظ: {OUT_JSON} ، {OUT_CSV}. إحداثيات: {ok}/{len(results)} حي.")
        return

    if args.missing_only and OUT_JSON.exists():
        with open(OUT_JSON, encoding="utf-8") as f:
            existing = json.load(f)
        by_key = {(r["city"], r["district"]): r for r in existing["centroids"]}
        missing = [(c, d) for c, d in pairs if by_key.get((c, d), {}).get("latitude") is None]
        if not missing:
            print("لا توجد أحياء ناقصة. انتهى.")
            return
        pairs = missing
        print(f"إعادة طلب {len(pairs)} حي ناقص (باسم مصحح: شمالي→الشمالية، جنوبي→الجنوبية)...")
    else:
        print(f"عدد الأحياء: {len(pairs)}. جاري الطلب من Nominatim (طلب واحد كل ثانية)...")

    results = []
    for i, (city, district) in enumerate(pairs, 1):
        # استعلام بالاسم المصحح (شمالي→الشمالية) لتحسين النتائج
        district_query = normalise_district_for_query(district)
        query = f"{district_query}، {city}، السعودية"
        lat_lon = geocode_nominatim(query)
        if lat_lon:
            lat, lon = lat_lon
            results.append({
                "city": city,
                "district": district,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
            })
            print(f"  [{i}/{len(pairs)}] {city} / {district} → {lat:.4f}, {lon:.4f}")
        else:
            results.append({
                "city": city,
                "district": district,
                "latitude": None,
                "longitude": None,
            })
            print(f"  [{i}/{len(pairs)}] {city} / {district} → لم يُعثر")
        time.sleep(1)

    if args.missing_only and OUT_JSON.exists():
        with open(OUT_JSON, encoding="utf-8") as f:
            existing = json.load(f)
        by_key = {(r["city"], r["district"]): r for r in existing["centroids"]}
        for r in results:
            by_key[(r["city"], r["district"])] = r
        results = list(by_key.values())
        # ترتيب كالملف الأصلي (مدينة ثم حي)
        all_pairs = load_city_districts()
        order = {(c, d): i for i, (c, d) in enumerate(all_pairs)}
        results.sort(key=lambda r: order.get((r["city"], r["district"]), 9999))

    # تطبيق الإحداثيات اليدوية من ملف التكميلات (مثلاً أحياء الظهران)
    if OUT_OVERRIDES.exists():
        with open(OUT_OVERRIDES, encoding="utf-8") as f:
            overrides_data = json.load(f)
        override_list = overrides_data.get("overrides", [])
        override_by = {(o["city"], o["district"]): (round(float(o["latitude"]), 6), round(float(o["longitude"]), 6)) for o in override_list}
        filled = 0
        for r in results:
            key_norm = (r["city"], normalise_district_for_query(r["district"]))
            if key_norm in override_by and r.get("latitude") is None:
                lat, lon = override_by[key_norm]
                r["latitude"], r["longitude"] = lat, lon
                filled += 1
        if filled:
            print(f"  تطبيق {filled} إحداثيات من التكميلات ({OUT_OVERRIDES.name})")

    # توحيد أسماء الأحياء في المخرجات: شمالي→الشمالية، جنوبي→الجنوبية
    for r in results:
        r["district"] = normalise_district_for_query(r["district"])

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"source": "Nominatim", "centroids": results}, f, ensure_ascii=False, indent=2)
    print(f"\nحفظ JSON: {OUT_JSON}")

    import pandas as pd
    df = pd.DataFrame(results)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"حفظ CSV: {OUT_CSV}")

    ok = sum(1 for r in results if r["latitude"] is not None)
    print(f"تم الحصول على إحداثيات لـ {ok}/{len(results)} حي.")


if __name__ == "__main__":
    main()
