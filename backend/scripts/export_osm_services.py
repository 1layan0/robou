#!/usr/bin/env python3
"""
تصدير الخدمات من ملف GeoJSON المنظف إلى CSV جاهز للاستخدام.

يبقى فقط العناصر ذات: amenity, shop, leisure, tourism, healthcare, office
ويُخرج: osm_id, type, name, operator, latitude, longitude
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SERVICE_KEYS = ("amenity", "shop", "leisure", "tourism", "healthcare", "office", "public_transport", "sport", "religion")


def get_centroid(geom: dict) -> tuple[float, float] | None:
    """استخراج centroid (lon, lat)."""
    typ = geom.get("type")
    coords_raw = geom.get("coordinates", [])

    def collect(c):
        out = []
        if isinstance(c[0], (int, float)):
            return [tuple(c[:2])]
        for x in c:
            out.extend(collect(x))
        return out

    coords = collect(coords_raw)
    if not coords:
        return None
    n = len(coords)
    lon = sum(c[0] for c in coords) / n
    lat = sum(c[1] for c in coords) / n
    return (lon, lat)


def main() -> None:
    parser = argparse.ArgumentParser(description="تصدير الخدمات من GeoJSON إلى CSV")
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=None,
        help="مسار GeoJSON (افتراضي: data/raw/osm_dammam_dhahran_khobar.geojson)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="مسار CSV الناتج",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    in_path = Path(args.input) if args.input else project_root / "data" / "raw" / "osm_dammam_dhahran_khobar.geojson"
    out_path = Path(args.output) if args.output else project_root / "data" / "raw" / "osm_services.csv"

    if not in_path.exists():
        print(f"خطأ: الملف غير موجود: {in_path}")
        return

    print(f"جاري تحميل: {in_path}")
    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        has_service = any(k in props for k in SERVICE_KEYS)
        if not has_service:
            continue

        geom = feat.get("geometry")
        if not geom:
            continue
        cent = get_centroid(geom)
        if not cent:
            continue
        lon, lat = cent

        # نوع الخدمة: أول مفتاح موجود
        svc_type = ""
        for k in SERVICE_KEYS:
            v = props.get(k)
            if v:
                svc_type = f"{k}={v}"
                break
        if not svc_type:
            continue

        name = props.get("name") or props.get("name:ar") or props.get("name:en") or svc_type
        operator = props.get("operator") or props.get("operator:ar") or ""
        osm_id = props.get("@id") or feat.get("id") or ""

        rows.append({
            "osm_id": str(osm_id),
            "type": svc_type[:100],
            "name": str(name)[:100],
            "operator": str(operator)[:100],
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
        })

    # تصدير CSV
    import csv
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["osm_id", "type", "name", "operator", "latitude", "longitude"])
        w.writeheader()
        w.writerows(rows)

    print(f"تم تصدير {len(rows)} خدمة إلى: {out_path}")


if __name__ == "__main__":
    main()
