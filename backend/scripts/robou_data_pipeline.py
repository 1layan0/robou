# robou_data_pipeline.py
# Python 3.10+
# pip install pandas numpy requests geopandas shapely osmnx networkx pyproj
#
# 1) تحميل بيانات منصة البيانات المفتوحة (قائمة روابط في open_data_urls.json)
# 2) تحميل GIS من OpenStreetMap (الدمام/الظهران/الخبر)
# 3) توليد كل CSVات المشروع دفعة واحدة بنفس الأسماء
#
# تشغيل:
#   python scripts/robou_data_pipeline.py --download_open_data --urls_json open_data_urls.json
#   python scripts/robou_data_pipeline.py --download_osm
#   python scripts/robou_data_pipeline.py --generate_csvs

from __future__ import annotations

import os
import json
import math
import uuid
import random
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# Optional heavy deps for GIS
try:
    import osmnx as ox
    import geopandas as gpd
    from shapely.geometry import Point
except Exception:
    ox = None
    gpd = None
    Point = None


# -----------------------------
# Utilities
# -----------------------------
def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def slugify(s: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in s).strip("_").lower()


def download_file(url: str, out_path: Path, timeout: int = 60) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    # meters
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def pick_city_center(city: str) -> tuple[float, float]:
    # Approximate centers (OK for synthetic generation). Adjust if you want.
    centers = {
        "Dammam": (26.4207, 50.0888),
        "Dhahran": (26.2361, 50.0393),
        "Al-Khobar": (26.2794, 50.2083),
    }
    return centers[city]


def jitter_point(lat, lon, max_km=6.0) -> tuple[float, float]:
    # random jitter in lat/lon approx
    # 1 deg lat ~111 km; lon scale by cos(lat)
    dy = (random.uniform(-max_km, max_km) / 111.0)
    dx = (random.uniform(-max_km, max_km) / (111.0 * math.cos(math.radians(lat))))
    return lat + dy, lon + dx


# -----------------------------
# 1) Open Data downloader
# -----------------------------
def download_open_data(url_list_path: Path, raw_dir: Path) -> None:
    """
    Provide a JSON file with a list of URLs:
    [
      {"name": "housing_indicators", "url": "https://.../resource.csv"},
      {"name": "transactions_eastern", "url": "https://.../resource.xlsx"}
    ]
    """
    if not url_list_path.exists():
        raise FileNotFoundError(f"URLs file not found: {url_list_path}")

    items = json.loads(url_list_path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise ValueError("URLs JSON must be a list.")
    if not items:
        print("No URLs in list; add entries with 'name' and 'url' to open_data_urls.json.")
        return

    ensure_dir(raw_dir)

    for item in items:
        name = item.get("name") or f"dataset_{uuid.uuid4().hex[:8]}"
        url = item.get("url")
        if not url:
            print(f"SKIP {name}: missing url")
            continue

        ext = Path(url.split("?")[0]).suffix
        if ext.lower() not in [".csv", ".xlsx", ".xls", ".json", ".zip"]:
            # still download, but default to .bin
            ext = ext if ext else ".bin"

        out_path = raw_dir / f"{slugify(name)}{ext}"
        print(f"Downloading: {name} -> {out_path.name}")
        download_file(url, out_path)

    print("Open data download done.")


# -----------------------------
# 2) OSM download (Facilities + Roads)
# -----------------------------
# bbox (west, south, east, north) لكل مدينة — استخدم عند فشل Geocoder
CITY_BBOXES = {
    "Dammam": (49.95, 26.22, 50.15, 26.48),
    "Dhahran": (50.08, 26.26, 50.16, 26.35),
    "Al-Khobar": (50.15, 26.18, 50.22, 26.30),
}


def download_osm(city: str, out_dir: Path) -> None:
    if ox is None:
        raise RuntimeError("Missing GIS deps. Install: pip install osmnx geopandas shapely pyproj")

    ensure_dir(out_dir)

    place = f"{city}, Saudi Arabia"
    print(f"[OSM] Fetching facilities: {place}")

    tags = {
        "amenity": ["school", "hospital", "university"],
        "shop": True,
        "leisure": True,
        "building": True,
    }

    try:
        gdf = ox.features_from_place(place, tags=tags)
    except (TypeError, Exception):
        # استخدام bbox عند فشل Nominatim — (west, south, east, north)
        if city not in CITY_BBOXES:
            raise
        bbox = CITY_BBOXES[city]
        print(f"[OSM] Using bbox for {city}: {bbox}")
        gdf = ox.features_from_bbox(bbox, tags=tags)
    gdf = gdf.reset_index()

    # Keep representative point for non-point geoms
    def rep_lat(geom):
        try:
            p = geom.representative_point()
            return float(p.y)
        except Exception:
            return np.nan

    def rep_lon(geom):
        try:
            p = geom.representative_point()
            return float(p.x)
        except Exception:
            return np.nan

    gdf["lat"] = gdf["geometry"].apply(rep_lat)
    gdf["lon"] = gdf["geometry"].apply(rep_lon)
    gdf["city"] = city

    # Build Facility.csv-like output
    def infer_type(row):
        for key in ["amenity", "shop", "leisure", "building"]:
            if key in row and pd.notna(row[key]):
                return str(row[key])
        return "unknown"

    fac = pd.DataFrame({
        "facility_id": [f"FAC_{uuid.uuid4().hex[:10].upper()}" for _ in range(len(gdf))],
        "type": gdf.apply(infer_type, axis=1),
        "lat": gdf["lat"],
        "lon": gdf["lon"],
        "city": gdf["city"],
        "source": "OpenStreetMap",
    }).dropna(subset=["lat", "lon"])

    fac_path = out_dir / f"Facility_{slugify(city)}.csv"
    fac.to_csv(fac_path, index=False, encoding="utf-8-sig")
    print(f"[OSM] Saved facilities: {fac_path}")

    # Roads graph
    print(f"[OSM] Fetching roads graph: {place}")
    try:
        G = ox.graph_from_place(place, network_type="drive")
    except (TypeError, Exception):
        if city in CITY_BBOXES:
            bbox = CITY_BBOXES[city]
            G = ox.graph_from_bbox(bbox=bbox, network_type="drive")
        else:
            raise
    roads = ox.graph_to_gdfs(G, nodes=False, edges=True).reset_index()
    roads_path = out_dir / f"Roads_{slugify(city)}.geojson"
    roads.to_file(roads_path, driver="GeoJSON")
    print(f"[OSM] Saved roads: {roads_path}")


# -----------------------------
# 3) Generate all CSVs (Synthetic)
# -----------------------------
def generate_all_csvs(out_dir: Path, n_parcels=600, n_facilities=120, n_transactions=1600, n_listings=400) -> None:
    ensure_dir(out_dir)

    random.seed(42)
    np.random.seed(42)

    cities = ["Dammam", "Dhahran", "Al-Khobar"]

    # 3.1 Users
    users = pd.DataFrame([
        {"user_id": "USR_ADMIN", "role": "Admin", "email": "admin@robou.local"},
        {"user_id": "USR_ANALYST", "role": "Analyst", "email": "analyst@robou.local"},
    ])
    users.to_csv(out_dir / "User.csv", index=False, encoding="utf-8-sig")

    # 3.2 DataSource
    datasources = pd.DataFrame([
        {"source_id": 1, "name": "OpenData", "details": "data.gov.sa"},
        {"source_id": 2, "name": "REGA", "details": "rega.gov.sa"},
        {"source_id": 3, "name": "OpenStreetMap", "details": "osm.org"},
    ])
    datasources.to_csv(out_dir / "DataSource.csv", index=False, encoding="utf-8-sig")

    # 3.3 Zoning
    zoning_types = ["Residential", "Commercial", "Mixed-use", "Industrial", "Government", "Agricultural"]
    zoning = pd.DataFrame([{"zoning_id": i+1, "zoning_type": z} for i, z in enumerate(zoning_types)])
    zoning.to_csv(out_dir / "Zoning.csv", index=False, encoding="utf-8-sig")

    # 3.4 Neighborhoods (synthetic placeholders - replace later with Amanah list)
    neighborhoods = []
    neighborhood_city_map = []
    nid = 1
    for c in cities:
        lat0, lon0 = pick_city_center(c)
        for i in range(1, 26):
            name = f"{c}_Neighborhood_{i:02d}"
            lat, lon = jitter_point(lat0, lon0, max_km=8.0)
            neighborhoods.append({"neighborhood_id": nid, "name": name, "city": c, "lat": lat, "lon": lon})
            neighborhood_city_map.append({"neighborhood_id": nid, "city": c})
            nid += 1

    Neighborhood = pd.DataFrame(neighborhoods)
    Neighborhood.to_csv(out_dir / "Neighborhood.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(neighborhood_city_map).to_csv(out_dir / "NeighborhoodCityMap.csv", index=False, encoding="utf-8-sig")

    # 3.5 Facilities (synthetic - you can overwrite later with OSM Facility outputs)
    facility_rows = []
    facility_types = ["school", "hospital", "mall", "university", "park"]
    for _ in range(n_facilities):
        c = random.choice(cities)
        lat0, lon0 = pick_city_center(c)
        lat, lon = jitter_point(lat0, lon0, max_km=10.0)
        facility_rows.append({
            "facility_id": f"FAC_{uuid.uuid4().hex[:10].upper()}",
            "type": random.choice(facility_types),
            "lat": lat,
            "lon": lon,
            "city": c,
            "source": "synthetic"
        })
    Facility = pd.DataFrame(facility_rows)
    Facility.to_csv(out_dir / "Facility.csv", index=False, encoding="utf-8-sig")

    # 3.6 Land Parcels
    base_sar_per_m2 = {
        "Dammam": 2200,
        "Dhahran": 2600,
        "Al-Khobar": 3000
    }

    parcel_rows = []
    for i in range(1, n_parcels + 1):
        c = random.choice(cities)
        neigh = Neighborhood[Neighborhood["city"] == c].sample(1, random_state=random.randint(1, 999999)).iloc[0]
        area = int(np.clip(np.random.normal(loc=750, scale=250), 250, 2000))
        z_id = int(np.random.choice(zoning["zoning_id"], p=[0.55, 0.15, 0.15, 0.08, 0.05, 0.02]))
        lat, lon = jitter_point(float(neigh["lat"]), float(neigh["lon"]), max_km=2.5)
        parcel_rows.append({
            "parcel_id": f"PAR_{i:05d}",
            "city": c,
            "neighborhood_id": int(neigh["neighborhood_id"]),
            "area_m2": area,
            "zoning_id": z_id,
            "lat": lat,
            "lon": lon,
            "source_id": 1
        })

    LandParcel = pd.DataFrame(parcel_rows)
    LandParcel.to_csv(out_dir / "LandParcel.csv", index=False, encoding="utf-8-sig")

    # 3.7 ParcelFacilityProximity
    prox_rows = []
    fac_by_city = {c: Facility[Facility["city"] == c].reset_index(drop=True) for c in cities}

    for _, p in LandParcel.iterrows():
        c = p["city"]
        facs = fac_by_city[c]
        if facs.empty:
            continue
        dists = []
        for idx, f in facs.iterrows():
            d = haversine_m(p["lat"], p["lon"], f["lat"], f["lon"])
            dists.append((idx, d))
        dists.sort(key=lambda x: x[1])
        for rank, (idx, d) in enumerate(dists[:3], start=1):
            f = facs.iloc[idx]
            prox_rows.append({
                "parcel_id": p["parcel_id"],
                "facility_id": f["facility_id"],
                "distance_m": round(d, 2),
                "rank": rank
            })

    ParcelFacilityProximity = pd.DataFrame(prox_rows)
    ParcelFacilityProximity.to_csv(out_dir / "ParcelFacilityProximity.csv", index=False, encoding="utf-8-sig")

    # 3.8 Transactions
    zoning_factor = {
        "Residential": 1.00,
        "Commercial": 1.25,
        "Mixed-use": 1.15,
        "Industrial": 0.80,
        "Government": 0.60,
        "Agricultural": 0.50,
    }
    zoning_map = dict(zip(zoning["zoning_id"], zoning["zoning_type"]))

    start_date = datetime(2022, 1, 1)
    end_date = datetime(2025, 12, 31)
    days_range = (end_date - start_date).days

    tx_rows = []
    parcels_sample = LandParcel.sample(n=min(n_transactions, len(LandParcel)), replace=True, random_state=42).reset_index(drop=True)

    for i in range(n_transactions):
        p = parcels_sample.iloc[i % len(parcels_sample)]
        c = p["city"]
        zt = zoning_map[int(p["zoning_id"])]
        base = base_sar_per_m2[c] * zoning_factor[zt]
        prox = ParcelFacilityProximity[ParcelFacilityProximity["parcel_id"] == p["parcel_id"]]
        bonus = 0.0
        if not prox.empty:
            nearest = float(prox.sort_values("distance_m").iloc[0]["distance_m"])
            bonus = np.clip((3000 - nearest) / 3000, 0, 1) * 0.12
        noise = np.random.normal(0, 0.10)
        sar_per_m2 = base * (1 + bonus + noise)
        price = max(50000, sar_per_m2 * float(p["area_m2"]))
        dt = start_date + timedelta(days=random.randint(0, days_range))

        tx_rows.append({
            "transaction_id": f"TRX_{i+1:06d}",
            "parcel_id": p["parcel_id"],
            "city": c,
            "neighborhood_id": int(p["neighborhood_id"]),
            "date": dt.strftime("%Y-%m-%d"),
            "price_sar": int(price),
            "price_per_m2_sar": round(price / float(p["area_m2"]), 2),
            "source_id": 2
        })

    Transaction = pd.DataFrame(tx_rows)
    Transaction.to_csv(out_dir / "Transaction.csv", index=False, encoding="utf-8-sig")

    # 3.9 Listings
    listing_rows = []
    parcels_for_listings = LandParcel.sample(n=min(n_listings, len(LandParcel)), replace=False, random_state=7).reset_index(drop=True)
    for i, p in parcels_for_listings.iterrows():
        c = p["city"]
        zt = zoning_map[int(p["zoning_id"])]
        base = base_sar_per_m2[c] * zoning_factor[zt]
        sar_per_m2 = base * (1 + np.random.normal(0.06, 0.07))
        list_price = max(60000, sar_per_m2 * float(p["area_m2"]))

        listing_rows.append({
            "listing_id": f"LST_{i+1:05d}",
            "parcel_id": p["parcel_id"],
            "city": c,
            "neighborhood_id": int(p["neighborhood_id"]),
            "asking_price_sar": int(list_price),
            "status": random.choice(["active", "active", "active", "sold", "expired"]),
            "posted_date": (end_date - timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d"),
            "source_id": 1
        })
    Listing = pd.DataFrame(listing_rows)
    Listing.to_csv(out_dir / "Listing.csv", index=False, encoding="utf-8-sig")

    # 3.10 ParcelImage
    img_rows = []
    for _, p in LandParcel.iterrows():
        img_rows.append({
            "parcel_id": p["parcel_id"],
            "image_url": f"https://example.com/parcel_images/{p['parcel_id']}.jpg"
        })
    ParcelImage = pd.DataFrame(img_rows)
    ParcelImage.to_csv(out_dir / "ParcelImage.csv", index=False, encoding="utf-8-sig")

    # 3.11 Predictions
    pred_rows = []
    for _, p in LandParcel.iterrows():
        c = p["city"]
        zt = zoning_map[int(p["zoning_id"])]
        base = base_sar_per_m2[c] * zoning_factor[zt]
        pred_sar_per_m2 = base * (1 + np.random.normal(0.02, 0.06))
        pred_price = max(50000, pred_sar_per_m2 * float(p["area_m2"]))
        confidence = float(np.clip(np.random.normal(0.78, 0.08), 0.50, 0.95))

        pred_rows.append({
            "prediction_id": f"PRD_{uuid.uuid4().hex[:12].upper()}",
            "parcel_id": p["parcel_id"],
            "predicted_price_sar": int(pred_price),
            "confidence": round(confidence, 3),
            "model_version": "v1.0"
        })
    Prediction = pd.DataFrame(pred_rows)
    Prediction.to_csv(out_dir / "Prediction.csv", index=False, encoding="utf-8-sig")

    # 3.12 Attribution
    (out_dir / "ATTRIBUTION.txt").write_text(
        "Some GIS layers may be derived from OpenStreetMap contributors.\n"
        "Synthetic data generated for academic prototype/testing only.\n",
        encoding="utf-8"
    )

    print(f"✅ Generated all CSVs in: {out_dir}")


# -----------------------------
# Main / CLI
# -----------------------------
def main():
    # Default urls_json relative to project root (parent of scripts/)
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    default_urls = project_root / "open_data_urls.json"

    parser = argparse.ArgumentParser(description="Robou Data Pipeline: Open Data + OSM + Generate CSVs")
    parser.add_argument("--base_dir", type=str, default=None, help="Base data directory (default: data/ in project root)")
    parser.add_argument("--urls_json", type=str, default=str(default_urls), help="JSON file with list of {name, url} for open data resources")
    parser.add_argument("--download_open_data", action="store_true", help="Download open data resources listed in urls_json")
    parser.add_argument("--download_osm", action="store_true", help="Download OSM facilities+roads for Dammam/Dhahran/Al-Khobar")
    parser.add_argument("--generate_csvs", action="store_true", help="Generate synthetic CSVs for all tables")

    parser.add_argument("--n_parcels", type=int, default=600)
    parser.add_argument("--n_facilities", type=int, default=120)
    parser.add_argument("--n_transactions", type=int, default=1600)
    parser.add_argument("--n_listings", type=int, default=400)

    args = parser.parse_args()

    base_dir = Path(args.base_dir) if args.base_dir else project_root / "data"
    raw_dir = base_dir / "raw"
    processed_dir = base_dir / "processed"
    osm_dir = base_dir / "osm"
    generated_dir = base_dir / "generated"

    ensure_dir(raw_dir)
    ensure_dir(processed_dir)
    ensure_dir(osm_dir)
    ensure_dir(generated_dir)

    if args.download_open_data:
        download_open_data(Path(args.urls_json), raw_dir)

    if args.download_osm:
        for city in ["Dammam", "Dhahran", "Al-Khobar"]:
            download_osm(city, osm_dir)

    if args.generate_csvs:
        generate_all_csvs(
            generated_dir,
            n_parcels=args.n_parcels,
            n_facilities=args.n_facilities,
            n_transactions=args.n_transactions,
            n_listings=args.n_listings
        )


if __name__ == "__main__":
    main()
