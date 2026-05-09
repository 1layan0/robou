# raboo3-frontend — واجهة ربوع (Next.js)

واجهة **Robou (ربوع)** بـ Next.js 15، عربي/إنجليزي، مع **Supabase Auth** (`@supabase/ssr` + كوكيز الجلسة) وربط اختياري بـ **FastAPI** (`raboo3-ml`) للتقدير.

## المتطلبات

- Node.js 20+
- حساب **Supabase** (مشروع مع Auth مفعّل)
- اختياري: **Mapbox** للخريطة، وتشغيل **raboo3-ml** محليًا للتقدير

## الإعداد

```bash
npm install
cp .env.example .env.local
```

### متغيرات مهمة في `.env.local`

| المتغير | الغرض |
|---------|--------|
| `NEXT_PUBLIC_SUPABASE_URL` | رابط مشروع Supabase |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | المفتاح العام (المتصفح) |
| `SUPABASE_SERVICE_ROLE_KEY` | **خادم فقط**: مسارات مثل `/api/account/update-email`، و`/api/insights` و`/api/deals` عند قراءة الجداول من Postgres |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | خريطة التقدير (إلزامي لعرض الخريطة الكاملة) |
| `ML_API_URL` | مثل `http://localhost:8000` — باكند التقدير والتوصية |

**استعادة كلمة المرور:** في Supabase → **Authentication → URL Configuration** أضيفي ضمن **Redirect URLs** على الأقل:

- `http://localhost:3000/auth/callback`
- `http://localhost:3000/ar/reset-password` و `.../en/reset-password`
- ونفس المسارات على نطاق الإنتاج وعلى `127.0.0.1` إن استخدمتِه.

التفاصيل في تعليقات `.env.example`.

## التشغيل

```bash
npm run dev
```

ثم [http://localhost:3000](http://localhost:3000) — غالبًا يُوجَّه إلى `/ar`.

## مسارات API (Next Route Handlers)

- `POST /api/predict/best-areas` — يوجّه إلى `ML_API_URL` (`/recommend/districts`)
- `GET /api/insights` — يقرأ من Supabase إن وُجدت البيانات والمفتاح، وإلا من `ML_API_URL`
- `GET /api/deals` — كذلك
- `GET /auth/callback` — تبادل PKCE لروابط استعادة كلمة المرور من الإيميل

## هيكل مهم

- `src/app/[locale]/` — الصفحات (predict، insights، transactions، account، login، signup، forgot-password، reset-password)
- `src/lib/supabase/client.ts` — عميل المتصفح (`createBrowserClient`)
- `src/app/auth/callback/route.ts` — استقبال `code` بعد رابط Supabase

## نشر (Vercel)

انظري **`VERCEL_DEPLOY.md`** لملاحظات أسماء المشاريع والتعارضات الشائعة.

## المرجع العام للمستودع

راجع **`../README.md`** في جذر المستودع لربط الفرونت مع الباكند وقواعد البيانات.
