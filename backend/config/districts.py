"""
قوائم الأحياء المرجعية لكل مدينة + التحقق الإلزامي قبل التوليد.

استخدام:
    from config.districts import load_city_districts, run_pre_generation_checks
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

CONFIG_DIR = Path(__file__).resolve().parent
DISTRICTS_JSON = CONFIG_DIR / "city_districts.json"

ALLOWED_CITIES = {"الدمام", "الظهران", "الخبر"}
VALID_PROPERTY_TYPES = {"قطعة أرض-سكنى", "قطعة أرض-تجارى", "شقة", "فيلا"}


def _normalize_name(s: str) -> str:
    """تطبيع اسم الحي للمقارنة: مسافات، همزات."""
    if not s or not isinstance(s, str):
        return ""
    s = " ".join(s.split()).strip()
    s = s.replace("إ", "ا").replace("أ", "ا").replace("آ", "ا")
    return s


def load_city_districts() -> dict[str, list[str]]:
    """تحميل قوائم الأحياء من ملف JSON."""
    if not DISTRICTS_JSON.exists():
        raise FileNotFoundError(f"ملف الأحياء غير موجود: {DISTRICTS_JSON}")
    with open(DISTRICTS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return {str(k): [str(d).strip() for d in v] for k, v in data.items()}


def verify_no_empty_districts(city_districts: dict[str, list[str]]) -> list[str]:
    """التحقق أن كل مدينة لها قائمة أحياء غير فارغة."""
    errors = []
    for city, districts in city_districts.items():
        if not districts:
            errors.append(f"المدينة '{city}' ليس لها أحياء معرّفة.")
        elif all(not d.strip() for d in districts):
            errors.append(f"المدينة '{city}' لها قائمة أحياء فارغة فعلياً.")
    return errors


def verify_no_duplicate_districts(city_districts: dict[str, list[str]]) -> list[str]:
    """التحقق من عدم وجود حي مكرر بكتابات مختلفة داخل نفس المدينة."""
    errors = []
    for city, districts in city_districts.items():
        seen: dict[str, str] = {}
        for d in districts:
            d_str = str(d).strip()
            if not d_str:
                continue
            norm = _normalize_name(d_str)
            if norm in seen:
                errors.append(
                    f"المدينة '{city}': تكرار محتمل "
                    f"('{seen[norm]}' و '{d_str}')"
                )
            else:
                seen[norm] = d_str
    return errors


def run_pre_generation_checks(city_districts: dict[str, list[str]]) -> None:
    """
    تشغيل التحقق الإلزامي قبل التوليد.
    يرفع ValueError إذا فشل أي تحقق.
    """
    err1 = verify_no_empty_districts(city_districts)
    err2 = verify_no_duplicate_districts(city_districts)
    all_errors = err1 + err2
    if all_errors:
        raise ValueError("فشل التحقق قبل التوليد:\n" + "\n".join(all_errors))


def get_valid_pairs(city_districts: dict[str, list[str]]) -> set[tuple[str, str]]:
    """إرجاع مجموعة (مدينة، حي) الصحيحة."""
    pairs = set()
    for city, districts in city_districts.items():
        for d in districts:
            d_str = str(d).strip()
            if d_str:
                pairs.add((city, d_str))
    return pairs


def run_post_generation_checks(
    df: "pd.DataFrame",
    valid_pairs: set[tuple[str, str]],
    *,
    city_col: str = "city_ar",
    district_col: str = "district_ar",
    property_col: str = "property_type_ar",
) -> list[str]:
    """
    التحقق بعد التوليد: كل (مدينة، حي) صحيح ونوع العقار مسموح.
    يرجع قائمة أخطاء (فارغة = نجاح).
    """
    errors = []
    for idx, row in df.iterrows():
        city = str(row.get(city_col, "")).strip()
        district = str(row.get(district_col, "")).strip()
        prop = str(row.get(property_col, "")).strip()

        if (city, district) not in valid_pairs:
            errors.append(
                f"سطر {idx + 1}: زوج غير صحيح '{city}' - '{district}'"
            )
        if prop and prop not in VALID_PROPERTY_TYPES:
            errors.append(
                f"سطر {idx + 1}: نوع عقار غير مسموح '{prop}'"
            )
    return errors
