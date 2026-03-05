"""ORM models matching db/schema.sql. Table/column names aligned with MySQL."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DATE,
    DECIMAL,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TIMESTAMP,
    text,
)
from sqlalchemy.dialects.mysql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# ---------------------------------------------------------------------------
# Base tables (no FK dependencies)
# ---------------------------------------------------------------------------


class User(Base):
    """User table. Table name 'User' (reserved word in MySQL)."""

    __tablename__ = "User"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        ENUM("Active", "Inactive", charset="utf8mb4"), nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)


class Neighborhood(Base):
    __tablename__ = "Neighborhood"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    neighborhood_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    land_parcels: Mapped[list["LandParcel"]] = relationship(
        "LandParcel", back_populates="neighborhood"
    )


class Zoning(Base):
    __tablename__ = "Zoning"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    zoning_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    far: Mapped[float] = mapped_column(Float, nullable=False)
    max_height: Mapped[int] = mapped_column(Integer, nullable=False)
    setbacks: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    allowed_uses: Mapped[str] = mapped_column(String(255), nullable=False)

    land_parcels: Mapped[list["LandParcel"]] = relationship(
        "LandParcel", back_populates="zoning"
    )


class DataSource(Base):
    __tablename__ = "DataSource"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    source_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class Facility(Base):
    __tablename__ = "Facility"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    facility_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    operator: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Decimal] = mapped_column(DECIMAL(10, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(DECIMAL(10, 6), nullable=False)


# ---------------------------------------------------------------------------
# Dependent tables
# ---------------------------------------------------------------------------


class LandParcel(Base):
    __tablename__ = "LandParcel"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    parcel_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    cadastre_no: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    neighborhood_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("Neighborhood.neighborhood_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    zoning_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("Zoning.zoning_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    area_sqm: Mapped[float] = mapped_column(Float, nullable=False)
    land_use: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(DECIMAL(10, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(DECIMAL(10, 6), nullable=False)
    geom_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    neighborhood: Mapped["Neighborhood"] = relationship(
        "Neighborhood", back_populates="land_parcels"
    )
    zoning: Mapped["Zoning"] = relationship(
        "Zoning", back_populates="land_parcels"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="parcel"
    )
    listings: Mapped[list["Listing"]] = relationship(
        "Listing", back_populates="parcel"
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        "Prediction", back_populates="parcel"
    )


class Transaction(Base):
    """Transaction table. Table name 'Transaction' (reserved word)."""

    __tablename__ = "Transaction"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    tx_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    parcel_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("LandParcel.parcel_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    tx_date: Mapped[date] = mapped_column(DATE, nullable=False)
    price_total_sar: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    price_per_sqm: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    buyer_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    seller_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("DataSource.source_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    record_quality: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    parcel: Mapped["LandParcel"] = relationship(
        "LandParcel", back_populates="transactions"
    )


class Listing(Base):
    __tablename__ = "Listing"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    listing_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    parcel_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("LandParcel.parcel_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    list_date: Mapped[date] = mapped_column(DATE, nullable=False)
    list_price_sar: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("DataSource.source_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    parcel: Mapped["LandParcel"] = relationship(
        "LandParcel", back_populates="listings"
    )


class ParcelImage(Base):
    __tablename__ = "ParcelImage"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    img_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    parcel_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("LandParcel.parcel_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    captured_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    kind: Mapped[str] = mapped_column(String(100), nullable=False)
    path_or_url: Mapped[str] = mapped_column(String(255), nullable=False)
    source_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("DataSource.source_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )


class Prediction(Base):
    __tablename__ = "Prediction"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    prediction_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    parcel_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("LandParcel.parcel_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    prediction_date: Mapped[date] = mapped_column(DATE, nullable=False)
    predicted_price_per_sqm: Mapped[Decimal] = mapped_column(
        DECIMAL(12, 2), nullable=False
    )
    ci_low: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 2), nullable=True)
    ci_high: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 2), nullable=True)
    features_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    shap_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data_timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    parcel: Mapped["LandParcel"] = relationship(
        "LandParcel", back_populates="predictions"
    )


class ParcelFacilityProximity(Base):
    __tablename__ = "ParcelFacilityProximity"
    __table_args__ = (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    parcel_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("LandParcel.parcel_id", onupdate="CASCADE", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    )
    facility_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("Facility.facility_id", onupdate="CASCADE", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    )
    as_of_date: Mapped[date] = mapped_column(DATE, primary_key=True, nullable=False)
    distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    travel_time_min: Mapped[float] = mapped_column(Float, nullable=False)
