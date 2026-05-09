/* =========================================================
   قاعدة البيانات لمودل السعر المجمع فقط (5 جداول بيانات)
   المصادقة والمفضلة في Supabase؛ MySQL للبيانات فقط (District، RealSale، إلخ).
   يحذف الجداول القديمة (User, Users, UserSessions, Favorites, ...) وينشئ الجداول الخمسة فقط.
   تشغيل: بعد docker compose up -d
   docker exec -i raboo3-ml-mysql mysql -u root -praboo3_root < db/schema_aggregate.sql
   ========================================================= */

CREATE DATABASE IF NOT EXISTS raboo3
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE raboo3;
SET NAMES utf8mb4;

-- حذف الجداول القديمة أولاً
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
-- جداول المستخدمين الجديدة (لو كانت موجودة) لإعادة إنشائها من جديد
DROP TABLE IF EXISTS UserSessions;
DROP TABLE IF EXISTS Favorites;
DROP TABLE IF EXISTS Users;
-- حذف جداول المودل المجمع إن وُجدت (لإعادة البناء)
DROP TABLE IF EXISTS RealSale;
DROP TABLE IF EXISTS DistrictQuarterAggregate;
DROP TABLE IF EXISTS DistrictGrowthYoy;
DROP TABLE IF EXISTS AggregatedPriceModelVersion;
DROP TABLE IF EXISTS District;
SET FOREIGN_KEY_CHECKS = 1;

-- =========================================================
-- 1) District — أحياء معتمدة + إحداثيات
-- =========================================================
CREATE TABLE District (
    district_id    INT NOT NULL AUTO_INCREMENT,
    city_ar        VARCHAR(100) NOT NULL,
    district_ar    VARCHAR(150) NOT NULL,
    latitude       DECIMAL(10,6) NOT NULL,
    longitude      DECIMAL(10,6) NOT NULL,
    is_active      TINYINT(1) NOT NULL DEFAULT 1,
    created_at     TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (district_id),
    UNIQUE KEY uq_city_district (city_ar, district_ar),
    KEY idx_city (city_ar),
    KEY idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================================================
-- 2) DistrictQuarterAggregate — بيانات حي-ربع للمودل
-- =========================================================
CREATE TABLE DistrictQuarterAggregate (
    id                              BIGINT NOT NULL AUTO_INCREMENT,
    city_ar                         VARCHAR(100) NOT NULL,
    district_ar                     VARCHAR(150) NOT NULL,
    property_type_ar                VARCHAR(100) NOT NULL,
    year                            SMALLINT UNSIGNED NOT NULL,
    quarter                         TINYINT UNSIGNED NOT NULL,
    target_median_price_per_sqm     DECIMAL(12,2) NOT NULL,
    deals_count                     INT UNSIGNED NOT NULL,
    std_price                       DECIMAL(12,2) NULL,
    iqr_price                       DECIMAL(12,2) NULL,
    min_price                       DECIMAL(12,2) NULL,
    max_price                       DECIMAL(12,2) NULL,
    prev_year_median_price_per_sqm  DECIMAL(12,2) NULL,
    baseline_roll4                  DECIMAL(12,2) NULL,
    baseline_price_per_sqm          DECIMAL(12,2) NOT NULL,
    baseline_log                    DECIMAL(10,6) NULL,
    target_log                      DECIMAL(10,6) NULL,
    target_resid                    DECIMAL(10,6) NULL,
    latitude                        DECIMAL(10,6) NOT NULL,
    longitude                       DECIMAL(10,6) NOT NULL,
    dist_school_km                  DECIMAL(6,3) NULL,
    dist_hospital_km                DECIMAL(6,3) NULL,
    dist_mall_km                    DECIMAL(6,3) NULL,
    count_school_3km                INT UNSIGNED NULL DEFAULT 0,
    count_hospital_3km              INT UNSIGNED NULL DEFAULT 0,
    count_mall_3km                  INT UNSIGNED NULL DEFAULT 0,
    growth_pct                      DECIMAL(8,2) NULL DEFAULT 0,
    quarter_sin                     DECIMAL(10,6) NULL,
    quarter_cos                     DECIMAL(10,6) NULL,
    year_quarter_idx                INT UNSIGNED NULL,
    created_at                      TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_district_quarter (city_ar, district_ar, property_type_ar, year, quarter),
    KEY idx_city_type_yq (city_ar, property_type_ar, year, quarter),
    KEY idx_year_quarter (year, quarter)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================================================
-- 3) DistrictGrowthYoy — نمو YoY لكل (مدينة، حي، نوع)
-- =========================================================
CREATE TABLE DistrictGrowthYoy (
    id                  INT NOT NULL AUTO_INCREMENT,
    city_ar             VARCHAR(100) NOT NULL,
    district_ar         VARCHAR(150) NOT NULL,
    property_type_ar    VARCHAR(100) NOT NULL,
    growth_pct          DECIMAL(8,2) NOT NULL,
    growth_source       VARCHAR(50) NULL DEFAULT 'default',
    growth_confidence   VARCHAR(20) NULL DEFAULT 'low',
    updated_at          TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_city_district_type (city_ar, district_ar, property_type_ar),
    KEY idx_city_type (city_ar, property_type_ar)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================================================
-- 4) AggregatedPriceModelVersion — نسخ المودل
-- =========================================================
CREATE TABLE AggregatedPriceModelVersion (
    version_id      INT NOT NULL AUTO_INCREMENT,
    trained_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    min_deals       TINYINT UNSIGNED NOT NULL,
    artifact_path   VARCHAR(500) NOT NULL,
    metrics_json    JSON NULL,
    feature_cols    JSON NULL,
    is_active       TINYINT(1) NOT NULL DEFAULT 0,
    notes           VARCHAR(500) NULL,
    PRIMARY KEY (version_id),
    KEY idx_active (is_active),
    KEY idx_trained (trained_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================================================
-- 5) RealSale — صفقات البيع الخام
-- =========================================================
CREATE TABLE RealSale (
    sale_id           BIGINT NOT NULL AUTO_INCREMENT,
    year              SMALLINT UNSIGNED NOT NULL,
    quarter           TINYINT UNSIGNED NOT NULL,
    region_ar         VARCHAR(100) NULL,
    city_ar           VARCHAR(100) NOT NULL,
    district_ar       VARCHAR(150) NOT NULL,
    property_type_ar  VARCHAR(100) NOT NULL,
    price_per_sqm     DECIMAL(12,2) NOT NULL,
    price_total       DECIMAL(14,2) NULL,
    area_sqm          DECIMAL(12,2) NULL,
    deed_count        INT UNSIGNED NULL DEFAULT 1,
    source            VARCHAR(100) NULL,
    tx_reference      VARCHAR(255) NULL,
    created_at        TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (sale_id),
    KEY idx_city_district_type (city_ar, district_ar, property_type_ar),
    KEY idx_year_quarter (year, quarter),
    KEY idx_source (source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- المستخدمون والمفضلة: في Supabase (auth.users + public.users + public.favorites).
-- لا ننشئ هنا Users / UserSessions / Favorites.
