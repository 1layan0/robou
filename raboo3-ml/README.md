# raboo3-ml

باكند **FastAPI** لـ Robou (ربوع): تقدير سعر المتر، توصية أحياء (`/recommend/districts`)، insights، صفقات، ومودل سعر مجمع (LightGBM/sklearn) مع بيانات تجميع حي-ربع.

## الهيكل

```
raboo3-ml/
├── api/           # FastAPI: predict، recommend، insights، deals، …
├── config/        # إعدادات وقوائم مدن/أحياء
├── data/          # CSVs، ميزات، صفقات
├── models/        # ميزات وموديلات
├── schemas/       # Pydantic
├── run.py         # تشغيل uvicorn
├── db/            # schema_aggregate (MySQL)، schema_supabase، loaded_aggregate*.sql
├── scripts/       # تدريب، تحميل، رفع إلى Supabase
├── docker-compose.yml
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
| `POST /predict` | تقدير سعر المتر (من valuation/DB أو افتراضي) + السعر الإجمالي |
| `POST /predict/investment` | تقييم الاستثمار: score + توصية (strong_buy \| buy \| hold \| avoid) |

**Body مثال (JSON):**
```json
{"city":"الدمام","district":"السيف","area_sqm":500,"land_use":"قطعة أرض-سكنى"}
```

**ملاحظة:** السعر في `/predict` يأتي من valuation (DB) أو قيمة افتراضية. **أفضل أحياء** (الفرونت) يعتمد على مودل السعر **المجمع** في الريكومندر (`price_model_agg_residual.pkl`).

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

**تطبيق الـ schema (جداول مودل السعر المجمع):** الملف `db/schema_aggregate.sql` ينشئ قاعدة `raboo3` والجداول الخمسة. بعد تشغيل MySQL:

```bash
docker exec -i raboo3-ml-mysql mysql -u root -p<MYSQL_ROOT_PASSWORD> < db/schema_aggregate.sql
```

(استبدل `<MYSQL_ROOT_PASSWORD>` بالقيمة من `.env`.)

## تحميل البيانات الحقيقية في MySQL

بعد تشغيل MySQL وتطبيق `db/schema_aggregate.sql`:

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

## جداول مودل السعر المجمع (5 جداول)

جداول الداتابيس لمودل السعر المجمع فقط: **District**، **DistrictQuarterAggregate**، **DistrictGrowthYoy**، **AggregatedPriceModelVersion**، **RealSale**.

**ملاحظة:** تطبيق `db/schema_aggregate.sql` يحذف الجداول القديمة (User, Transaction, LandParcel, …) وينشئ الجداول الخمسة فقط. استخدميه عندما تريدين الاكتفاء بمودل السعر المجمع. التقدير من الـ API يعتمد على المودل؛ عند فشله يُستخدم سعر افتراضي (لا استعلام على جداول الصفقات).

**إنشاء قاعدة البيانات والجداول الخمسة (بعد تشغيل MySQL):**

```bash
docker exec -i raboo3-ml-mysql mysql -u root -praboo3_root < db/schema_aggregate.sql
```

**توليد ملف التحميل من البيانات الحالية (CSV + metadata):**

```bash
python scripts/generate_aggregate_sql.py
```

**تحميل البيانات في Docker:**

```bash
docker exec -i raboo3-ml-mysql mysql -u root -praboo3_root raboo3 < db/loaded_aggregate.sql
```

(استبدلي كلمة السر إن اختلفت في `.env`.)

بديل: تحميل من Python مباشرة (يتطلب اتصال قاعدة البيانات من الجهاز وفق إعدادات `.env`):

```bash
python scripts/load_aggregate_tables_data.py
```

## موديل السعر + التكميل والتوليد

**عند إضافة أحياء جديدة** (مثل أحياء الظهران: السلمانية، الحرس الوطني، أجيال أرامكو...):

1. **إضافتك في المرجع:** عدّل `config/city_districts.json`
2. **تكميل بيانات التدريب** للأحياء بدون صفقات حقيقية:
   ```bash
   python scripts/augment_training_data.py
   ```
   يُنشئ `data/real/real_sales_augmented.csv` (حقيقي + مكمّل)
3. **مودل السعر:** المعتمد في المشروع هو **مودل السعر المجمع** (`train_price_model_aggregated.py` → `price_model_agg_residual.pkl`) للريكومندر (أفضل أحياء). مودل السعر per-parcel أُزيل؛ `/predict` يعتمد على valuation (DB) أو افتراضي.

قوائم الأحياء في `config/city_districts.json`.

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

**ملاحظة:** أسماء الأعمدة في `data/generated/*.csv` قد تختلف قليلاً عن جداول الـ schema. إن أردت تحميلها في MySQL استخدم سكربت تحميل يدعم تعيين الأعمدة أو عدّل الـ pipeline ليطابق الـ schema.

## مراكز الأحياء والمرافق (Google)

المشروع يستخدم **Google APIs** كمصدر أساسي لمراكز الأحياء والمرافق (بديل OSM).

- **مراكز الأحياء:** `scripts/fetch_district_centroids_from_numbers.py` — يقرأ قائمة أحياء من ملف Numbers ويحدّث `config/city_districts.json`، ويجلب الإحداثيات (Google Geocoding) ويحفظ في `data/raw/district_centroids.json` و `.csv`. يحتاج `GOOGLE_MAPS_API_KEY` في `.env`.
- **المرافق (مدارس، مستشفيات، مولات):** `scripts/fetch_google_places_services.py` — Places API (Text Search)، المخرجات: `data/raw/google_places_services.csv`.
- **ميزات القرب في الموديل:** `models/place_features.py` يقرأ من `google_places_services.csv` و `district_centroids.json`.

```bash
# مراكز الأحياء (يحتاج ملف Numbers للأحياء + GOOGLE_MAPS_API_KEY في .env)
python scripts/fetch_district_centroids_from_numbers.py "/path/to/الاحياء_final.numbers"
# المرافق
python scripts/fetch_google_places_services.py
```

## الربط مع الفرونت

الفرونت يضبط **`ML_API_URL`** (مثل `http://localhost:8000`) ويستدعي مسارات مثل **`POST /recommend/districts`** و **`GET /insights`** عبر Route Handlers في Next. راجع **`../README.md`** و **`../raboo3-frontend/README.md`**.

## مصادر البيانات وأثر المشاريع

لمن يريد معرفة **من أين نجلب بيانات "أثر المشاريع"** (طرق، خدمات، تخطيط، سوق، طلب، سكان) وما إذا كانت تحتاج تسجيلاً أم لا، راجع:

- **[docs/impact_sources.md](docs/impact_sources.md)** — جدول بالمصادر (OSM، بلدي U maps، هيئة العقار، سكني، GASTAT، أمانة الشرقية)، ماذا نستخرج من كل مصدر، وأقصر طريق يشتغل.

ملخص: OSM للخدمات والطرق ✅، بلدي خرائط حضرية للمخططات ✅، مؤشرات هيئة العقار (إكسل) ✅، سكني مؤشرات إيجارية ✅، GASTAT للسكان ✅؛ GIS أمانة الشرقية 🟡 قد يتطلب صلاحية.

## النمو (YoY)

معدل النمو يُستمد من **district_growth_yoy.csv** و **city_growth_yoy.csv** (يُبنى بـ `build_district_growth_yoy.py`) ويُستخدم في الريكومندر (أفضل أحياء). لا يوجد مودل نمو منفصل.

### إعداد بيانات النمو

من جذر المشروع:

```bash
# 1) اختياري: تحديث مراكز الأحياء والمرافق (مراكز الأحياء: من ملف Numbers + Google Geocoding؛ المرافق: fetch_google_places_services)
python scripts/fetch_district_centroids_from_numbers.py "/path/to/الاحياء_final.numbers"
python scripts/fetch_google_places_services.py

# 2) النمو (YoY): من district_growth_yoy و city_growth_yoy (يُبنى بـ build_district_growth_yoy.py)
#    يُستخدم في الريكومندر (أفضل أحياء)؛ لا يوجد مودل نمو منفصل.
```

## Supabase (رفع التجميع)

بعد تطبيق `db/schema_supabase.sql` و`favorites_supabase_auth.sql` في SQL Editor، يمكن رفع البيانات بـ `scripts/upload_to_supabase.py` و`SUPABASE_DB_URL` — التفاصيل في **`db/README_SUPABASE.md`**.
