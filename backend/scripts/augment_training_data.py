#!/usr/bin/env python3
"""
تكميل بيانات التدريب للأحياء الجديدة التي لا تحتوي صفقات حقيقية.

يولّد صفوفاً صناعية مستندة إلى توزيع الأسعار والمساحات من أحياء نفس المدينة
(مثلاً: الظهران - السلمانية من توزيع الظهران - الدوحة الجنوبية، شمال الظهران، إلخ).

الاستخدام:
    python scripts/augment_training_data.py

الإخراج: data/real/real_sales_augmented.csv (حقيقي + مكمّل)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REAL_PATH = PROJECT_ROOT / "data" / "real" / "real_sales_merged.csv"
CONFIG_PATH = PROJECT_ROOT / "config" / "city_districts.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "real" / "real_sales_augmented.csv"

# عدد الصفوف المولّدة لكل (مدينة، حي) جديد ونوع عقار
ROWS_PER_DISTRICT_PROPERTY = 25

VALID_PROPERTY_TYPES = ["قطعة أرض-سكنى", "قطعة أرض-تجارى", "شقة", "فيلا"]
REGION_AR = "الشرقية"
SOURCE_AUGMENT = "augment"


def load_config_pairs() -> set[tuple[str, str]]:
    """تحميل أزواج (مدينة، حي) من المرجع."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    pairs = set()
    for city, districts in cfg.items():
        for d in districts:
            if str(d).strip():
                pairs.add((city, str(d).strip()))
    return pairs


def get_districts_without_data(real_df: pd.DataFrame) -> set[tuple[str, str]]:
    """إرجاع أحياء في المرجع بدون بيانات حقيقية (أو بيانات قليلة جداً)."""
    config_pairs = load_config_pairs()
    real_df = real_df[
        real_df["price_per_sqm"].notna()
        & (real_df["price_per_sqm"] > 0)
        & real_df["area_sqm"].notna()
        & (real_df["area_sqm"] > 0)
    ]
    real_df["district_ar"] = real_df["district_ar"].fillna("").astype(str).str.strip().replace("nan", "")
    real_pairs_counts = real_df.groupby(["city_ar", "district_ar"]).size()
    # أحياء إما غير موجودة أو لديها أقل من 3 صفوف
    missing = set()
    for (city, district) in config_pairs:
        count = real_pairs_counts.get((city, district), 0)
        if count < 3:
            missing.add((city, district))
    return missing


def generate_augment_rows(
    real_df: pd.DataFrame,
    missing_pairs: set[tuple[str, str]],
    rows_per: int,
    seed: int = 42,
) -> pd.DataFrame:
    """توليد صفوف تكميلية مستندة إلى توزيع نفس المدينة."""
    rng = np.random.default_rng(seed)
    real_df = real_df[
        real_df["price_per_sqm"].notna()
        & (real_df["price_per_sqm"] > 0)
        & real_df["area_sqm"].notna()
        & (real_df["area_sqm"] > 0)
    ].copy()
    real_df["district_ar"] = real_df["district_ar"].fillna("").astype(str).str.strip().replace("nan", "")

    rows = []
    for city, district in sorted(missing_pairs):
        # مرجع: نفس المدينة + أي حي (لدينا بياناته)
        ref = real_df[real_df["city_ar"] == city]
        if len(ref) == 0:
            # إذا لم تكن هناك بيانات للمدينة، استخدم الكل
            ref = real_df

        for prop in VALID_PROPERTY_TYPES:
            ref_prop = ref[ref["property_type_ar"] == prop]
            if len(ref_prop) < 5:
                ref_prop = ref

            if len(ref_prop) == 0:
                continue

            ppsqm = ref_prop["price_per_sqm"].values
            area = ref_prop["area_sqm"].values

            for _ in range(rows_per):
                p = float(rng.choice(ppsqm))
                a = float(np.clip(rng.choice(area), 80, 5000))
                total = round(p * a, 2)
                rows.append({
                    "year": int(ref_prop["year"].mode().iloc[0]) if len(ref_prop) else 2024,
                    "quarter": int(rng.choice([1, 2, 3, 4])),
                    "region_ar": REGION_AR,
                    "city_ar": city,
                    "district_ar": district,
                    "property_type_ar": prop,
                    "deed_count": 1,
                    "price_total": total,
                    "area_sqm": round(a, 2),
                    "price_per_sqm": round(p, 2),
                    "source": SOURCE_AUGMENT,
                    "tx_reference": "",
                })

    return pd.DataFrame(rows)


def main() -> int:
    if not REAL_PATH.exists():
        print(f"خطأ: الملف غير موجود {REAL_PATH}")
        return 1

    real_df = pd.read_csv(REAL_PATH, encoding="utf-8-sig")
    missing = get_districts_without_data(real_df)

    if not missing:
        print("لا توجد أحياء تحتاج تكميلاً. النسخة المدمجة = النسخة الأصلية.")
        real_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
        print(f"تم نسخ {OUTPUT_PATH}")
        return 0

    print(f"عدد الأحياء التي تحتاج تكميلاً: {len(missing)}")
    for city, district in sorted(missing):
        print(f"  {city} - {district}")

    augment_df = generate_augment_rows(real_df, missing, ROWS_PER_DISTRICT_PROPERTY)
    print(f"\nتم توليد {len(augment_df):,} صف تكميلي")

    combined = pd.concat([real_df, augment_df], ignore_index=True)
    combined.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"تم حفظ النسخة المدمجة: {OUTPUT_PATH} ({len(combined):,} صف)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
