"""اختبار سريع لـ POST /recommend/districts.

تشغيل بدون خادم (TestClient):
  python scripts/test_recommend_districts.py

أو مع خادم فعلي (اختياري):
  uv run uvicorn api.main:app --reload
  python scripts/test_recommend_districts.py --live
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def _client_live():
    import requests
    return lambda method, path, **kw: getattr(requests, method)(f"http://127.0.0.1:8000{path}", **kw)


def _client_test():
    from fastapi.testclient import TestClient
    from api.main import app
    c = TestClient(app)
    return lambda method, path, **kw: c.request(method, path, **kw)


def test_small_radius(request_fn):
    """نطاق صغير: mode فقط (الباك يستخدم أحدث ربع تلقائياً)."""
    r = request_fn("post", "/recommend/districts", json={
        "center_lat": 26.43,
        "center_lon": 50.09,
        "radius_km": 2.0,
        "city_ar": "الدمام",
        "property_type_ar": "قطعة أرض-سكنى",
        "top_k": 3,
        "mode": "value",
    })
    assert r.status_code == 200, r.text if hasattr(r, "text") else r.json()
    data = r.json()
    assert "count_in_radius" in data and "results" in data
    assert "mode_used" in data and "used_weights" in data
    assert "latest_year" in data and "latest_quarter" in data
    assert isinstance(data["latest_year"], int) and isinstance(data["latest_quarter"], int)
    if data["results"]:
        for res in data["results"]:
            assert res.get("confidence") in ("high", "medium", "low"), "confidence must be high/medium/low"
            assert res.get("services_level") in ("high", "medium", "low")
            assert res.get("growth_trend") in ("up", "flat", "down")
            assert isinstance(res.get("reasons_ar"), list)
    print("test_small_radius OK:", "count_in_radius =", data["count_in_radius"], "results =", len(data["results"]))


def test_large_radius(request_fn):
    """نطاق كبير: mode=premium (الباك يستخدم أحدث ربع تلقائياً)."""
    r = request_fn("post", "/recommend/districts", json={
        "center_lat": 26.42,
        "center_lon": 50.10,
        "radius_km": 15.0,
        "city_ar": None,
        "property_type_ar": "قطعة أرض-تجارى",
        "top_k": 5,
        "mode": "premium",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["count_in_radius"] >= 0
    assert data.get("mode_used") == "premium"
    assert "latest_year" in data and "latest_quarter" in data
    print("test_large_radius OK:", "count_in_radius =", data["count_in_radius"], "top_k =", data["top_k"])


def test_zero_radius(request_fn):
    """نطاق بعيد: 0 أحياء."""
    r = request_fn("post", "/recommend/districts", json={
        "center_lat": 24.0,
        "center_lon": 45.0,
        "radius_km": 5.0,
        "city_ar": None,
        "property_type_ar": "قطعة أرض-سكنى",
        "top_k": 3,
        "mode": "value",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["count_in_radius"] == 0 and len(data["results"]) == 0
    assert "latest_year" in data and "latest_quarter" in data
    print("test_zero_radius OK: لا أحياء ضمن النطاق")


def test_budget_filter(request_fn):
    """min/max يقلل النتائج أو يفرغها."""
    r = request_fn("post", "/recommend/districts", json={
        "center_lat": 26.43,
        "center_lon": 50.09,
        "radius_km": 12.0,
        "city_ar": None,
        "property_type_ar": "قطعة أرض-سكنى",
        "top_k": 5,
        "mode": "value",
        "min_price_per_sqm": 500,
        "max_price_per_sqm": 8000,
    })
    assert r.status_code == 200
    data = r.json()
    for res in data.get("results", []):
        assert res["predicted_median_price_per_sqm"] >= 500
        assert res["predicted_median_price_per_sqm"] <= 8000
    print("test_budget_filter OK")


def test_mode_changes_order(request_fn):
    """تغيير mode يغير ترتيب Top3 (أو على الأقل used_weights)."""
    r_value = request_fn("post", "/recommend/districts", json={
        "center_lat": 26.43,
        "center_lon": 50.09,
        "radius_km": 8.0,
        "city_ar": "الدمام",
        "property_type_ar": "قطعة أرض-سكنى",
        "top_k": 3,
        "mode": "value",
    })
    r_growth = request_fn("post", "/recommend/districts", json={
        "center_lat": 26.43,
        "center_lon": 50.09,
        "radius_km": 8.0,
        "city_ar": "الدمام",
        "property_type_ar": "قطعة أرض-سكنى",
        "top_k": 3,
        "mode": "growth",
    })
    assert r_value.status_code == 200 and r_growth.status_code == 200
    d1, d2 = r_value.json(), r_growth.json()
    assert d1.get("mode_used") == "value" and d2.get("mode_used") == "growth"
    w1, w2 = d1.get("used_weights", {}), d2.get("used_weights", {})
    assert w1.get("price", 0) > w2.get("price", 0) and w2.get("growth", 0) > w1.get("growth", 0)
    print("test_mode_changes_order OK")


def test_weights(request_fn):
    """أوزان مخصصة + وجود confidence/reasons_ar."""
    r = request_fn("post", "/recommend/districts", json={
        "center_lat": 26.43,
        "center_lon": 50.09,
        "radius_km": 10.0,
        "city_ar": "الخبر",
        "property_type_ar": "قطعة أرض-سكنى",
        "top_k": 3,
        "mode": "value",
        "weights": {"price": 0.6, "growth": 0.2, "services": 0.2},
    })
    assert r.status_code == 200
    data = r.json()
    if data["results"]:
        res = data["results"][0]
        assert "score" in res and "reasons_ar" in res
        assert res.get("confidence") in ("high", "medium", "low")
        assert "confidence_reason" in res
    print("test_weights OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Use live server (default: TestClient)")
    args = parser.parse_args()
    request_fn = _client_live() if args.live else _client_test()
    if args.live:
        print("Testing against live server http://127.0.0.1:8000 ...")
    else:
        print("Testing POST /recommend/districts (TestClient)...")
    test_small_radius(request_fn)
    test_large_radius(request_fn)
    test_zero_radius(request_fn)
    test_budget_filter(request_fn)
    test_mode_changes_order(request_fn)
    test_weights(request_fn)
    print("All quick tests passed.")
