"""حساب ميزات قرب مرافق (مدارس، مستشفيات، مولات) لكل (مدينة، حي) لاستخدامها في موديل السعر.

المصدر الوحيد للمعلومات المكانية: Google.
- المرافق: google_places_services.csv (من Google Places).
- مراكز المدن: district_centroids.json (من Google Geocoding)، أو قيم ثابتة للشرقية فقط عند غياب الملف.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
GOOGLE_PLACES_PATH = RAW_DIR / "google_places_services.csv"
DISTRICT_CENTROIDS_JSON = RAW_DIR / "district_centroids.json"

# تقريب: كم متر في درجة واحدة (عند خط عرض ~26)
KM_PER_DEG_LAT = 111.0
KM_PER_DEG_LON = 111.0 * math.cos(math.radians(26))


def _dist_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """مسافة تقريبية بالكم بين نقطتين (درجات)."""
    dlat = (lat2 - lat1) * KM_PER_DEG_LAT
    dlon = (lon2 - lon1) * KM_PER_DEG_LON
    return math.sqrt(dlat * dlat + dlon * dlon)


def _min_dist_km(lat: float, lon: float, points: pd.DataFrame) -> float:
    """أقرب مسافة بالكم من (lat, lon) إلى أي نقطة في points (يجب أن يحتوي latitude, longitude)."""
    if points.empty:
        return 99.0
    dists = points.apply(
        lambda r: _dist_km(lat, lon, float(r["latitude"]), float(r["longitude"])),
        axis=1,
    )
    return float(dists.min())


def _count_within_km(lat: float, lon: float, points: pd.DataFrame, radius_km: float) -> int:
    """عدد النقاط ضمن نصف قطر معين (بالكم)."""
    if points.empty:
        return 0
    dists = points.apply(
        lambda r: _dist_km(lat, lon, float(r["latitude"]), float(r["longitude"])),
        axis=1,
    )
    return int((dists <= radius_km).sum())


DENSITY_RADIUS_KM = 3.0


def _load_pois_by_type() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """تحميل مرافق من Google فقط (google_places_services.csv). لا استخدام لـ OSM."""
    if not GOOGLE_PLACES_PATH.exists():
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = pd.read_csv(GOOGLE_PLACES_PATH, encoding="utf-8-sig")
    if df.empty or "type" not in df.columns:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df = df.dropna(subset=["latitude", "longitude"])
    t = df["type"].astype(str).str.lower()
    # تجميع أنواع Google مع الميزات الثلاثة للموديل
    schools = df[t.isin(["school"])].copy()
    hospitals = df[t.isin(["hospital", "pharmacy", "clinic"])].copy()
    malls = df[t.isin(["mall", "shopping"])].copy()
    return schools, hospitals, malls


def _load_district_centroids() -> dict[tuple[str, str], tuple[float, float]]:
    """(مدينة، حي) → (lat, lon) من district_centroids.json."""
    out = {}
    if DISTRICT_CENTROIDS_JSON.exists():
        with open(DISTRICT_CENTROIDS_JSON, encoding="utf-8") as f:
            data = json.load(f)
        for r in data.get("centroids", []):
            city = (r.get("city") or "").strip()
            district = (r.get("district") or "").strip() or "_غير_محدد"
            lat, lon = r.get("latitude"), r.get("longitude")
            if not city or lat is None or lon is None:
                continue
            out[(city, district)] = (float(lat), float(lon))
    return out


def _load_city_centroids() -> dict[str, tuple[float, float]]:
    """مركز كل مدينة من Google فقط: district_centroids.json (متوسط إحداثيات أحياء المدينة). قيم ثابتة للشرقية فقط عند غياب الملف."""
    district_c = _load_district_centroids()
    if district_c:
        by_city = {}
        for (_c, _d), pt in district_c.items():
            by_city.setdefault(_c, []).append(pt)
        centroids = {c: (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) for c, pts in by_city.items()}
        return centroids
    centroids = {}
    centroids["الدمام"] = (26.42, 50.10)
    centroids["الظهران"] = (26.29, 50.15)
    centroids["الخبر"] = (26.22, 50.20)
    return centroids


def build_osm_features_table(
    city_district_pairs: list[tuple[str, str]],
) -> pd.DataFrame:
    """جدول ميزات: مسافات أقرب مرافق + كثافة مرافق ضمن 3 كم (من Google Places).

    مخرجات: dist_school_km, dist_hospital_km, dist_mall_km, count_school_3km, count_hospital_3km, count_mall_3km.
    """
    schools, hospitals, malls = _load_pois_by_type()
    city_centroids = _load_city_centroids()
    district_centroids = _load_district_centroids()
    rows = []
    for city_ar, district in city_district_pairs:
        city_ar = (city_ar or "").strip()
        district = (district or "").strip() or "_غير_محدد"
        lat, lon = district_centroids.get((city_ar, district)) or city_centroids.get(city_ar, (26.3, 50.1))
        d_school = _min_dist_km(lat, lon, schools)
        d_hospital = _min_dist_km(lat, lon, hospitals)
        d_mall = _min_dist_km(lat, lon, malls)
        c_school = _count_within_km(lat, lon, schools, DENSITY_RADIUS_KM)
        c_hospital = _count_within_km(lat, lon, hospitals, DENSITY_RADIUS_KM)
        c_mall = _count_within_km(lat, lon, malls, DENSITY_RADIUS_KM)
        rows.append({
            "city": city_ar,
            "district": district,
            "dist_school_km": round(d_school, 3),
            "dist_hospital_km": round(d_hospital, 3),
            "dist_mall_km": round(d_mall, 3),
            "count_school_3km": c_school,
            "count_hospital_3km": c_hospital,
            "count_mall_3km": c_mall,
        })
    return pd.DataFrame(rows)
