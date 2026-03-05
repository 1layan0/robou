# raboo3-ml

مشروع ML منفصل لـ Robou (ربوع) — تقدير أسعار الأراضي. الهيكل جاهز، والمودلز تُضاف لاحقاً.

## الهيكل

```
raboo3-ml/
├── api/           # FastAPI: health + predict (stub)
├── config/        # إعدادات التطبيق
├── data/          # تحميل ومعالجة البيانات (لاحقاً)
├── models/        # تعريف المودلز واستدعاؤها (لاحقاً)
├── schemas/       # Pydantic: طلبات واستجابات الـ API
├── run.py         # تشغيل السيرفر
├── db/                 # SQL schema و migrations
├── scripts/            # سكربتات مساعدة (مولد بيانات وهمية)
├── docker-compose.yml  # MySQL عبر Docker
├── requirements.txt
└── README.md
```

## التشغيل

```bash
cd raboo3-ml
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

أو:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: [http://localhost:8000/health](http://localhost:8000/health)
- Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

**Endpoints لكل المودلز (نفس الـ body لجميعها):**

| Endpoint | الوصف |
|----------|--------|
| `POST /predict` | مودل السعر: سعر المتر + السعر الإجمالي |
| `POST /predict/rent` | مودل الإيجار: الإيجار الشهري (ريال) |
| `POST /predict/growth` | مودل النمو: معدل النمو السنوي (%) |
| `POST /predict/investment` | تقييم الاستثمار: score + توصية (strong_buy \| buy \| hold \| avoid) |

**Body مثال (JSON) — استخدم قيماً عربية من بيانات التدريب:**
```json
{"city":"الدمام","district":"السيف","area_sqm":500,"land_use":"قطعة أرض-سكنى"}
```

**التركيز:** المشروع يركز على **الدمام والظهران والخبر** فقط. أي مدينة أخرى تُرجع 400.  
**أنواع العقار المسموحة (land_use):** `قطعة أرض-سكنى`، `قطعة أرض-تجارى`، `شقة`، `فيلا`  
**المدينة والحي:** يجب أن يكونا زوجاً موجوداً في بيانات التدريب (مثل الدمام+السيف). إذا أدخلت حي غير تابع للمدينة يُرجع 400.

**تجربة من المتصفح:** افتح [http://localhost:8000/docs](http://localhost:8000/docs) واختر أي endpoint واضغط Try it out.

**تجربة من الطرفية:** شغّل السيرفر أولاً (`python run.py`)، ثم في طرفية ثانية:
```bash
python scripts/try_api.py
```

## قاعدة البيانات MySQL (Docker)

تشغيل MySQL في الخلفية:

```bash
# انسخ .env من المثال وعدّل كلمة السر إن تحتاج
cp .env.example .env

# تشغيل الحاوية
docker compose up -d

# التأكد أن الخدمة شغالة
docker compose ps
```

الاتصال: `localhost:3306`، قاعدة البيانات الافتراضية `raboo3_ml`، المستخدم `root` وكلمة السر من `MYSQL_ROOT_PASSWORD` في `.env`. إعدادات التطبيق (للربط لاحقاً) في `config/settings.py`: `db_host`, `db_port`, `db_user`, `db_password`, `db_name`, و`database_url`.

إيقاف MySQL: `docker compose down`. الحفاظ على البيانات: `docker compose down` فقط (بدون `-v`) حتى يبقى الـ volume.

**تطبيق الـ schema (جداول Raboo3):** الملف `db/schema.sql` ينشئ قاعدة `raboo3` وجميع الجداول. بعد تشغيل MySQL:

```bash
# من جهازك (يحتاج عميل mysql أو استيراد من واجهة)
mysql -h 127.0.0.1 -P 3306 -u root -p < db/schema.sql
# كلمة السر من MYSQL_ROOT_PASSWORD في .env
```

أو من داخل الحاوية:

```bash
docker exec -i raboo3-ml-mysql mysql -u root -p<MYSQL_ROOT_PASSWORD> < db/schema.sql
```

(استبدل `<MYSQL_ROOT_PASSWORD>` بالقيمة من `.env`.)

## تحميل البيانات الحقيقية في MySQL

بعد تشغيل MySQL وتطبيق `db/schema.sql`:

```bash
python scripts/load_real_data_to_mysql.py
```

أو باستخدام الملف الجاهز (أسرع):

```bash
python scripts/run_loaded_real_sql.py
```

البيانات: صفقات عقارية حقيقية، مرافق OSM، أحياء. راجع `data/real/` و `scripts/merge_real_estate_data.py` للدمج من Excel.

**بيانات منصة أرض:** إذا كان عندك ملفات صفقات أو سجل عقاري من منصة أرض (مثلاً مُصدّرة من Numbers)، صدّرها إلى Excel أو CSV ثم:
```bash
python scripts/ingest_ard_platform_data.py --dir "المسار/إلى/مجلد/الملفات"
# أو دمج ثم إعادة تدريب مباشرة:
python scripts/ingest_ard_platform_data.py --dir "المسار/إلى/مجلد/الملفات" --train
```
السكربت يدمجها مع `real_sales_merged.csv` ويضع المصدر "منصة ارض".

## موديل السعر + التكميل والتوليد

**عند إضافة أحياء جديدة** (مثل أحياء الظهران: السلمانية، الحرس الوطني، أجيال أرامكو...):

1. **إضافتك في المرجع:** عدّل `config/city_districts.json`
2. **تكميل بيانات التدريب** للأحياء بدون صفقات حقيقية:
   ```bash
   python scripts/augment_training_data.py
   ```
   يُنشئ `data/real/real_sales_augmented.csv` (حقيقي + مكمّل)
3. **إعادة تدريب الموديل:** `train_price_model` يقرأ الملف المكمّل تلقائياً إن وُجد:
   ```bash
   python -m scripts.train_price_model
   ```
   **ملاحظة:** ملف `artifacts/price_per_sqm_model.pkl` غير موجود في المستودع (حجمه يتجاوز حد GitHub). بعد استنساخ المشروع شغّلي التدريب أعلاه لتوليده محلياً.

قوائم الأحياء وحدها في `config/city_districts.json`؛ التحقق قبل/بعد التوليد في `config/districts.py`.

## Pipeline بيانات ربوع (Open Data + OSM + CSVs)

السكربت `scripts/robou_data_pipeline.py` يجمع ثلاث مهام:
1. **تحميل منصة البيانات المفتوحة:** يقرأ قائمة روابط من `open_data_urls.json` (في جذر المشروع) ويحمّل الملفات إلى `data/raw/`.
2. **تحميل GIS من OpenStreetMap:** مرافق وطرق للدمام، الظهران، الخبر → `data/osm/`.
3. **توليد كل CSVات دفعة واحدة:** User, DataSource, Zoning, Neighborhood, Facility, LandParcel, ParcelFacilityProximity, Transaction, Listing, ParcelImage, Prediction → `data/generated/`.

**متطلبات إضافية للـ OSM:** `pip install geopandas shapely osmnx` (اختياري؛ بدونها يعمل فقط التحميل من open data وتوليد الـ CSVs).

**تشغيل:**

```bash
# من جذر المشروع
cd raboo3-ml

# إضافة روابط التحميل في open_data_urls.json ثم:
python scripts/robou_data_pipeline.py --download_open_data --urls_json open_data_urls.json

# تحميل OSM (يحتاج إنترنت + osmnx)
python scripts/robou_data_pipeline.py --download_osm

# توليد كل الـ CSVs
python scripts/robou_data_pipeline.py --generate_csvs
```

**ملاحظة:** أسماء الأعمدة في `data/generated/*.csv` قد تختلف قليلاً عن `db/schema.sql` (مثلاً area_m2 vs area_sqm). إن أردت تحميلها في MySQL استخدم سكربت تحميل يدعم تعيين الأعمدة أو عدّل الـ pipeline ليطابق الـ schema.

## مراكز الأحياء والمرافق (Google)

المشروع يستخدم **Google APIs** كمصدر أساسي لمراكز الأحياء والمرافق (بديل OSM).

- **مراكز الأحياء:** `scripts/fetch_district_centroids_google.py` — Geocoding API، المخرجات: `data/raw/district_centroids.json` و `.csv`. يحتاج `GOOGLE_MAPS_API_KEY` في `.env`.
- **المرافق (مدارس، مستشفيات، مولات):** `scripts/fetch_google_places_services.py` — Places API (Text Search)، المخرجات: `data/raw/google_places_services.csv`.
- **ميزات القرب في الموديل:** `models/osm_features.py` يقرأ من `google_places_services.csv` إن وُجد، ومراكز المدن من `district_centroids.json`؛ وإلا يعود لـ OSM.

```bash
# بعد إضافة GOOGLE_MAPS_API_KEY في .env
python scripts/fetch_district_centroids_google.py
python scripts/fetch_google_places_services.py
```

OSM (Nominatim، Overpass، `osm_services.csv`) يبقى كخيار احتياطي إن لم تتوفر بيانات Google.

## الربط مع الفرونت

الفرونت (`raboo3-frontend`) يرسل طلبات POST إلى هذا الـ API (مثلاً `http://localhost:8000/predict`). غيّري الرابط في متغير البيئة أو في كود الفرونت عند النشر.

## مصادر البيانات وأثر المشاريع

لمن يريد معرفة **من أين نجلب بيانات "أثر المشاريع"** (طرق، خدمات، تخطيط، سوق، طلب، سكان) وما إذا كانت تحتاج تسجيلاً أم لا، راجع:

- **[docs/impact_sources.md](docs/impact_sources.md)** — جدول بالمصادر (OSM، بلدي U maps، هيئة العقار، سكني، GASTAT، أمانة الشرقية)، ماذا نستخرج من كل مصدر، وأقصر طريق يشتغل.

ملخص: OSM للخدمات والطرق ✅، بلدي خرائط حضرية للمخططات ✅، مؤشرات هيئة العقار (إكسل) ✅، سكني مؤشرات إيجارية ✅، GASTAT للسكان ✅؛ GIS أمانة الشرقية 🟡 قد يتطلب صلاحية.

## مودل النمو (Growth Model)

مودل النمو يقدّر **معدل النمو السنوي** (كسر، مثلاً 0.05 = 5%) لكل (مدينة، حي، نوع استخدام) بناءً على بيانات الصفقات التاريخية ومرافق Google.

### تدريب المودل

من جذر المشروع:

```bash
# 1) اختياري: تحديث مراكز الأحياء والمرافق من Google (يحتاج GOOGLE_MAPS_API_KEY في .env)
python scripts/fetch_district_centroids_google.py
python scripts/fetch_google_places_services.py

# 2) تدريب مودل النمو (يقرأ من data/real/real_sales_merged.csv + quarter_report إن وُجد)
python -m scripts.train_growth_model
```

المخرجات:
- `artifacts/growth_model.pkl` — المودل (مثلاً LightGBM)
- `artifacts/growth_model_metadata.json` — قوائم المدن/الأحياء/الأنواع، قرب مرافق، وقيم افتراضية للميزات

### الميزات المستخدمة (مشتقة من البيانات الحالية)

| الميزة | الوصف |
|--------|--------|
| سنة البداية، مساحة، سعر المتر السابق، عدد صفقات السنة السابقة | من التجميع (سنة، مدينة، حي، نوع) |
| lagged_growth | نمو السنة السابقة لنفس (مدينة، حي، نوع) |
| liquidity_2y | مجموع عدد الصفقات في السنتين السابقتين |
| price_volatility | انحراف معياري لسعر المتر حتى سنة البداية |
| city_avg_growth | متوسط نمو المدينة في نفس السنة |
| region_avg_growth | متوسط نمو المنطقة (الشرقية) في نفس السنة |
| growth_2y | نمو تراكمي سنتين: (سعر الآن − سعر قبل سنتين) / سعر قبل سنتين |
| price_trend_slope | ميل الاتجاه السعري (انحدار خطي لآخر 3 سنوات، معادلته سنوية) |
| قرب مرافق | مسافات أقرب مدرسة/مستشفى/مول + عددها ضمن 3 كم (من Google Places) |
| نوع الاستخدام، مدينة، حي | فئات (OneHot) |

### كيف تستخدم المودل

**1) عبر الـ API (بعد تشغيل السيرفر):**

```bash
python run.py
# في طرفية ثانية أو من المتصفح:
curl -X POST http://localhost:8000/predict/growth \
  -H "Content-Type: application/json" \
  -d '{"city":"الدمام","district":"السيف","area_sqm":500,"land_use":"قطعة أرض-سكنى"}'
```

الاستجابة تحتوي معدل النمو السنوي (كسر أو نسبة مئوية حسب تصميم الـ endpoint).

**2) من بايثون (سكربت أو تطبيق):**

```python
from schemas.predict import PredictRequest
from models.growth_model import predict_annual_growth_rate_from_request

req = PredictRequest(city="الدمام", district="السيف", area_sqm=500, land_use="قطعة أرض-سكنى")
rate = predict_annual_growth_rate_from_request(req)  # مثلاً 0.04 = 4%
print(f"معدل النمو السنوي: {rate:.2%}")
```

**تجربة سريعة من الطرفية:**

```bash
python scripts/try_growth_model.py
```

السكربت يستدعي المودل بعدة طلبات نموذجية ويطبع النتائج.

## لاحقاً

- إضافة المودلز في `models/`
- تحميل البيانات ومعالجتها في `data/`
- استبدال استجابة `/predict` الحالية (stub) باستدعاء المودل الحقيقي
