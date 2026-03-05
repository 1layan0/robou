#!/usr/bin/env python3
"""
جلب أكبر عدد من المرافق والأماكن من Google Places API (Text Search Legacy)
للمنطقة الشرقية: الدمام، الخبر، الظهران.
المخرجات: data/raw/google_places_services.csv. المصدر الوحيد للمعلومات المكانية — لا OSM.
يحتاج GOOGLE_MAPS_API_KEY في .env.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.settings import settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "data" / "raw"
OUT_CSV = OUT_DIR / "google_places_services.csv"
OUT_CSV_CHECKPOINT = OUT_DIR / "google_places_services_checkpoint.csv"
CONFIG_DISTRICTS = PROJECT_ROOT / "config" / "city_districts.json"
CITY_AR_TO_EN = {"الدمام": "Dammam", "الخبر": "Al Khobar", "الظهران": "Dhahran"}

CITIES = [
    ("Dammam", "الدمام"),
    ("Al Khobar", "الخبر"),
    ("Dhahran", "الظهران"),
]
PLACES_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
MAX_PAGES_PER_QUERY = 10
REQUEST_TIMEOUT = 45
MAX_RETRIES = 3
SAVE_EVERY_N_QUERIES = 100
# حدود المنطقة الشرقية (الدمام، الخبر، الظهران) تقريباً
LAT_MIN, LAT_MAX = 25.8, 27.2
LON_MIN, LON_MAX = 49.2, 50.5

# مرافق وأماكن — استعلامات موسّعة (إنجليزي + عربي حيث يزيد النتائج)
SEARCHES = [
    ("school", "school"),
    ("university", "school"),
    ("college", "school"),
    ("kindergarten", "school"),
    ("nursery", "school"),
    ("مدرسة", "school"),
    ("جامعة", "school"),
    ("hospital", "hospital"),
    ("pharmacy", "pharmacy"),
    ("clinic", "clinic"),
    ("medical center", "clinic"),
    ("dental clinic", "clinic"),
    ("مستشفى", "hospital"),
    ("صيدلية", "pharmacy"),
    ("عيادة", "clinic"),
    ("shopping_mall", "mall"),
    ("shopping center", "shopping"),
    ("supermarket", "shopping"),
    ("hypermarket", "shopping"),
    ("mall", "mall"),
    ("مول", "mall"),
    ("مركز تجاري", "shopping"),
    ("سوبرماركت", "shopping"),
    ("mosque", "mosque"),
    ("مسجد", "mosque"),
    ("park", "park"),
    ("حديقة", "park"),
    ("bank", "bank"),
    ("ATM", "bank"),
    ("بنك", "bank"),
    ("gas station", "gas_station"),
    ("محطة وقود", "gas_station"),
    ("police", "police"),
    ("شرطة", "police"),
    ("fire station", "fire_station"),
    ("restaurant", "restaurant"),
    ("مطعم", "restaurant"),
    ("cafe", "cafe"),
    ("coffee shop", "cafe"),
    ("مقهى", "cafe"),
    ("gym", "gym"),
    ("نادي رياضي", "gym"),
    ("hotel", "hotel"),
    ("فندق", "hotel"),
    ("library", "library"),
    ("مكتبة", "library"),
    ("museum", "museum"),
    ("متحف", "museum"),
    ("stadium", "stadium"),
    ("ملعب", "stadium"),
    ("cinema", "cinema"),
    ("theater", "cinema"),
    ("سينما", "cinema"),
    ("playground", "park"),
    ("garden", "park"),
    ("post office", "post_office"),
    ("بريد", "post_office"),
    ("car wash", "car_wash"),
    ("غسيل سيارات", "car_wash"),
    ("laundry", "laundry"),
    ("real estate office", "real_estate"),
    ("مكتب عقاري", "real_estate"),
    ("salon", "salon"),
    ("bakery", "bakery"),
    ("مخبز", "bakery"),
    ("petrol station", "gas_station"),
    ("parking", "parking"),
    ("مواقف", "parking"),
    ("government office", "government"),
    ("ministry", "government"),
    ("دوائر حكومية", "government"),
    # إضافي لزيادة التغطية
    ("vet", "clinic"),
    ("daycare", "school"),
    ("driving school", "school"),
    ("language center", "school"),
    ("training center", "school"),
    ("مركز تدريب", "school"),
    ("حضانة", "school"),
    ("wedding hall", "restaurant"),
    ("event venue", "restaurant"),
    ("قاعة أفراح", "restaurant"),
    ("furniture store", "shopping"),
    ("electronics store", "shopping"),
    ("محل إلكترونيات", "shopping"),
    ("car showroom", "real_estate"),
    ("معرض سيارات", "real_estate"),
    ("insurance company", "bank"),
    ("شركة تأمين", "bank"),
    ("lawyer", "government"),
    ("محامي", "government"),
    ("travel agency", "real_estate"),
    ("وكالة سفر", "real_estate"),
    ("car rental", "car_wash"),
    ("تأجير سيارات", "car_wash"),
    ("maintenance", "car_wash"),
    ("صيانة", "car_wash"),
    ("pet shop", "shopping"),
    ("محل حيوانات", "shopping"),
    ("florist", "shopping"),
    ("محل زهور", "shopping"),
    ("bookstore", "library"),
    ("مكتبة كتب", "library"),
    ("laboratory", "clinic"),
    ("مختبر", "clinic"),
    ("optical", "clinic"),
    ("محل نظارات", "clinic"),
    ("spa", "salon"),
    ("سبا", "salon"),
    ("barber", "salon"),
    ("حلاق", "salon"),
    ("tailor", "salon"),
    ("خياط", "salon"),
    ("dry cleaner", "laundry"),
    ("مغسلة", "laundry"),
    ("stationery", "shopping"),
    ("قرطاسية", "shopping"),
    ("building materials", "shopping"),
    ("مواد بناء", "shopping"),
    ("sports club", "gym"),
    ("نادي رياضي", "gym"),
    ("swimming pool", "gym"),
    ("مسبح", "gym"),
    ("kids area", "park"),
    ("منطقة أطفال", "park"),
    ("coastal", "park"),
    ("كورنيش", "park"),
    ("marina", "park"),
    ("مرسى", "park"),
    ("exhibition", "museum"),
    ("معرض", "museum"),
    ("cultural center", "library"),
    ("مركز ثقافي", "library"),
    # نقل وبنية تحتية (تؤثر على السعر والدقة)
    ("airport", "transport"),
    ("مطار", "transport"),
    ("port", "transport"),
    ("ميناء", "transport"),
    ("bus station", "transport"),
    ("محطة حافلات", "transport"),
    ("taxi stand", "transport"),
    ("موقف تاكسي", "transport"),
    ("highway exit", "transport"),
    ("طريق سريع", "transport"),
    ("ambulance", "hospital"),
    ("إسعاف", "hospital"),
    ("blood bank", "hospital"),
    ("بنك دم", "hospital"),
]

# استعلامات حسب الحي (مرافق داخل كل حي — تزيد دقة الموديل)
DISTRICT_TERMS = [
    ("restaurant", "restaurant"),
    ("mall", "mall"),
    ("school", "school"),
    ("clinic", "clinic"),
    ("mosque", "mosque"),
    ("park", "park"),
    ("pharmacy", "pharmacy"),
    ("bank", "bank"),
    ("مطعم", "restaurant"),
    ("مول", "mall"),
    ("مدرسة", "school"),
    ("عيادة", "clinic"),
    ("مسجد", "mosque"),
    ("حديقة", "park"),
]

# مشاريع — عقارية، سكنية، تجارية، تنموية
PROJECT_SEARCHES = [
    ("real estate project", "project"),
    ("housing project", "project"),
    ("residential project", "project"),
    ("residential compound", "project"),
    ("compound", "project"),
    ("commercial project", "project"),
    ("commercial development", "project"),
    ("development project", "project"),
    ("real estate development", "project"),
    ("مشروع سكني", "project"),
    ("مشروع عقاري", "project"),
    ("مشروع تجاري", "project"),
    ("مشروع تنموي", "project"),
    ("مجمع سكني", "project"),
    ("مشروع إسكان", "project"),
    ("مجمع تجاري", "project"),
    ("ضاحية", "project"),
    ("حي سكني", "project"),
    ("tower", "project"),
    ("برج", "project"),
    ("mixed use", "project"),
    ("استخدام مختلط", "project"),
    ("office building", "project"),
    ("مبنى مكاتب", "project"),
    ("industrial area", "project"),
    ("منطقة صناعية", "project"),
    ("logistics", "project"),
    ("لوجستي", "project"),
    ("medical complex", "project"),
    ("مجمع طبي", "project"),
    ("education city", "project"),
    ("مدينة تعليمية", "project"),
    ("entertainment", "project"),
    ("ترفيه", "project"),
    ("waterfront", "project"),
    ("واجهة بحرية", "project"),
    ("new city", "project"),
    ("مدينة جديدة", "project"),
]

# مشاريع وأماكن قيد الإنشاء / قريباً
UNDER_CONSTRUCTION_SEARCHES = [
    ("under construction mall", "under_construction"),
    ("under construction project", "under_construction"),
    ("mall under construction", "under_construction"),
    ("opening soon mall", "under_construction"),
    ("opening soon", "under_construction"),
    ("قيد الإنشاء", "under_construction"),
    ("مشروع قيد الإنشاء", "under_construction"),
    ("مول قيد الإنشاء", "under_construction"),
    ("قريباً", "under_construction"),
    ("افتتاح قريب", "under_construction"),
    ("Avenues mall", "under_construction"),
    ("الأفنيوز", "under_construction"),
    ("Avenues Doha", "under_construction"),
    ("Avenues Dhahran", "under_construction"),
    ("new mall", "under_construction"),
    ("مول جديد", "under_construction"),
    ("قيد الإنشاء المنطقة الشرقية", "under_construction"),
    ("under construction Eastern Province", "under_construction"),
    ("coming soon mall", "under_construction"),
    ("مشروع جديد", "under_construction"),
    ("under construction compound", "under_construction"),
    ("مجمع قيد الإنشاء", "under_construction"),
    ("under construction tower", "under_construction"),
    ("برج قيد الإنشاء", "under_construction"),
]

# استعلامات ثابتة (بدون دورة المدن) — معالم ومشاريع معروفة
SPECIFIC_QUERIES = [
    ("Avenues Mall Al Doha Dhahran Saudi Arabia", "mall"),
    ("الأفنيوز الدوحة الظهران السعودية", "mall"),
    ("Avenues Doha Dhahran Saudi Arabia", "mall"),
    ("The Avenues Doha Dhahran", "mall"),
    ("مول الأفنيوز الظهران", "mall"),
    ("under construction mall Eastern Province Saudi Arabia", "under_construction"),
    ("مشاريع قيد الإنشاء المنطقة الشرقية", "under_construction"),
    ("Dammam Corniche", "park"),
    ("Khobar Corniche", "park"),
    ("كورنيش الدمام", "park"),
    ("كورنيش الخبر", "park"),
    ("King Fahd Park Dammam", "park"),
    ("Half Moon Beach Khobar", "park"),
    ("Ithra Dhahran", "museum"),
    ("إثراء الظهران", "museum"),
    ("Danmann Mall", "mall"),
    ("Rashid Mall Dammam", "mall"),
    ("مول الراشد الدمام", "mall"),
    ("Al Rashid Mall Khobar", "mall"),
    ("Eastern Province malls", "mall"),
    ("مولات المنطقة الشرقية", "mall"),
    ("King Fahd International Airport", "transport"),
    ("مطار الملك فهد", "transport"),
    ("Dammam Port", "transport"),
    ("ميناء الدمام", "transport"),
    ("King Fahd Causeway", "transport"),
    ("جسر الملك فهد", "transport"),
    ("Eastern Province Saudi Arabia points of interest", "park"),
]


def _in_bounds(lat: float, lon: float) -> bool:
    """هل النقطة داخل حدود المنطقة الشرقية (الدمام، الظهران، الخبر) فقط؟"""
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX


def _save_checkpoint(rows: list[dict]) -> None:
    """حفظ النتائج الحالية في ملف checkpoint منفصل (لا يُستبدل الملف الرئيسي)."""
    if not rows:
        return
    pd.DataFrame(rows).to_csv(OUT_CSV_CHECKPOINT, index=False, encoding="utf-8-sig")
    print(f"    [حفظ مؤقت] {len(rows)} سجل → {OUT_CSV_CHECKPOINT.name}")


def fetch_places(query: str, api_key: str, page_token: str | None = None) -> dict:
    """طلب واحد من Places Text Search (Legacy) مع إعادة محاولة عند timeout أو خطأ شبكة."""
    params = {"query": query, "key": api_key, "region": "sa"}
    if page_token:
        params["pagetoken"] = page_token
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(PLACES_URL, params=params, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.json()
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as e:
            last_err = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 + attempt * 2)
    raise last_err


def _run_query_loop(
    api_key: str,
    rows: list[dict],
    seen_place_ids: set[str],
    query_template: str,
    searches: list[tuple[str, str]],
    total_queries: int,
    start_idx: int,
) -> None:
    """تشغيل مجموعة استعلامات (مدينة + نوع) مع التصفح لأقصى عدد صفحات."""
    idx = start_idx
    for city_en, _ in CITIES:
        for term, our_type in searches:
            idx += 1
            query = query_template.format(term=term, city=city_en)
            data = fetch_places(query, api_key)
            time.sleep(0.25)
            page = 0
            while page < MAX_PAGES_PER_QUERY:
                if data.get("status") != "OK":
                    break
                for p in data.get("results", []):
                    pid = p.get("place_id")
                    if pid and pid in seen_place_ids:
                        continue
                    loc = p.get("geometry", {}).get("location")
                    if not loc:
                        continue
                    lat, lng = round(float(loc["lat"]), 6), round(float(loc["lng"]), 6)
                    if not _in_bounds(lat, lng):
                        continue
                    if pid:
                        seen_place_ids.add(pid)
                    rows.append({
                        "type": our_type,
                        "name": (p.get("name") or "").strip() or "—",
                        "latitude": lat,
                        "longitude": lng,
                    })
                token = data.get("next_page_token")
                if not token:
                    break
                page += 1
                time.sleep(1.5)
                data = fetch_places(query, api_key, page_token=token)
                time.sleep(0.25)
            if idx % 15 == 0 or idx == total_queries:
                print(f"  [{idx}/{total_queries}] {len(rows)} مكان حتى الآن")
            if idx % SAVE_EVERY_N_QUERIES == 0 and rows:
                _save_checkpoint(rows)
    return


def _run_specific_queries(
    api_key: str,
    rows: list[dict],
    seen_place_ids: set[str],
    total_queries: int,
    start_idx: int,
) -> None:
    """تشغيل استعلامات ثابتة (معالم ومشاريع معروفة بالاسم) بدون دورة المدن."""
    for i, (query, our_type) in enumerate(SPECIFIC_QUERIES):
        idx = start_idx + i + 1
        data = fetch_places(query, api_key)
        time.sleep(0.25)
        page = 0
        while page < MAX_PAGES_PER_QUERY:
            if data.get("status") != "OK":
                break
            for p in data.get("results", []):
                pid = p.get("place_id")
                if pid and pid in seen_place_ids:
                    continue
                loc = p.get("geometry", {}).get("location")
                if not loc:
                    continue
                lat, lng = round(float(loc["lat"]), 6), round(float(loc["lng"]), 6)
                if not _in_bounds(lat, lng):
                    continue
                if pid:
                    seen_place_ids.add(pid)
                rows.append({
                    "type": our_type,
                    "name": (p.get("name") or "").strip() or "—",
                    "latitude": lat,
                    "longitude": lng,
                })
            token = data.get("next_page_token")
            if not token:
                break
            page += 1
            time.sleep(1.5)
            data = fetch_places(query, api_key, page_token=token)
            time.sleep(0.25)
        print(f"  [{idx}/{total_queries}] {len(rows)} مكان (استعلام ثابت)")
        if (start_idx + i + 1) % SAVE_EVERY_N_QUERIES == 0 and rows:
            _save_checkpoint(rows)
    return


def _load_district_pairs() -> list[tuple[str, str]]:
    """(city_en, district_ar) من config/city_districts.json لكل المدن الثلاث."""
    if not CONFIG_DISTRICTS.exists():
        return []
    with open(CONFIG_DISTRICTS, encoding="utf-8") as f:
        data = json.load(f)
    pairs = []
    for city_ar, districts in data.items():
        city_en = CITY_AR_TO_EN.get((city_ar or "").strip())
        if not city_en:
            continue
        for d in districts or []:
            d = (d or "").strip()
            if d:
                pairs.append((city_en, d))
    return pairs


def _run_district_queries(
    api_key: str,
    rows: list[dict],
    seen_place_ids: set[str],
    total_queries: int,
    start_idx: int,
) -> None:
    """استعلامات مرافق داخل كل حي (ترفع دقة الموديل)."""
    district_pairs = _load_district_pairs()
    if not district_pairs:
        return
    idx = start_idx
    n_district = len(district_pairs) * len(DISTRICT_TERMS)
    for city_en, district in district_pairs:
        for term, our_type in DISTRICT_TERMS:
            idx += 1
            query = f"{term} {district} {city_en} Saudi Arabia"
            data = fetch_places(query, api_key)
            time.sleep(0.2)
            page = 0
            while page < MAX_PAGES_PER_QUERY:
                if data.get("status") != "OK":
                    break
                for p in data.get("results", []):
                    pid = p.get("place_id")
                    if pid and pid in seen_place_ids:
                        continue
                    loc = p.get("geometry", {}).get("location")
                    if not loc:
                        continue
                    lat, lng = round(float(loc["lat"]), 6), round(float(loc["lng"]), 6)
                    if not _in_bounds(lat, lng):
                        continue
                    if pid:
                        seen_place_ids.add(pid)
                    rows.append({
                        "type": our_type,
                        "name": (p.get("name") or "").strip() or "—",
                        "latitude": lat,
                        "longitude": lng,
                    })
                token = data.get("next_page_token")
                if not token:
                    break
                page += 1
                time.sleep(1.5)
                data = fetch_places(query, api_key, page_token=token)
                time.sleep(0.2)
            if idx % 100 == 0 or idx == start_idx + n_district:
                print(f"  [{idx}/{total_queries}] {len(rows)} مكان (حسب الحي)")
            if idx % SAVE_EVERY_N_QUERIES == 0 and rows:
                _save_checkpoint(rows)
    return


def collect_pois(api_key: str, skip_districts: bool = False) -> list[dict]:
    """جمع النتائج: مرافق + مشاريع + قيد الإنشاء + ثابتة؛ اختياريًا + مرافق حسب الحي."""
    rows = []
    seen_place_ids = set()
    n_place = len(CITIES) * len(SEARCHES)
    n_project = len(CITIES) * len(PROJECT_SEARCHES)
    n_under = len(CITIES) * len(UNDER_CONSTRUCTION_SEARCHES)
    n_specific = len(SPECIFIC_QUERIES)
    district_pairs = _load_district_pairs() if not skip_districts else []
    n_district = len(district_pairs) * len(DISTRICT_TERMS) if district_pairs else 0
    total_queries = n_place + n_project + n_under + n_specific + n_district

    print("  مرافق وأماكن (إنجليزي + عربي)...")
    _run_query_loop(
        api_key, rows, seen_place_ids,
        query_template="{term} in {city} Saudi Arabia",
        searches=SEARCHES,
        total_queries=total_queries,
        start_idx=0,
    )
    print("  مشاريع (عقارية، سكنية، تجارية، تنموية)...")
    _run_query_loop(
        api_key, rows, seen_place_ids,
        query_template="{term} {city} Saudi Arabia",
        searches=PROJECT_SEARCHES,
        total_queries=total_queries,
        start_idx=n_place,
    )
    print("  مشاريع قيد الإنشاء / قريباً (منها الأفنيوز ومولات تحت الإنشاء)...")
    _run_query_loop(
        api_key, rows, seen_place_ids,
        query_template="{term} {city} Saudi Arabia",
        searches=UNDER_CONSTRUCTION_SEARCHES,
        total_queries=total_queries,
        start_idx=n_place + n_project,
    )
    print("  استعلامات ثابتة (الأفنيوز، مطار، ميناء، معالم)...")
    _run_specific_queries(
        api_key, rows, seen_place_ids,
        total_queries=total_queries,
        start_idx=n_place + n_project + n_under,
    )
    if district_pairs:
        print("  مرافق حسب الحي (أحياء الدمام والخبر والظهران — لرفع دقة الموديل)...")
        _run_district_queries(
            api_key, rows, seen_place_ids,
            total_queries=total_queries,
            start_idx=n_place + n_project + n_under + n_specific,
        )
    return rows


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="جلب مرافق ومشاريع من Google Places")
    parser.add_argument("--no-districts", action="store_true", help="تخطي استعلامات الأحياء (أسرع، ~652 استعلام بدل 2934)")
    args = parser.parse_args()
    api_key = (settings.google_maps_api_key or "").strip()
    if not api_key:
        print("أضيفي GOOGLE_MAPS_API_KEY في .env")
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    msg = "مرافق + مشاريع + قيد الإنشاء + ثابتة"
    if not args.no_districts:
        msg += " + مرافق حسب الحي"
    print(f"جاري جلب البيانات من Google Places: {msg}...")
    rows = collect_pois(api_key, skip_districts=args.no_districts)
    df = pd.DataFrame(rows)
    if df.empty:
        print("لم يُعثر على نتائج. تحققي من المفتاح وتفعيل Places API.")
        return
    # دمج مع الملف الحالي إن وُجد حتى لا ينقص العدد عند تشغيل بأقل استعلامات (مثلاً --no-districts)
    if OUT_CSV.exists():
        try:
            existing = pd.read_csv(OUT_CSV, encoding="utf-8-sig")
            if not existing.empty and set(existing.columns) >= {"name", "latitude", "longitude"}:
                combined = pd.concat([existing, df], ignore_index=True)
                combined = combined.drop_duplicates(subset=["name", "latitude", "longitude"], keep="first")
                if len(combined) > len(df):
                    df = combined
                    print(f"دمج مع الملف الحالي: {len(combined)} سجل (بدون تكرار)")
        except Exception as e:
            print(f"تحذير: لم نستطع دمج الملف الحالي: {e}")
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"حفظ {len(df)} سجل في {OUT_CSV}")
    if OUT_CSV_CHECKPOINT.exists():
        OUT_CSV_CHECKPOINT.unlink()
        print(f"حذف ملف الحفظ المؤقت {OUT_CSV_CHECKPOINT.name}")
    # حفظ بيانات المشاريع قيد الإنشاء في ملف منفصل (لا ننسى تحفظها)
    under = df[df["type"] == "under_construction"]
    if not under.empty:
        out_under = OUT_DIR / "google_places_under_construction.csv"
        under.to_csv(out_under, index=False, encoding="utf-8-sig")
        print(f"حفظ {len(under)} مشروع قيد الإنشاء في {out_under.name}")
    print(df["type"].value_counts().to_string())


if __name__ == "__main__":
    main()
