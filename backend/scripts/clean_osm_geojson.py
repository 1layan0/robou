#!/usr/bin/env python3
"""
تنظيف وتصفية ملف GeoJSON من Overpass Turbo.
يبقى فقط بيانات الظهران والدمام والخبر، ويُزيل الأشكال التالفة.

الاستخدام:
    python scripts/clean_osm_geojson.py --input "/Users/sarah/Downloads/export (3).geojson"
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


# bbox الظهران، الدمام، الخبر (south, west, north, east)
BBOX = (26.10, 50.00, 26.55, 50.35)  # lat_min, lon_min, lat_max, lon_max


def get_coords(geom: dict) -> list[tuple[float, float]]:
    """استخراج كل الإحداثيات من geometry."""
    coords = []
    typ = geom.get("type")
    coords_raw = geom.get("coordinates", [])

    if typ == "Point":
        return [tuple(coords_raw)] if len(coords_raw) >= 2 else []
    if typ == "LineString":
        return [tuple(c) for c in coords_raw if len(c) >= 2]
    if typ == "Polygon":
        for ring in coords_raw:
            if ring:
                coords.extend([tuple(c) for c in ring if len(c) >= 2])
        return coords
    if typ in ("MultiPoint", "MultiLineString"):
        for c in coords_raw:
            if len(c) >= 2:
                coords.append(tuple(c[:2]))
        return coords
    if typ == "MultiPolygon":
        for poly in coords_raw:
            for ring in poly:
                if ring:
                    coords.extend([tuple(c) for c in ring if len(c) >= 2])
        return coords
    return []


def in_bbox(lon: float, lat: float) -> bool:
    lon_min, lon_max = BBOX[1], BBOX[3]
    lat_min, lat_max = BBOX[0], BBOX[2]
    return lon_min <= lon <= lon_max and lat_min <= lat <= lat_max


def is_collapsed(coords: list[tuple[float, float]], tol: float = 1e-8) -> bool:
    """هل كل النقاط متطابقة (شكل تالف)؟"""
    if len(coords) < 2:
        return False
    x0, y0 = coords[0]
    for x, y in coords[1:]:
        if abs(x - x0) > tol or abs(y - y0) > tol:
            return False
    return True


def centroid(coords: list[tuple[float, float]]) -> tuple[float, float] | None:
    """مركز تقريبي للإحداثيات (lon, lat)."""
    if not coords:
        return None
    n = len(coords)
    lon = sum(c[0] for c in coords) / n
    lat = sum(c[1] for c in coords) / n
    return (lon, lat)


def clean_geometry(geom: dict) -> dict | None:
    """إصلاح/إزالة الأشكال التالفة. يرجع None إذا كان الشكل غير صالح."""
    coords = get_coords(geom)
    if not coords:
        return None
    if is_collapsed(coords):
        return None
    return geom


def main() -> None:
    parser = argparse.ArgumentParser(description="تنظيف وتصفية GeoJSON للدمام/الظهران/الخبر")
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="/Users/sarah/Downloads/export (3).geojson",
        help="مسار ملف GeoJSON المدخل",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="مسار الملف الناتج (افتراضي: data/raw/osm_dammam_dhahran_khobar.geojson)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    out_path = Path(args.output) if args.output else project_root / "data" / "raw" / "osm_dammam_dhahran_khobar.geojson"
    in_path = Path(args.input)

    if not in_path.exists():
        print(f"خطأ: الملف غير موجود: {in_path}")
        return

    print(f"جاري تحميل: {in_path}")
    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    print(f"إجمالي العناصر: {len(features)}")

    kept = []
    skipped_bbox = 0
    skipped_collapsed = 0
    skipped_no_geom = 0

    for feat in features:
        geom = feat.get("geometry")
        if not geom:
            skipped_no_geom += 1
            continue

        coords = get_coords(geom)
        if not coords:
            skipped_no_geom += 1
            continue
        if is_collapsed(coords):
            skipped_collapsed += 1
            continue

        lon, lat = centroid(coords)
        if not in_bbox(lon, lat):
            skipped_bbox += 1
            continue

        # نسخ العنصر مع التأكد من geometry صالح
        clean_geom = clean_geometry(geom)
        if clean_geom is None:
            skipped_collapsed += 1
            continue

        kept.append({
            "type": "Feature",
            "properties": feat.get("properties", {}),
            "geometry": clean_geom,
            "id": feat.get("id"),
        })

    # GeoJSON bbox: [min_lon, min_lat, max_lon, max_lat]
    geo_bbox = [BBOX[1], BBOX[0], BBOX[3], BBOX[2]]
    out_collection = {
        "type": "FeatureCollection",
        "generator": "clean_osm_geojson",
        "copyright": data.get("copyright", "© OpenStreetMap contributors, ODbL"),
        "bbox": geo_bbox,
        "features": kept,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_collection, f, ensure_ascii=False, indent=2)

    print(f"تم الاحتفاظ بـ: {len(kept)} عنصر")
    print(f"مستبعد (خارج المنطقة): {skipped_bbox}")
    print(f"مستبعد (شكل تالف): {skipped_collapsed}")
    print(f"مستبعد (بدون إحداثيات): {skipped_no_geom}")
    print(f"تم الحفظ في: {out_path}")


if __name__ == "__main__":
    main()
