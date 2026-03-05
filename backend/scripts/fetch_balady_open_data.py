#!/usr/bin/env python3
"""
جمع بيانات حقيقية من منصة البلديات (Momrah) - البيانات المفتوحة.
API: https://apiservices.balady.gov.sa/v1/momrah-services/open-data

يستخرج الأخبار/المحتوى ويحفظه في data/raw/ للاستخدام أو التحليل لاحقاً.
تشغيل: python scripts/fetch_balady_open_data.py
"""
from __future__ import annotations

import re
from pathlib import Path

import requests

BASE_URL = "https://apiservices.balady.gov.sa/v1/momrah-services/open-data"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "data" / "raw"
OUT_JSON = OUT_DIR / "balady_open_data.json"
OUT_CSV = OUT_DIR / "balady_open_data.csv"


def _first_value(obj, key: str, default=None):
    """استخراج القيمة من الحقل بصيغة [{"value": ...}]"""
    if not isinstance(obj, dict):
        return default
    arr = obj.get(key)
    if not isinstance(arr, list) or not arr:
        return default
    first = arr[0]
    if isinstance(first, dict) and "value" in first:
        return first["value"]
    return first


def _strip_html(text: str, max_len: int = 300) -> str:
    """إزالة وسوم HTML واختصار النص."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:max_len] if len(clean) > max_len else clean


def fetch_and_save() -> int:
    """جلب البيانات من API وحفظها. يعيد عدد السجلات المستخرجة."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        r = requests.get(BASE_URL, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"خطأ في الاتصال: {e}")
        return 0

    # المسار: data.result.rows
    result = data.get("data", {}).get("result", {})
    rows = result.get("rows")
    if not rows:
        print("لا توجد صفوف في الاستجابة.")
        # حفظ الاستجابة الخام لأي تحليل لاحق
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            import json
            json.dump(data, f, ensure_ascii=False, indent=2)
        return 0

    records = []
    for row in rows:
        title = _first_value(row, "title", "")
        if isinstance(title, list):
            title = title[0].get("value", "") if title else ""
        created = _first_value(row, "created", "")
        field_date = _first_value(row, "field_date", "")
        date_str = field_date or (str(created)[:10] if created else "")
        body_raw = _first_value(row, "body", "")
        body_preview = _strip_html(str(body_raw)) if body_raw else ""
        nid = _first_value(row, "nid", "")

        records.append({
            "id": nid,
            "title": title,
            "date": date_str,
            "body_preview": body_preview,
            "source": "apiservices.balady.gov.sa",
        })

    # حفظ JSON كامل
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        import json
        json.dump({"source": BASE_URL, "count": len(records), "rows": records}, f, ensure_ascii=False, indent=2)

    # حفظ CSV للقراءة السهلة
    import pandas as pd
    df = pd.DataFrame(records)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    print(f"تم جلب {len(records)} سجل من البلديات. حفظ: {OUT_JSON.name}, {OUT_CSV.name}")
    return len(records)


if __name__ == "__main__":
    fetch_and_save()
