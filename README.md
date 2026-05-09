# Robou (ربوع) — تقدير عقاري وأحياء

مستودع واحد للنسخة المعتمدة من **ربوع**: واجهة ويب (Next.js) + باكند ML (FastAPI) + بيانات وجداول جاهزة. المصادقة والمفضلة عبر **Supabase**؛ الباكند يقرأ من **MySQL** (Docker) أو يمكن رفع البيانات إلى **Supabase**.

---

## محتويات المستودع

| المجلد | الوصف |
|--------|--------|
| **raboo3-frontend** | واجهة Next.js: تقدير، خريطة، توصية، تحليلات، صفقات، حساب، مفضلة، استعادة كلمة المرور (PKCE عبر `/auth/callback`) |
| **raboo3-ml** | باكند FastAPI: تقدير سعر المتر، أفضل أحياء، insights، صفقات (RealSale)، مودل مجمع + CSV |

البيانات المعتمدة للباكند (MySQL): `raboo3-ml/db/loaded_aggregate.sql` + ملفات في `raboo3-ml/data/`. لرفع التجميع إلى Postgres/Supabase: `raboo3-ml/db/loaded_aggregate_pg.sql` (يُولَّد عبر `scripts/build_supabase_aggregate_sql.py`) — انظر `raboo3-ml/db/README_SUPABASE.md`.

---

## تشغيل سريع — الواجهة (Frontend)

```bash
cd raboo3-frontend
npm install
cp .env.example .env.local
# عدّلي في .env.local (انظر raboo3-frontend/.env.example):
#   NEXT_PUBLIC_SUPABASE_URL، NEXT_PUBLIC_SUPABASE_ANON_KEY
#   SUPABASE_SERVICE_ROLE_KEY (للمسارات التي تقرأ من DB على الخادم)
#   NEXT_PUBLIC_MAPBOX_TOKEN، ML_API_URL=http://localhost:8000
npm run dev
```

ثم افتحي `http://localhost:3000` (مثلاً `/ar` للعربي).

- **Supabase:** Auth، المفضلة، والبروفايل؛ مسارات **`/api/insights`** و **`/api/deals`** تستخدم **service role** على الخادم إن وُجدت جداول التجميع في Supabase.
- تفاصيل الواجهة والمتغيرات: **`raboo3-frontend/README.md`**.

---

## تشغيل سريع — الباكند (ML API)

```bash
cd raboo3-ml
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# اختياري: انسخي .env.example إلى .env وعدّلي (MySQL، مفاتيح Google/OpenAI)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

- التوثيق: `http://localhost:8000/docs`
- الصحة: `http://localhost:8000/health`

الباكند يقرأ من **MySQL** (انظر أدناه). لو تريدين تشغيله بدون Docker، تأكدي أن MySQL شغال وطبّقي السكيمة والبيانات كما في `raboo3-ml/README.md`.

---

## قاعدة البيانات

### MySQL (للباكند المحلي)

- **Docker:** من مجلد `raboo3-ml`: `docker compose up -d`
- **السكيمة:** `raboo3-ml/db/schema_aggregate.sql` (جداول: District، RealSale، DistrictQuarterAggregate، DistrictGrowthYoy، AggregatedPriceModelVersion)
- **البيانات:** `raboo3-ml/db/loaded_aggregate.sql` — حمّليه بعد السكيمة:
  ```bash
  docker exec -i raboo3-ml-mysql mysql -u root -praboo3_root raboo3 < raboo3-ml/db/loaded_aggregate.sql
  ```
- إعدادات الاتصال في `raboo3-ml/config/settings.py` و `raboo3-ml/.env` (من `.env.example`).

### Supabase (الواجهة + اختياري للباكند)

- **المصادقة والمفضلة:** الواجهة تتصل مباشرة بـ Supabase (Auth + جدول `public.favorites`).
- **نسيت كلمة المرور:** الإيميل يوجّه إلى `/auth/callback` (تبادل PKCE على الخادم) ثم `/{locale}/reset-password`. في Supabase → **Redirect URLs** أضيفي `http://localhost:3000/auth/callback` و`/ar/reset-password` و`/en/reset-password` (انظر `raboo3-frontend/.env.example`).
- **سكيمات Supabase:**
  - `raboo3-ml/db/schema_supabase.sql` — الجداول الرئيسية + جدول `Users` + تريجر من `auth.users`
  - `raboo3-ml/db/favorites_supabase_auth.sql` — جدول `public.favorites` + RLS
- **رفع البيانات إلى Supabase:** بعد تشغيل السكيمات من Supabase SQL Editor:
  ```bash
  cd raboo3-ml
  export SUPABASE_DB_URL='postgresql://...'
  pip install psycopg2-binary
  python scripts/upload_to_supabase.py
  ```
  راجع `raboo3-ml/db/README_SUPABASE.md` إن وُجد.

---

## ما الذي لا يُرفع في المستودع

- ملفات `.env` و `.env.local` (مفاتيح واتصالات) — استخدمي `.env.example` كمرجع.
- `node_modules/` و `raboo3-frontend/.next/`.
---

## الصفحات الرئيسية (الواجهة)

- `/` أو `/ar` — الرئيسية
- `/[locale]/predict` — تقدير وتوصية أفضل أحياء (يتطلب `ML_API_URL`)
- `/[locale]/insights` — تحليلات (Supabase أو ML حسب الإعداد)
- `/[locale]/transactions` — صفقات (Supabase أو ML)
- `/[locale]/account` — الحساب والمفضلة
- `/[locale]/login` ، `/[locale]/signup` ، `/[locale]/forgot-password` ، `/[locale]/reset-password`
- `/auth/callback` — استعادة كلمة المرور (PKCE، بدون بادئة لغة)

---

## قراءة إضافية

- **raboo3-frontend/README.md** — تفاصيل الواجهة، Mapbox، Supabase، ML API.
- **raboo3-ml/README.md** — Docker، MySQL، تحميل البيانات، مودل السعر المجمع، سكربتات التحميل والرفع.
