#!/usr/bin/env python3
"""
مثال استدعاء API عقارسس (صفقات وإحصائيات).
المصدر: https://www.digitalocean.com/community/tutorials/how-to-use-web-apis-in-python-3

الاستخدام:
  export AQARSAS_API_KEY=your_api_key
  python backend/scripts/aqarsas_api_example.py

أو من مجلد backend:
  export AQARSAS_API_KEY=your_api_key
  python scripts/aqarsas_api_example.py
"""

import json
import os
import requests

API_KEY = os.environ.get("AQARSAS_API_KEY", "your_api_key")
DEALS_URL = "https://api.aqarsas.sa/deals/"
STATS_URL = "https://api.aqarsas.sa/stats/"
HEADERS = {"Content-Type": "application/json"}


def main():
    if API_KEY == "your_api_key":
        print("تحذير: ضع مفتاح API في المتغير AQARSAS_API_KEY")
        print("مثال: export AQARSAS_API_KEY=your_actual_key")
        print()

    # --- استدعاء /stats/ ---
    stats_req = {
        "key": API_KEY,
        "stat_type": "number_of_deals",
        "calendar": "gregorian",
        "start_date": "2016-01-01",
        "end_date": "2016-01-31",
        "state": 0,
        "city": "الرياض",
    }
    print("استدعاء /stats/ (عدد الصفقات - الرياض):")
    try:
        r = requests.post(STATS_URL, headers=HEADERS, json=stats_req, timeout=30)
        result = r.json()
        for k, v in result.items():
            print(" ", k, v)
    except Exception as e:
        print(" خطأ:", e)
    print()

    # --- استدعاء /deals/ ---
    # state: 0=الرياض, 4=المنطقة الشرقية
    deals_req = {
        "key": API_KEY,
        "calendar": "hijri",
        "start_date": "1439-05-01",
        "end_date": "1439-05-30",
        "category": "سكني",
        "dtype": "قطعة أرض",
        "state": 0,
        "city": "الرياض",
        "min_meter_price": 1000,
        "max_meter_price": 1200,
        "min_area": 100,
        "max_area": 5000,
        "hai": "القادسيه",
        "hai_exact_match": 0,
    }
    print("استدعاء /deals/ (صفقات - الرياض، قطعة أرض سكني):")
    try:
        r = requests.post(DEALS_URL, headers=HEADERS, json=deals_req, timeout=30)
        result = r.json()
        for k, v in result.items():
            if k == "Deals_list" and isinstance(v, list):
                print(" ", k, f"({len(v)} عنصر)")
                for i, deal in enumerate(v[:3]):
                    print("    [{}] {}".format(i + 1, deal))
                if len(v) > 3:
                    print("    ...")
            else:
                print(" ", k, v)
    except Exception as e:
        print(" خطأ:", e)


if __name__ == "__main__":
    main()
