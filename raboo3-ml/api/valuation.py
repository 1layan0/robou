"""Valuation: سعر المتر افتراضي (جداول Transaction/Listing/LandParcel أُزيلت؛ المعتمد aggregate + مودل المجمع)."""
from sqlalchemy.orm import Session

# عند استخدام schema_aggregate لا توجد جداول Transaction/Listing/LandParcel؛ السعر من مودل المجمع أو افتراضي
DEFAULT_PRICE_PER_SQM = 1000.0


def estimate_price_per_sqm(
    db: Session,
    land_use: str,
    area_sqm: float,
) -> float:
    """سعر المتر: قيمة افتراضية (الجداول القديمة استُبدلت بجداول الـ aggregate)."""
    return DEFAULT_PRICE_PER_SQM
