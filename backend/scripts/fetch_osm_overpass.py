#!/usr/bin/env python3
"""
جلب بيانات حقيقية من OpenStreetMap عبر Overpass API (بدون osmnx).
يُخرج: مرافق (amenity, shop, leisure, tourism) من نود وواي في منطقة الشرقية (الدمام/الظهران/الخبر)،
بصيغة osm_services.csv ثم دمج مع الموجود إن وُجد.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "data" / "raw"
# bbox أوسع للشرقية: الدمام، الظهران، الخبر (south, west, north, east)
BBOX = (26.15, 49.98, 26.52, 50.28)
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
OSM_SERVICES_CSV = OUT_DIR / "osm_services.csv"


def run_overpass_query(query: str, timeout: int = 90) -> dict:
    for url in OVERPASS_URLS:
        try:
            r = requests.post(url, data={"data": query}, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            continue
    raise RuntimeError("فشل كل خوادم Overpass")


def _tags_to_type(tags: dict) -> str | None:
    for key in ("amenity", "shop", "leisure", "tourism"):
        if key in tags and tags[key]:
            return f"{key}={tags[key]}"
    return None


def _elements_to_rows(elements: list) -> list[dict]:
    rows = []
    for el in elements:
        typ = el.get("type")
        tags = el.get("tags") or {}
        svc_type = _tags_to_type(tags)
        if not svc_type:
            continue
        if typ == "node":
            lat, lon = el.get("lat"), el.get("lon")
        else:
            center = el.get("center") or {}
            lat, lon = center.get("lat"), center.get("lon")
        if lat is None or lon is None:
            continue
        osm_id = f"{typ}/{el.get('id')}"
        name = (tags.get("name") or tags.get("name:ar") or tags.get("name:en") or "")[:100]
        operator = (tags.get("operator") or tags.get("operator:ar") or "")[:100]
        rows.append({
            "osm_id": osm_id,
            "type": svc_type[:100],
            "name": name,
            "operator": operator,
            "latitude": round(float(lat), 6),
            "longitude": round(float(lon), 6),
        })
    return rows


def fetch_pois() -> list[dict]:
    south, west, north, east = BBOX
    all_rows = []
    # استعلام 1: نود amenity + shop
    q1 = f"""[out:json][timeout:75];(node["amenity"]({south},{west},{north},{east});node["shop"]({south},{west},{north},{east}););out body;"""
    try:
        data = run_overpass_query(q1)
        all_rows.extend(_elements_to_rows(data.get("elements", [])))
        print(f"  نود (amenity+shop): {len(data.get('elements', []))} عنصر")
    except Exception as e:
        print(f"  تحذير (نود amenity+shop): {e}")
    time.sleep(2)
    # استعلام 2: نود leisure + tourism
    q2 = f"""[out:json][timeout:75];(node["leisure"]({south},{west},{north},{east});node["tourism"]({south},{west},{north},{east}););out body;"""
    try:
        data = run_overpass_query(q2)
        all_rows.extend(_elements_to_rows(data.get("elements", [])))
        print(f"  نود (leisure+tourism): {len(data.get('elements', []))} عنصر")
    except Exception as e:
        print(f"  تحذير (نود leisure+tourism): {e}")
    time.sleep(2)
    # استعلام 3: واي
    query_ways = f"""
    [out:json][timeout:90];
    (
      way["amenity"]({south},{west},{north},{east});
      way["shop"]({south},{west},{north},{east});
      way["leisure"]({south},{west},{north},{east});
      way["tourism"]({south},{west},{north},{east});
    );
    out body center;
    """
    try:
        data = run_overpass_query(query_ways)
        all_rows.extend(_elements_to_rows(data.get("elements", [])))
        print(f"  واي: {len(data.get('elements', []))} عنصر")
    except Exception as e:
        print(f"  تحذير (واي): {e}")
    return all_rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("جاري جلب المرافق من OpenStreetMap (Overpass API)...")
    try:
        pois = fetch_pois()
    except Exception as e:
        print(f"خطأ: {e}")
        raise
    if not pois:
        print("لم يُرجع الاستعلام أي نقاط. تحقق من الـ bbox أو الشبكة.")
        return

    out_json = OUT_DIR / "osm_pois_eastern.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"source": "Overpass API", "bbox": BBOX, "count": len(pois), "pois": pois}, f, ensure_ascii=False, indent=2)

    import pandas as pd
    new_df = pd.DataFrame(pois)
    new_df = new_df[["osm_id", "type", "name", "operator", "latitude", "longitude"]]

    if OSM_SERVICES_CSV.exists():
        existing = pd.read_csv(OSM_SERVICES_CSV, encoding="utf-8-sig")
        for c in ["osm_id", "type", "name", "operator", "latitude", "longitude"]:
            if c not in existing.columns:
                existing[c] = pd.NA
        existing = existing[["osm_id", "type", "name", "operator", "latitude", "longitude"]]
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["osm_id"], keep="first")
        combined.to_csv(OSM_SERVICES_CSV, index=False, encoding="utf-8-sig")
        print(f"تم جلب {len(pois)} نقطة جديدة. دُمجت مع الموجود → {len(combined)} نقطة في {OSM_SERVICES_CSV.name}")
    else:
        new_df.to_csv(OSM_SERVICES_CSV, index=False, encoding="utf-8-sig")
        print(f"تم جلب {len(pois)} نقطة. حفظ: {OSM_SERVICES_CSV.name}")

    print(f"JSON: {out_json.name}")
    time.sleep(1)


if __name__ == "__main__":
    main()
