-- =========================================================
-- PostgreSQL schema for Supabase (من schema_aggregate.sql MySQL)
-- نموذج مُطبّع: الأحياء والأسماء العربية ومركز الحي في جدول District فقط.
-- الجداول الفرعية تحتفظ بـ district_id + الحقول غير المكررة.
-- ربط المصادقة: Users.id = auth.users فقط.
-- شغّليه في Supabase: SQL Editor → New query → Paste → Run
-- ثم db/favorites_supabase_auth.sql
-- بيانات التجميع: python scripts/build_supabase_aggregate_sql.py ثم رفع db/loaded_aggregate_pg.sql
-- =========================================================

DROP TABLE IF EXISTS Favorites CASCADE;
DROP TABLE IF EXISTS UserSessions CASCADE;
DROP TABLE IF EXISTS Users CASCADE;
DROP TABLE IF EXISTS RealSale CASCADE;
DROP TABLE IF EXISTS DistrictQuarterAggregate CASCADE;
DROP TABLE IF EXISTS DistrictGrowthYoy CASCADE;
DROP TABLE IF EXISTS AggregatedPriceModelVersion CASCADE;
DROP TABLE IF EXISTS District CASCADE;

-- =========================================================
-- 1) District
-- =========================================================
CREATE TABLE District (
    district_id    SERIAL PRIMARY KEY,
    city_ar        VARCHAR(100) NOT NULL,
    district_ar    VARCHAR(150) NOT NULL,
    latitude       NUMERIC(10,6) NOT NULL,
    longitude      NUMERIC(10,6) NOT NULL,
    is_active      SMALLINT NOT NULL DEFAULT 1,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (city_ar, district_ar)
);
CREATE INDEX idx_district_city ON District (city_ar);
CREATE INDEX idx_district_active ON District (is_active);

-- =========================================================
-- 2) DistrictQuarterAggregate
-- =========================================================
CREATE TABLE DistrictQuarterAggregate (
    id                              BIGSERIAL PRIMARY KEY,
    district_id                     INTEGER NOT NULL REFERENCES District (district_id) ON DELETE RESTRICT,
    property_type_ar                VARCHAR(100) NOT NULL,
    year                            SMALLINT NOT NULL,
    quarter                         SMALLINT NOT NULL,
    target_median_price_per_sqm     NUMERIC(12,2) NOT NULL,
    deals_count                     INTEGER NOT NULL,
    std_price                       NUMERIC(12,2),
    iqr_price                       NUMERIC(12,2),
    min_price                       NUMERIC(12,2),
    max_price                       NUMERIC(12,2),
    prev_year_median_price_per_sqm  NUMERIC(12,2),
    baseline_roll4                  NUMERIC(12,2),
    baseline_price_per_sqm          NUMERIC(12,2) NOT NULL,
    baseline_log                    NUMERIC(10,6),
    target_log                      NUMERIC(10,6),
    target_resid                    NUMERIC(10,6),
    dist_school_km                  NUMERIC(6,3),
    dist_hospital_km                NUMERIC(6,3),
    dist_mall_km                    NUMERIC(6,3),
    count_school_3km                INTEGER DEFAULT 0,
    count_hospital_3km              INTEGER DEFAULT 0,
    count_mall_3km                  INTEGER DEFAULT 0,
    -- نمو مرتبط بالربع كميزة في بيانات الحي-ربع (مصدر CSV: growth_pct؛ لا يُخلط مع yoy_growth_pct)
    quarter_feature_growth_pct      NUMERIC(8,2) DEFAULT 0,
    quarter_sin                     NUMERIC(10,6),
    quarter_cos                     NUMERIC(10,6),
    year_quarter_idx                INTEGER,
    created_at                      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (district_id, property_type_ar, year, quarter)
);
CREATE INDEX idx_dq_district_type_yq ON DistrictQuarterAggregate (district_id, property_type_ar, year, quarter);
CREATE INDEX idx_dq_year_quarter ON DistrictQuarterAggregate (year, quarter);

-- =========================================================
-- 3) DistrictGrowthYoy
-- =========================================================
CREATE TABLE DistrictGrowthYoy (
    id                  SERIAL PRIMARY KEY,
    district_id         INTEGER NOT NULL REFERENCES District (district_id) ON DELETE RESTRICT,
    property_type_ar    VARCHAR(100) NOT NULL,
    yoy_growth_pct      NUMERIC(8,2) NOT NULL,
    growth_source       VARCHAR(50) DEFAULT 'default',
    growth_confidence   VARCHAR(20) DEFAULT 'low',
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (district_id, property_type_ar)
);
CREATE INDEX idx_growth_district ON DistrictGrowthYoy (district_id);

-- =========================================================
-- 4) AggregatedPriceModelVersion
-- =========================================================
CREATE TABLE AggregatedPriceModelVersion (
    version_id      SERIAL PRIMARY KEY,
    trained_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    min_deals       SMALLINT NOT NULL,
    artifact_path   VARCHAR(500) NOT NULL,
    metrics_json    JSONB,
    feature_cols    JSONB,
    is_active       SMALLINT NOT NULL DEFAULT 0,
    notes           VARCHAR(500)
);
CREATE INDEX idx_model_active ON AggregatedPriceModelVersion (is_active);
CREATE INDEX idx_model_trained ON AggregatedPriceModelVersion (trained_at);

-- =========================================================
-- 5) RealSale
-- =========================================================
CREATE TABLE RealSale (
    sale_id           BIGSERIAL PRIMARY KEY,
    district_id       INTEGER NOT NULL REFERENCES District (district_id) ON DELETE RESTRICT,
    year              SMALLINT NOT NULL,
    quarter           SMALLINT NOT NULL,
    region_ar         VARCHAR(100),
    property_type_ar  VARCHAR(100) NOT NULL,
    price_per_sqm     NUMERIC(12,2) NOT NULL,
    price_total       NUMERIC(14,2),
    area_sqm          NUMERIC(12,2),
    deed_count        INTEGER DEFAULT 1,
    source            VARCHAR(100),
    tx_reference      VARCHAR(255),
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_realsale_district ON RealSale (district_id);
CREATE INDEX idx_realsale_yq ON RealSale (year, quarter);
CREATE INDEX idx_realsale_source ON RealSale (source);
CREATE INDEX idx_realsale_district_type ON RealSale (district_id, property_type_ar);

-- =========================================================
-- 6) Users
-- =========================================================
CREATE TABLE Users (
    id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email        TEXT UNIQUE,
    first_name   TEXT,
    last_name    TEXT,
    phone        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER district_updated_at BEFORE UPDATE ON District
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER users_updated_at BEFORE UPDATE ON Users
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can read own profile" ON public.users;
CREATE POLICY "Users can read own profile"
  ON public.users FOR SELECT
  USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON public.users;
CREATE POLICY "Users can update own profile"
  ON public.users FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert own profile" ON public.users;
CREATE POLICY "Users can insert own profile"
  ON public.users FOR INSERT
  WITH CHECK (auth.uid() = id);

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (id, email, first_name, last_name, phone, created_at, updated_at)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'first_name', NEW.raw_user_meta_data->>'given_name'),
    COALESCE(NEW.raw_user_meta_data->>'last_name', NEW.raw_user_meta_data->>'family_name'),
    NEW.phone,
    NOW(),
    NOW()
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- public.favorites: ملف db/favorites_supabase_auth.sql
--
-- ترقية أسماء أعمدة النمو (من نسخة سابقة growth_pct في الجدولين):
--   ALTER TABLE DistrictQuarterAggregate RENAME COLUMN growth_pct TO quarter_feature_growth_pct;
--   ALTER TABLE DistrictGrowthYoy RENAME COLUMN growth_pct TO yoy_growth_pct;
