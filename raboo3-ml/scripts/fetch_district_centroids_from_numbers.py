#!/usr/bin/env python3
"""
جلب قائمة الأحياء المعتمدة من ملف Numbers ثم إحداثيات مركز كل حي من Google Geocoding.

يستبدل القائمة اليدوية القديمة:
  - يقرأ (المدينة، الحي) من ملف الاحياء_final.numbers
  - يحدّث config/city_districts.json بهذه القائمة
  - يجلب الإحداثيات من Google ويحفظ في data/raw/district_centroids.json و .csv

يحتاج: GOOGLE_MAPS_API_KEY في .env، وحزمة numbers-parser لقراءة الملف.

الاستخدام:
  python scripts/fetch_district_centroids_from_numbers.py "/Users/sarah/Desktop/الاحياء_final.numbers"
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings

CONFIG_PATH = PROJECT_ROOT / "config" / "city_districts.json"
OUT_DIR = PROJECT_ROOT / "data" / "raw"
OUT_JSON = OUT_DIR / "district_centroids.json"
OUT_CSV = OUT_DIR / "district_centroids.csv"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def load_pairs_from_numbers(path: Path) -> list[tuple[str, str]]:
    """استخراج (مدينة، حي) من ملف Numbers. العمودان الأولان: المدينة، الحي."""
    try:
        from numbers_parser import Document
    except ImportError:
        raise ImportError("ثبّتي الحزمة: pip install numbers-parser")
    doc = Document(path)
    table = doc.sheets[0].tables[0]
    pairs = []
    for r in range(1, table.num_rows):
        city = table.cell(r, 0).value
        district = table.cell(r, 1).value
        if city and district:
            pairs.append((str(city).strip(), str(district).strip()))
    return pairs


def pairs_to_city_districts(pairs: list[tuple[str, str]]) -> dict[str, list[str]]:
    """تحويل قائمة (مدينة، حي) إلى {مدينة: [حي، حي، ...]}."""
    by_city: dict[str, list[str]] = {}
    for city, district in pairs:
        if city not in by_city:
            by_city[city] = []
        if district and district not in by_city[city]:
            by_city[city].append(district)
    return by_city


def normalise_district_for_query(district: str) -> str:
    s = (district or "").strip()
    if s.endswith("شمالي"):
        s = s[:-5] + "الشمالية"
    elif s.endswith("جنوبي"):
        s = s[:-5] + "الجنوبية"
    s = s.replace(" شمالي", " الشمالية").replace(" جنوبي", " الجنوبية")
    return s.strip()


def geocode_google(address: str, api_key: str) -> tuple[float, float] | None:
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
    if len(sys.argv) < 2:
        print("الاستخدام: python scripts/fetch_district_centroids_from_numbers.py <مسار ملف الاحياء_final.numbers>")
        sys.exit(1)
    numbers_path = Path(sys.argv[1])
    if not numbers_path.exists():
        print(f"الملف غير موجود: {numbers_path}")
        sys.exit(1)

    api_key = (settings.google_maps_api_key or "").strip()
    if not api_key:
        print("أضيفي GOOGLE_MAPS_API_KEY في .env")
        sys.exit(1)

    print(f"قراءة القائمة من {numbers_path.name}...")
    pairs = load_pairs_from_numbers(numbers_path)
    print(f"عدد الأحياء: {len(pairs)}")

    # استبدال القائمة القديمة في config
    city_districts = pairs_to_city_districts(pairs)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(city_districts, f, ensure_ascii=False, indent=2)
    print(f"تم تحديث {CONFIG_PATH}")

    # جلب الإحداثيات من Google
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for i, (city, district) in enumerate(pairs, 1):
        district_query = normalise_district_for_query(district)
        address = f"{district_query}, {city}, Saudi Arabia"
        lat_lon = geocode_google(address, api_key)
        if lat_lon:
            lat, lon = lat_lon
            results.append({
                "city": city,
                "district": normalise_district_for_query(district),
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
        time.sleep(0.2)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"source": "Google", "source_list": "الاحياء_final.numbers", "centroids": results}, f, ensure_ascii=False, indent=2)
    import pandas as pd
    pd.DataFrame(results).to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    ok = sum(1 for r in results if r.get("latitude") is not None)
    print(f"\nحفظ: {OUT_JSON} ، {OUT_CSV}. إحداثيات: {ok}/{len(results)} حي.")


if __name__ == "__main__":
    main()
