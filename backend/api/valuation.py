"""Valuation logic: derive price_per_sqm from DB (transactions/listings) or fallback."""
from decimal import Decimal
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import LandParcel, Listing, Transaction


def _median_price_per_sqm_from_transactions(
    db: Session,
    land_use: str,
    area_sqm: float,
    area_tolerance: float = 0.5,
) -> float | None:
    """Median price_per_sqm from Transaction + LandParcel for same land_use and similar area."""
    area_lo = area_sqm * (1 - area_tolerance)
    area_hi = area_sqm * (1 + area_tolerance)
    stmt = (
        select(Transaction.price_per_sqm)
        .join(LandParcel, Transaction.parcel_id == LandParcel.parcel_id)
        .where(
            LandParcel.land_use == land_use,
            LandParcel.area_sqm >= area_lo,
            LandParcel.area_sqm <= area_hi,
        )
    )
    rows = db.execute(stmt).scalars().all()
    if not rows:
        return None
    values = [float(r) for r in rows]
    return median(values)


def _median_price_per_sqm_from_listings(
    db: Session,
    land_use: str,
    area_sqm: float,
    area_tolerance: float = 0.5,
) -> float | None:
    """Median (list_price_sar / area_sqm) from Listing + LandParcel for same land_use and similar area."""
    area_lo = area_sqm * (1 - area_tolerance)
    area_hi = area_sqm * (1 + area_tolerance)
    stmt = (
        select(Listing.list_price_sar, LandParcel.area_sqm)
        .join(LandParcel, Listing.parcel_id == LandParcel.parcel_id)
        .where(
            LandParcel.land_use == land_use,
            LandParcel.area_sqm >= area_lo,
            LandParcel.area_sqm <= area_hi,
        )
    )
    rows = db.execute(stmt).all()
    if not rows:
        return None
    values = []
    for list_price, area in rows:
        if area and float(area) > 0:
            values.append(float(list_price) / float(area))
    if not values:
        return None
    return median(values)


# Default when no DB data (SAR/sqm)
DEFAULT_PRICE_PER_SQM = 1000.0


def estimate_price_per_sqm(
    db: Session,
    land_use: str,
    area_sqm: float,
) -> float:
    """
    Estimate price per sqm from DB: transactions first, then listings, else default.
    """
    price = _median_price_per_sqm_from_transactions(db, land_use, area_sqm)
    if price is not None:
        return price
    price = _median_price_per_sqm_from_listings(db, land_use, area_sqm)
    if price is not None:
        return price
    return DEFAULT_PRICE_PER_SQM
