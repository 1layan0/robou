#!/usr/bin/env python3
"""
تحميل البيانات الحقيقية إلى MySQL: Facility من osm_services.csv، وبيانات العقار من real_sales.
التركيز: الدمام، الظهران، الخبر فقط.

يشغّل بعد: docker compose up -d، تطبيق db/schema.sql

الاستخدام: python scripts/load_real_data_to_mysql.py
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OSM_SERVICES_CSV = PROJECT_ROOT / "data" / "raw" / "osm_services.csv"
REAL_SALES_CSV = PROJECT_ROOT / "data" / "real" / "real_sales_merged.csv"
SQL_OUT = PROJECT_ROOT / "db" / "loaded_real.sql"

# المدن المدعومة فقط
ALLOWED_CITIES = {"الدمام", "الظهران", "الخبر"}

# إحداثيات تقريبية لمراكز المدن (lat, lon)
CITY_CENTROIDS = {
    "الدمام": (26.42, 50.11),
    "الظهران": (26.29, 50.11),
    "الخبر": (26.22, 50.21),
}


def escape_sql(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "NULL"
    if isinstance(v, str):
        s = str(v).replace("\\", "\\\\").replace("'", "''")[:255]
        return f"'{s}'"
    if pd.isna(v):
        return "NULL"
    if hasattr(v, "strftime"):
        return f"'{str(v)[:10]}'"
    if isinstance(v, (int, float)):
        return str(v)
    return f"'{str(v)}'"


def tq(name: str) -> str:
    return f"`{name}`" if name in ("User", "Transaction") else f"`{name}`"


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", "-n", type=int, default=0, help="حد أقصى لصفقات التحميل (0=الكل)")
    args = ap.parse_args()
    lines = [
        "USE raboo3;",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
        "-- تفريغ الجداول قبل التحميل",
        "TRUNCATE TABLE ParcelFacilityProximity;",
        "TRUNCATE TABLE `Transaction`;",
        "TRUNCATE TABLE LandParcel;",
        "TRUNCATE TABLE Facility;",
        "TRUNCATE TABLE Neighborhood;",
        "TRUNCATE TABLE Zoning;",
        "",
    ]

    # 1) DataSource
    lines.append("-- DataSource")
    lines.append("INSERT IGNORE INTO DataSource (name, type, url, notes) VALUES")
    lines.append("  ('OpenStreetMap', 'OSM', 'https://www.openstreetmap.org', 'ODbL'),")
    lines.append("  ('هيئة العقار', 'Rega', 'https://rega.gov.sa', 'مؤشرات عقارية');")
    lines.append("")

    # 2) Facility من osm_services.csv
    if not OSM_SERVICES_CSV.exists():
        print(f"تحذير: {OSM_SERVICES_CSV} غير موجود.")
    else:
        df = pd.read_csv(OSM_SERVICES_CSV, encoding="utf-8-sig")
        df = df[df["latitude"].notna() & df["longitude"].notna()]
        lines.append("-- Facility (OSM services)")
        lines.append("INSERT INTO Facility (type, name, operator, latitude, longitude) VALUES")
        rows = []
        for _, r in df.iterrows():
            t = str(r.get("type", ""))[:100]
            n = str(r.get("name", ""))[:100] or t
            op = r.get("operator")
            op = "" if pd.isna(op) else str(op)[:100]
            lat = float(r["latitude"])
            lon = float(r["longitude"])
            rows.append(f"  ({escape_sql(t)}, {escape_sql(n)}, {escape_sql(op) or 'NULL'}, {lat:.6f}, {lon:.6f})")
        lines.append(",\n".join(rows))
        lines.append(";")
        lines.append("")
        print(f"Facility: {len(rows)} سجل")

    # 3) Neighborhood, Zoning, LandParcel, Transaction من real_sales
    sales_path = REAL_SALES_CSV
    if not sales_path.exists():
        print(f"تحذير: {sales_path} غير موجود. شغّل merge_real_estate_data.py أولاً.")
    else:
        sales = pd.read_csv(sales_path, encoding="utf-8-sig")
        sales["city_ar"] = sales.get("city_ar", pd.Series(dtype=object)).fillna("").astype(str).str.strip()
        sales["district_ar"] = sales.get("district_ar", pd.Series(dtype=object)).fillna("").astype(str).str.strip().replace("nan", "")
        sales["type_category_ar"] = sales.get("property_type_ar", sales.get("type_category_ar", pd.Series(dtype=object))).fillna("").astype(str).str.strip()
        sales["price_per_sqm"] = pd.to_numeric(sales.get("price_per_sqm"), errors="coerce")
        sales = sales[sales["city_ar"].str.len() > 0]

        # فلترة: الدمام، الظهران، الخبر فقط
        sales = sales[sales["city_ar"].isin(ALLOWED_CITIES)].copy()
        if len(sales) == 0:
            print("تحذير: لا توجد بيانات للدمام/الظهران/الخبر في الملف.")
        else:
            print(f"بعد الفلترة (الدمام+الظهران+الخبر): {len(sales)} صف")

        # Neighborhood: فريد (مدينة - حي)
        neigh_map = {}
        for _, r in sales.iterrows():
            city = r["city_ar"]
            dist = r["district_ar"] if r["district_ar"] else "غير محدد"
            key = f"{city}|{dist}"
            if key not in neigh_map:
                neigh_map[key] = (city, dist)

        lines.append("-- Neighborhood")
        for i, (key, (city, dist)) in enumerate(neigh_map.items(), 1):
            name = f"{city} - {dist}" if dist != "غير محدد" else city
            lines.append(f"INSERT IGNORE INTO Neighborhood (neighborhood_id, name) VALUES ({i}, {escape_sql(name)});")
        lines.append("")

        # Zoning
        zoning_map = {"قطعة أرض-سكنى": ("R1", "سكني", 1), "قطعة أرض-تجارى": ("C1", "تجاري", 2), "قطعة أرض-زراعي": ("A1", "زراعي", 3)}
        lines.append("-- Zoning")
        for code, desc, zid in zoning_map.values():
            lines.append(f"INSERT IGNORE INTO Zoning (zoning_id, code, description, far, max_height, allowed_uses) VALUES ({zid}, '{code}', '{desc}', 1.0, 12, '{desc}');")
        lines.append("")

        # LandParcel: واحد لكل (مدينة، حي، نوع)
        parcel_map = {}  # (city, dist, type) -> parcel_id
        pid = 1
        for key, (city, dist) in neigh_map.items():
            for cat in ("قطعة أرض-سكنى", "قطعة أرض-تجارى", "قطعة أرض-زراعي"):
                dist_ok = (sales["district_ar"].fillna("").str.strip() == "") if dist == "غير محدد" else (sales["district_ar"].fillna("") == dist)
                subset = sales[(sales["city_ar"] == city) & dist_ok & (sales["type_category_ar"] == cat)]
                if len(subset) == 0:
                    continue
                pkey = (city, dist or "غير محدد", cat)
                if pkey in parcel_map:
                    continue
                parcel_map[pkey] = pid
                cadastre = f"REAL-{city[:20]}-{dist[:20] if dist else 'X'}-{cat[:10]}"[:100]
                neigh_id = list(neigh_map.keys()).index(f"{city}|{dist}") + 1
                zid = 1 if "سكنى" in cat else (2 if "تجارى" in cat else 3)
                lat, lon = CITY_CENTROIDS.get(city, (26.42, 50.11))
                land_use = "Residential" if "سكنى" in cat else ("Commercial" if "تجارى" in cat else "Agricultural")
                lines.append(f"INSERT IGNORE INTO LandParcel (parcel_id, cadastre_no, neighborhood_id, zoning_id, area_sqm, land_use, latitude, longitude, status) VALUES ({pid}, {escape_sql(cadastre)}, {neigh_id}, {zid}, 500, {escape_sql(land_use)}, {lat:.6f}, {lon:.6f}, 'Active');")
                pid += 1

        lines.append("")
        print(f"LandParcel: {len(parcel_map)} سجل")

        # Transaction: صفوف ذات price_per_sqm صالح
        tx_rows = sales[sales["price_per_sqm"].notna() & (sales["price_per_sqm"] > 0)]
        if args.limit > 0:
            tx_rows = tx_rows.head(args.limit)
        # نحتاج source_id لهيئة العقار
        lines.append("-- Transaction (source_id=2 لهيئة العقار)")
        for _, r in tx_rows.iterrows():
            city = r["city_ar"]
            dist = r["district_ar"] if pd.notna(r["district_ar"]) and str(r["district_ar"]) != "nan" else ""
            cat = r["type_category_ar"]
            pkey = (city, dist or "غير محدد", cat)
            parcel_id = parcel_map.get(pkey)
            if parcel_id is None:
                continue
            dt = r.get("tx_date")
            if pd.notna(dt) and str(dt) and "/" in str(dt):
                try:
                    parts = str(dt).split("/")
                    tx_date = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"[:10]
                except (IndexError, ValueError):
                    year = int(r.get("year", 2023))
                    qnum = int(r.get("quarter", 1)) if pd.notna(r.get("quarter")) else 1
                    tx_date = f"{year}-{min(qnum*3,12):02d}-01"
            else:
                year = int(r.get("year", 2023))
                q = r.get("quarter", 1)
                if isinstance(q, str) and "الربع" in str(q):
                    qnum = 1
                    if "الثانى" in str(q) or "الثاني" in str(q): qnum = 2
                    elif "الثالث" in str(q): qnum = 3
                    elif "الرابع" in str(q): qnum = 4
                else:
                    qnum = int(q) if pd.notna(q) else 1
                tx_date = f"{year}-{min(qnum*3,12):02d}-01"
            ppq = float(r["price_per_sqm"])
            area_val = pd.to_numeric(r.get("area_sqm"), errors="coerce")
            total = float(r.get("price_total", ppq * 500)) if pd.notna(r.get("price_total")) else (ppq * (area_val if pd.notna(area_val) and area_val > 0 else 500))
            lines.append(f"INSERT INTO `Transaction` (parcel_id, tx_date, price_total_sar, price_per_sqm, source_id) VALUES ({parcel_id}, '{tx_date}', {total:.2f}, {ppq:.2f}, 2);")

        print(f"Transaction: {len([l for l in lines if 'INSERT INTO `Transaction`' in l])} سجل")

    lines.append("")
    lines.append("SET FOREIGN_KEY_CHECKS = 1;")

    SQL_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(SQL_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"تم توليد: {SQL_OUT}")
    print("جاري التحميل إلى MySQL...")

    with open(SQL_OUT, "r", encoding="utf-8") as f:
        result = subprocess.run(
            ["docker", "exec", "-i", "raboo3-ml-mysql", "mysql", "-u", "root", "-praboo3_root", "raboo3"],
            stdin=f,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

    if result.returncode != 0:
        print("خطأ MySQL:", result.stderr or result.stdout)
        return
    print("تم. البيانات الحقيقية في MySQL (raboo3).")


if __name__ == "__main__":
    main()
