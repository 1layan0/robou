-- =========================================================
-- المفضلة: مصدر الحقّة district_id + نوع العقار (يتمJOIN مع District للعرض).
-- user_id → auth.users (كما كان). district_id → public.district ON DELETE RESTRICT.
-- بعد هجرة من جدول قديم (city_ar/district_ar): احذفي الجدول يدوياً أو انقلوا البيانات ثم أعيدوا إنشاءه.
-- =========================================================

DROP TABLE IF EXISTS public.favorites;

CREATE TABLE public.favorites (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    district_id             INTEGER NOT NULL REFERENCES public.district(district_id) ON DELETE RESTRICT,
    property_type_ar        TEXT NOT NULL DEFAULT '',
    predicted_price_per_sqm NUMERIC NULL,
    -- لقطة عند الحفظ (للعرض دون الاعتماد على JOIN مع district ولا سيما مع RLS)
    city_ar                 TEXT NULL,
    district_ar             TEXT NULL,
    saved_year              INT NULL,
    saved_quarter           INT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, district_id, property_type_ar)
);

CREATE INDEX idx_favorites_user_id ON public.favorites (user_id);
CREATE INDEX idx_favorites_district_id ON public.favorites (district_id);

ALTER TABLE public.favorites ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can read own favorites" ON public.favorites;
CREATE POLICY "Users can read own favorites"
    ON public.favorites FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own favorites" ON public.favorites;
CREATE POLICY "Users can insert own favorites"
    ON public.favorites FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own favorites" ON public.favorites;
CREATE POLICY "Users can update own favorites"
    ON public.favorites FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own favorites" ON public.favorites;
CREATE POLICY "Users can delete own favorites"
    ON public.favorites FOR DELETE
    USING (auth.uid() = user_id);

-- ترقية للقواعد القديمة (آمنة للتكرار؛ لا تحذف البيانات):
ALTER TABLE public.favorites ADD COLUMN IF NOT EXISTS city_ar TEXT;
ALTER TABLE public.favorites ADD COLUMN IF NOT EXISTS district_ar TEXT;
