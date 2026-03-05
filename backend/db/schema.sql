/* =========================================================
   Raboo3 - MySQL Database Schema (Final)
   MySQL 8.0+, InnoDB, utf8mb4
   ========================================================= */

-- 1) Create database
CREATE DATABASE IF NOT EXISTS raboo3
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE raboo3;

-- 2) (Optional) clean re-run: drop tables in safe order
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS Prediction;
DROP TABLE IF EXISTS ParcelImage;
DROP TABLE IF EXISTS ParcelFacilityProximity;
DROP TABLE IF EXISTS Listing;
DROP TABLE IF EXISTS `Transaction`;
DROP TABLE IF EXISTS LandParcel;
DROP TABLE IF EXISTS Facility;
DROP TABLE IF EXISTS DataSource;
DROP TABLE IF EXISTS Zoning;
DROP TABLE IF EXISTS Neighborhood;
DROP TABLE IF EXISTS `User`;
SET FOREIGN_KEY_CHECKS = 1;

-- =========================================================
-- 3) Base tables (no FK dependencies first)
-- =========================================================

-- User (NOTE: `User` is reserved in some DBs, keep backticks)
CREATE TABLE `User` (
  user_id        INT NOT NULL AUTO_INCREMENT,
  name           VARCHAR(100) NOT NULL,
  email          VARCHAR(255) NOT NULL,
  role           VARCHAR(50)  NOT NULL,
  status         ENUM('Active','Inactive') NOT NULL,
  password_hash  VARCHAR(255) NOT NULL,
  PRIMARY KEY (user_id),
  UNIQUE KEY uq_user_email (email)
) ENGINE=InnoDB;

-- Neighborhood
CREATE TABLE Neighborhood (
  neighborhood_id INT NOT NULL AUTO_INCREMENT,
  name            VARCHAR(100) NOT NULL,
  PRIMARY KEY (neighborhood_id),
  UNIQUE KEY uq_neighborhood_name (name)
) ENGINE=InnoDB;

-- Zoning
CREATE TABLE Zoning (
  zoning_id     INT NOT NULL AUTO_INCREMENT,
  code          VARCHAR(50)  NOT NULL,
  description   VARCHAR(255) NOT NULL,
  far           FLOAT NOT NULL,
  max_height    INT NOT NULL,
  setbacks      VARCHAR(100) NULL,
  allowed_uses  VARCHAR(255) NOT NULL,
  PRIMARY KEY (zoning_id),
  UNIQUE KEY uq_zoning_code (code)
) ENGINE=InnoDB;

-- DataSource
CREATE TABLE DataSource (
  source_id  INT NOT NULL AUTO_INCREMENT,
  name       VARCHAR(100) NOT NULL,
  type       VARCHAR(100) NOT NULL,
  url        VARCHAR(255) NULL,
  notes      VARCHAR(255) NULL,
  PRIMARY KEY (source_id),
  UNIQUE KEY uq_datasource_name (name)
) ENGINE=InnoDB;

-- Facility
CREATE TABLE Facility (
  facility_id INT NOT NULL AUTO_INCREMENT,
  type        VARCHAR(100) NOT NULL,
  name        VARCHAR(100) NOT NULL,
  operator    VARCHAR(100) NULL,
  latitude    DECIMAL(10,6) NOT NULL,
  longitude   DECIMAL(10,6) NOT NULL,
  PRIMARY KEY (facility_id),
  KEY idx_facility_lat (latitude),
  KEY idx_facility_lng (longitude)
) ENGINE=InnoDB;

-- =========================================================
-- 4) Dependent tables
-- =========================================================

-- LandParcel
CREATE TABLE LandParcel (
  parcel_id        INT NOT NULL AUTO_INCREMENT,
  cadastre_no      VARCHAR(100) NOT NULL,
  neighborhood_id  INT NOT NULL,
  zoning_id        INT NOT NULL,
  area_sqm         FLOAT NOT NULL,
  land_use         VARCHAR(100) NOT NULL,
  latitude         DECIMAL(10,6) NOT NULL,
  longitude        DECIMAL(10,6) NOT NULL,
  geom_ref         VARCHAR(255) NULL,
  status           VARCHAR(50) NOT NULL,
  created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (parcel_id),
  UNIQUE KEY uq_landparcel_cadastre (cadastre_no),
  KEY idx_landparcel_neighborhood (neighborhood_id),
  KEY idx_landparcel_zoning (zoning_id),
  KEY idx_landparcel_lat (latitude),
  KEY idx_landparcel_lng (longitude),
  CONSTRAINT fk_landparcel_neighborhood
    FOREIGN KEY (neighborhood_id) REFERENCES Neighborhood(neighborhood_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_landparcel_zoning
    FOREIGN KEY (zoning_id) REFERENCES Zoning(zoning_id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Transaction (NOTE: TRANSACTION is a keyword; keep backticks)
CREATE TABLE `Transaction` (
  tx_id            INT NOT NULL AUTO_INCREMENT,
  parcel_id        INT NOT NULL,
  tx_date          DATE NOT NULL,
  price_total_sar  DECIMAL(12,2) NOT NULL,
  price_per_sqm    DECIMAL(12,2) NOT NULL,
  buyer_type       VARCHAR(100) NULL,
  seller_type      VARCHAR(100) NULL,
  source_id        INT NOT NULL,
  record_quality   VARCHAR(50) NULL,
  PRIMARY KEY (tx_id),
  KEY idx_tx_parcel (parcel_id),
  KEY idx_tx_source (source_id),
  KEY idx_tx_date (tx_date),
  CONSTRAINT fk_transaction_parcel
    FOREIGN KEY (parcel_id) REFERENCES LandParcel(parcel_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_transaction_source
    FOREIGN KEY (source_id) REFERENCES DataSource(source_id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Listing
CREATE TABLE Listing (
  listing_id      INT NOT NULL AUTO_INCREMENT,
  parcel_id       INT NOT NULL,
  list_date       DATE NOT NULL,
  list_price_sar  DECIMAL(12,2) NOT NULL,
  status          VARCHAR(50) NOT NULL,
  source_id       INT NOT NULL,
  url             VARCHAR(255) NULL,
  PRIMARY KEY (listing_id),
  KEY idx_listing_parcel (parcel_id),
  KEY idx_listing_source (source_id),
  KEY idx_listing_date (list_date),
  CONSTRAINT fk_listing_parcel
    FOREIGN KEY (parcel_id) REFERENCES LandParcel(parcel_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_listing_source
    FOREIGN KEY (source_id) REFERENCES DataSource(source_id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ParcelImage
CREATE TABLE ParcelImage (
  img_id       INT NOT NULL AUTO_INCREMENT,
  parcel_id    INT NOT NULL,
  captured_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  kind         VARCHAR(100) NOT NULL,
  path_or_url  VARCHAR(255) NOT NULL,
  source_id    INT NOT NULL,
  PRIMARY KEY (img_id),
  KEY idx_parcelimage_parcel (parcel_id),
  KEY idx_parcelimage_source (source_id),
  KEY idx_parcelimage_captured (captured_at),
  CONSTRAINT fk_parcelimage_parcel
    FOREIGN KEY (parcel_id) REFERENCES LandParcel(parcel_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_parcelimage_source
    FOREIGN KEY (source_id) REFERENCES DataSource(source_id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Prediction
CREATE TABLE Prediction (
  prediction_id            INT NOT NULL AUTO_INCREMENT,
  parcel_id                INT NOT NULL,
  prediction_date          DATE NOT NULL,
  predicted_price_per_sqm  DECIMAL(12,2) NOT NULL,
  ci_low                   DECIMAL(12,2) NULL,
  ci_high                  DECIMAL(12,2) NULL,
  features_json            TEXT NULL,
  shap_json                TEXT NULL,
  data_timestamp           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (prediction_id),
  KEY idx_prediction_parcel (parcel_id),
  KEY idx_prediction_date (prediction_date),
  CONSTRAINT fk_prediction_parcel
    FOREIGN KEY (parcel_id) REFERENCES LandParcel(parcel_id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ParcelFacilityProximity (bridge with composite PK)
CREATE TABLE ParcelFacilityProximity (
  parcel_id         INT NOT NULL,
  facility_id       INT NOT NULL,
  distance_m        FLOAT NOT NULL,
  travel_time_min   FLOAT NOT NULL,
  as_of_date        DATE NOT NULL,
  PRIMARY KEY (parcel_id, facility_id, as_of_date),
  KEY idx_pfp_facility (facility_id),
  KEY idx_pfp_asof (as_of_date),
  CONSTRAINT fk_pfp_parcel
    FOREIGN KEY (parcel_id) REFERENCES LandParcel(parcel_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_pfp_facility
    FOREIGN KEY (facility_id) REFERENCES Facility(facility_id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Done
