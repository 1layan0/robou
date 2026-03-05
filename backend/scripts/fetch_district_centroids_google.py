#!/usr/bin/env python3
"""
جلب إحداثيات (مركز) كل حي من Google Geocoding API.

يقرأ الأحياء من config/city_districts.json ويرسل طلب Geocoding لكل (مدينة، حي)
ويحفظ النتيجة في data/raw/district_centroids.json و .csv.
يحتاج GOOGLE_MAPS_API_KEY في .env.

الاستخدام: python scripts/fetch_district_centroids_google.py
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.parse import quote

import requests

# تحميل المفتاح من إعدادات المشروع
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.settings import settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "city_districts.json"
OUT_DIR = PROJECT_ROOT / "data" / "raw"
OUT_JSON = OUT_DIR / "district_centroids.json"
OUT_CSV = OUT_DIR / "district_centroids.csv"
OUT_OVERRIDES = OUT_DIR / "district_centroids_overrides.json"

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


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
    """تصحيح الاسم: شمالي→الشمالية، جنوبي→الجنوبية."""
    s = district.strip()
    if s.endswith("شمالي"):
        s = s[:-5] + "الشمالية"
    elif s.endswith("جنوبي"):
        s = s[:-5] + "الجنوبية"
    s = s.replace(" شمالي", " الشمالية").replace(" جنوبي", " الجنوبية")
    return s.strip()


def geocode_google(address: str, api_key: str) -> tuple[float, float] | None:
    """يرجع (lat, lon) أو None."""
    try:
        r = requests.get(
            GEOCODE_URL,
            params={"address": address, "key": api_key, "region": "sa"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "OK" or not data.get("results"):
            return None
        loc = data["results"][0]["geometry"]["location"]
        return (float(loc["lat"]), float(loc["lng"]))
    except Exception:
        return None


def main() -> None:
    api_key = (settings.google_maps_api_key or "").strip()
    if not api_key:
        print("أضيفي GOOGLE_MAPS_API_KEY في .env")
        return

    parser = argparse.ArgumentParser(description="جلب إحداثيات مراكز الأحياء من Google Geocoding")
    parser.add_argument("--missing-only", action="store_true", help="إعادة طلب الأحياء الناقصة فقط")
    parser.add_argument("--apply-overrides-only", action="store_true", help="تطبيق التكميلات فقط (بدون شبكة)")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pairs = load_city_districts()

    if args.apply_overrides_only:
        if not OUT_JSON.exists():
            print("لا يوجد district_centroids.json. شغّلي السكربت أولاً.")
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
            json.dump({"source": data.get("source", "Google"), "centroids": results}, f, ensure_ascii=False, indent=2)
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
            print("لا توجد أحياء ناقصة.")
            return
        pairs = missing
        print(f"إعادة طلب {len(pairs)} حي ناقص...")
    else:
        print(f"عدد الأحياء: {len(pairs)}. جاري الطلب من Google Geocoding...")

    results = []
    for i, (city, district) in enumerate(pairs, 1):
        district_query = normalise_district_for_query(district)
        address = f"{district_query}, {city}, Saudi Arabia"
        lat_lon = geocode_google(address, api_key)
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
            results.append({"city": city, "district": district, "latitude": None, "longitude": None})
            print(f"  [{i}/{len(pairs)}] {city} / {district} → لم يُعثر")
        time.sleep(0.2)

    if args.missing_only and OUT_JSON.exists():
        with open(OUT_JSON, encoding="utf-8") as f:
            existing = json.load(f)
        by_key = {(r["city"], r["district"]): r for r in existing["centroids"]}
        for r in results:
            by_key[(r["city"], r["district"])] = r
        results = list(by_key.values())
        all_pairs = load_city_districts()
        order = {(c, d): i for i, (c, d) in enumerate(all_pairs)}
        results.sort(key=lambda r: order.get((r["city"], r["district"]), 9999))

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
            print(f"  تطبيق {filled} إحداثيات من التكميلات.")

    for r in results:
        r["district"] = normalise_district_for_query(r["district"])

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"source": "Google", "centroids": results}, f, ensure_ascii=False, indent=2)
    import pandas as pd
    pd.DataFrame(results).to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    ok = sum(1 for r in results if r["latitude"] is not None)
    print(f"\nحفظ: {OUT_JSON} ، {OUT_CSV}. إحداثيات: {ok}/{len(results)} حي.")


if __name__ == "__main__":
    main()
