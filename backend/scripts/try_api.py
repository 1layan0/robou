#!/usr/bin/env python3
"""
تجربة الـ API بنفسك — تشغّل السيرفر أولاً ثم نفّذ هذا السكربت.

الخطوات:
  1. في طرفية:  python run.py
  2. في طرفية ثانية:  python scripts/try_api.py
"""
import sys

try:
    import requests
except ImportError:
    print("يُحتاج تثبيت: pip install requests")
    sys.exit(1)

BASE = "http://127.0.0.1:8000"


def main():
    print("=" * 50)
    print("تجربة ربط الـ API (تأكد أن السيرفر يعمل: python run.py)")
    print("=" * 50)

    # 1) Health
    print("\n1) GET /health")
    try:
        r = requests.get(f"{BASE}/health", timeout=5)
        r.raise_for_status()
        data = r.json()
        print(f"   النتيجة: {data}")
        if data.get("db") == "ok":
            print("   قاعدة البيانات: متصلة ✓")
        else:
            print("   قاعدة البيانات: غير متصلة (التقدير سيستخدم القيمة الافتراضية)")
    except requests.exceptions.ConnectionError:
        print("   خطأ: لا يمكن الاتصال. شغّل السيرفر أولاً: python run.py")
        sys.exit(1)
    except Exception as e:
        print(f"   خطأ: {e}")
        sys.exit(1)

    # استخدم قيماً عربية مطابقة لبيانات التدريب (المدينة، الحي، نوع العقار)
    payload = {
        "city": "الدمام",
        "district": "السيف",
        "area_sqm": 500.0,
        "land_use": "قطعة أرض-سكنى",
    }

    # 2) مودل السعر
    print("\n2) POST /predict — مودل السعر")
    try:
        r = requests.post(f"{BASE}/predict", json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        print(f"   السعر للمتر: {data['price_per_sqm']:,.0f} {data['currency']}/م²")
        print(f"   السعر الإجمالي: {data['total_price']:,.0f} {data['currency']}")
    except requests.exceptions.HTTPError as e:
        print(f"   خطأ: {e.response.status_code} — {r.text[:200]}")
    except Exception as e:
        print(f"   خطأ: {e}")

    # 3) مودل الإيجار
    print("\n3) POST /predict/rent — مودل الإيجار")
    try:
        r = requests.post(f"{BASE}/predict/rent", json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        print(f"   الإيجار الشهري: {data['monthly_rent_sar']:,.0f} {data['currency']}")
    except requests.exceptions.HTTPError as e:
        print(f"   خطأ: {e.response.status_code} — {r.text[:200]}")
    except Exception as e:
        print(f"   خطأ: {e}")

    # 4) مودل النمو
    print("\n4) POST /predict/growth — مودل النمو")
    try:
        r = requests.post(f"{BASE}/predict/growth", json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        print(f"   معدل النمو السنوي: {data['growth_rate_pct']}%")
    except requests.exceptions.HTTPError as e:
        print(f"   خطأ: {e.response.status_code} — {r.text[:200]}")
    except Exception as e:
        print(f"   خطأ: {e}")

    # 5) تقييم الاستثمار
    print("\n5) POST /predict/investment — تقييم الاستثمار")
    try:
        r = requests.post(f"{BASE}/predict/investment", json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        print(f"   السعر للمتر: {data['price_per_sqm']:,.0f} | الإيجار الشهري: {data['monthly_rent_sar']:,.0f}")
        print(f"   النمو السنوي: {data['annual_growth_rate']*100:.2f}% | العائد الإيجاري: {data['rent_yield']*100:.2f}%")
        print(f"   Score: {data['score']} | التوصية: {data['recommendation']}")
    except requests.exceptions.HTTPError as e:
        print(f"   خطأ: {e.response.status_code} — {r.text[:200]}")
    except Exception as e:
        print(f"   خطأ: {e}")

    print("\n" + "=" * 50)
    print("لتجربة من المتصفح: http://localhost:8000/docs")
    print("=" * 50)


if __name__ == "__main__":
    main()
