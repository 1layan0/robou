# رفع قاعدة البيانات إلى Supabase

Supabase يعتمد على **PostgreSQL**. المشروع كان يستخدم MySQL، لذلك تم تجهيز سكيمة وجدولة بيانات متوافقة مع PostgreSQL.

## الخطوات

### 1) الحصول على رابط الاتصال من Supabase

- ادخلي إلى [Supabase](https://supabase.com/dashboard) → مشروعك.
- **Project Settings** → **Database**.
- في **Connection string** اختر **URI** وانسخي الرابط (مثال: `postgresql://postgres.[ref]:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres`).
- استبدلي `[YOUR-PASSWORD]` بكلمة مرور قاعدة البيانات إن طُلبت.

### 2) تشغيل السكيمة (مرة واحدة)

- في Supabase: **SQL Editor** → **New query**.
- انسخي محتوى الملف `db/schema_supabase.sql` والصقيه ثم **Run**.
- ثم شغّلي `db/favorites_supabase_auth.sql` لجدول المفضلة وRLS (يبني علاقة `district_id` → `District`).

### 3) توليد بيانات PostgreSQL المطبّعة ثم الرفع

السكيمة الحالية تعتمد على **`district_id`** في الجداول الفرعية. أعمدة النمو مميّزة بالاسم: **`quarter_feature_growth_pct`** (حي-ربع، ميزة من CSV) و **`yoy_growth_pct`** (ملخص YoY لكل حي/نوع). لإنشاء ملف الإدراج:

```bash
cd raboo3-ml
python scripts/build_supabase_aggregate_sql.py   # ينتج db/loaded_aggregate_pg.sql
```

ثم الرفع:

```bash
pip install -r requirements.txt   # يتضمن psycopg2-binary
# إمّا تصدير يدوي:
export SUPABASE_DB_URL='postgresql://postgres.xxx:كلمة_المرور@...'
# أو ضعي السطر في raboo3-ml/.env → السكربت يقرأه تلقائياً إن لم يكن المتغير مضبوطاً في الشل
python scripts/upload_to_supabase.py
```

السكربت يفضّل **`db/loaded_aggregate_pg.sql`** إن وُجد؛ وإلا يحذّر ويستخدم `loaded_aggregate.sql` (صيغة MySQL / أعمدة قديمة قد لا تطابق السكيمة المطبّعة).

## ملاحظات

- **لا** تخزّني كلمة مرور قاعدة البيانات في Git؛ استخدمي `.env` محلية أو `export` في الطرفية فقط.
- السكربت يحمّل `SUPABASE_DB_URL` من **`raboo3-ml/.env`** إذا لم يكن معرّفاً في البيئة (سطر واحد: `SUPABASE_DB_URL=postgresql://...`).
- إن واجهت حداً على حجم الطلب في Supabase، السكربت يقسّم الإدخالات تلقائياً (مثلاً 2000 صف لكل دفعة لـ RealSale و DistrictQuarterAggregate).
