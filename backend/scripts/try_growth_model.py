"""تجربة مودل النمو من الطرفية: استدعاء المودل بعدة طلبات نموذجية وطباعة النتائج.

تشغيل من جذر المشروع:
    python scripts/try_growth_model.py

يحتاج artifacts/growth_model.pkl و artifacts/growth_model_metadata.json (بعد تشغيل train_growth_model).
"""
from __future__ import annotations

import sys
from pathlib import Path

# إضافة جذر المشروع لـ import
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schemas.predict import PredictRequest
from models.growth_model import predict_annual_growth_rate_from_request, GrowthModelNotAvailableError


def main() -> None:
    samples = [
        PredictRequest(city="الدمام", district="السيف", area_sqm=500, land_use="قطعة أرض-سكنى"),
        PredictRequest(city="الخبر", district="الحزام الذهبي", area_sqm=400, land_use="قطعة أرض-سكنى"),
        PredictRequest(city="الظهران", district="أجيال", area_sqm=600, land_use="فيلا"),
    ]
    print("مودل النمو — تجربة استدعاء")
    print("-" * 50)
    try:
        for req in samples:
            rate = predict_annual_growth_rate_from_request(req)
            print(f"  {req.city} / {req.district} / {req.land_use}  →  معدل النمو السنوي: {rate:.2%}")
        print("-" * 50)
        print("تم بنجاح.")
    except GrowthModelNotAvailableError as e:
        print(f"خطأ: المودل غير متوفر. {e}")
        print("شغّلي أولاً: python -m scripts.train_growth_model")
        sys.exit(1)
    except Exception as e:
        print(f"خطأ: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
