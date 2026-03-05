'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import clsx from 'classnames';
import { CITIES, City } from '@/lib/cities';
import { getDistrictsForCity } from '@/lib/cityDistricts';
import type { PredictionResult } from '@/components/PriceCard';
import { CITY_CENTER, type CityKey } from '@/lib/geo';
import { useNotifications } from '@/contexts/NotificationContext';
import { useI18n, useT } from '@/i18n/useTranslations';

/** عنصر من استجابة أفضل أحياء (مقارنة 2–3 أحياء) */
export type BestAreaItem = {
  city: string;
  district: string;
  latitude: number;
  longitude: number;
  price_per_sqm: number;
  growth_rate_pct: number;
  reasons: string[];
  score?: number;
  confidence?: 'high' | 'medium' | 'low';
  confidence_reason?: { deals_count: number; volatility: number };
  services_level?: 'high' | 'medium' | 'low';
  growth_trend?: 'up' | 'flat' | 'down';
  growth_component?: { growth_pct: number; source: string; confidence: string };
};

export type PredictionPayload = PredictionResult & {
  city: City;
  coords: [number, number] | null;
  area?: number;
  district?: string;
  /** عند الطلب بـ bbox: قائمة 1–3 أحياء للمقارنة */
  bestAreas?: BestAreaItem[];
  /** فلتر القرب المطبّق على ترتيب الأحياء (قريب | متوسط | بعيد) */
  proximityApplied?: string;
  /** الأحياء متقاربة (فرق score صغير) */
  tie?: boolean;
  /** ملاحظة من الخادم */
  note?: string;
  /** أحدث سنة مستخدمة (من استجابة best-areas) */
  latestYear?: number;
  /** أحدث ربع مستخدم 1–4 (من استجابة best-areas) */
  latestQuarter?: number;
};

interface PredictFormProps {
  onPredicted?: (data: PredictionPayload) => void;
  onCityChange?: (city: CityKey) => void;
  onDistrictChange?: (district: string) => void;
  onError?: (message: string) => void;
  coords?: { lat: number; lng: number } | null;
  mismatch?: { selected: CityKey; detected: CityKey } | null;
}

type FormValues = {
  city: City;
  district: string;
  land_area_m2: number;
  land_use: 'سكني' | 'تجاري';
  num_streets: '1' | '2';
  proximity: 'قريب' | 'متوسط' | 'بعيد';
  latitude: number | null;
  longitude: number | null;
};

const defaultValues: FormValues = {
  city: 'الدمام',
  district: '',
  land_area_m2: 400,
  land_use: 'سكني',
  num_streets: '1',
  proximity: 'قريب',
  latitude: null,
  longitude: null,
};

export default function PredictForm({
  onPredicted,
  onCityChange,
  onDistrictChange,
  onError,
  coords,
  mismatch,
}: PredictFormProps) {
  const t = useT();
  const { locale } = useI18n();
  const isAr = locale === 'ar';
  const { addNotification } = useNotifications();
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    control,
    formState: { errors },
  } = useForm<FormValues>({ defaultValues, mode: 'onBlur' });

  const selectedCity = useWatch({ control, name: 'city' });
  const watchedDistrict = useWatch({ control, name: 'district' });

  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [dismissedMismatch, setDismissedMismatch] = useState(false);

  useEffect(() => {
    if (coords) {
      setValue('latitude', coords.lat, { shouldDirty: true });
      setValue('longitude', coords.lng, { shouldDirty: true });
      setMessage(isAr ? 'تم تحديد الموقع من الخريطة.' : 'Location set from map.');
    }
  }, [coords, setValue, isAr]);

  const prevCityRef = useRef<City | null>(null);
  
  useEffect(() => {
    if (selectedCity && onCityChange && selectedCity !== prevCityRef.current) {
      prevCityRef.current = selectedCity;
      onCityChange(selectedCity as CityKey);
    }
  }, [selectedCity, onCityChange]);

  // Reset district when city changes (new city = different districts list)
  useEffect(() => {
    setValue('district', '');
  }, [selectedCity, setValue]);

  useEffect(() => {
    if (!onDistrictChange) return;
    const handler = setTimeout(() => {
      const trimmed = (watchedDistrict || '').trim();
      onDistrictChange(trimmed);
    }, 300);
    return () => clearTimeout(handler);
  }, [watchedDistrict, onDistrictChange]);

  // Reset dismissed state when mismatch changes
  useEffect(() => {
    if (mismatch) {
      setDismissedMismatch(false);
    }
  }, [mismatch]);

  const onSubmit = handleSubmit(async (values) => {
    setSubmitting(true);
    setMessage(null);

    // Prevent submit if mismatch exists and not dismissed
    if (mismatch && !dismissedMismatch) {
      const msg = isAr ? 'تأكدي من تطابق المدينة مع موقع الحي على الخريطة.' : 'Please ensure the city matches the district location on the map.';
      setMessage(msg);
      onError?.(msg);
      addNotification({
        type: 'error',
        title: isAr ? 'لا يمكن إتمام التقدير' : 'Cannot Complete Valuation',
        message: t.predict.form.validation_mismatch
          .replace('{{detected}}', mismatch.detected)
          .replace('{{selected}}', mismatch.selected),
        duration: 5000,
      });
      setSubmitting(false);
      return;
    }

    const trimmedDistrict = values.district.trim();
    if (!trimmedDistrict) {
      const msg = isAr ? 'فضلاً أدخل اسم الحي.' : 'Please enter the district name.';
      setMessage(msg);
      onError?.(msg);
      setSubmitting(false);
      return;
    }

    if (values.land_area_m2 < 50) {
      const msg = isAr ? 'المساحة يجب ألا تقل عن 50 م².' : 'Area must be at least 50 sqm.';
      setMessage(msg);
      onError?.(msg);
      setSubmitting(false);
      return;
    }

    try {
      const response = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          city: values.city,
          district: trimmedDistrict,
          land_area_m2: Number(values.land_area_m2),
          land_use: values.land_use,
          num_streets: Number(values.num_streets),
          proximity: values.proximity,
          lat: values.latitude ?? coords?.lat ?? undefined,
          lng: values.longitude ?? coords?.lng ?? undefined,
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        const errorMessage = payload?.error ?? (isAr ? 'فشل تنفيذ التقدير، تحقق من البيانات وجرب مجددًا.' : 'Valuation failed. Please check the data and try again.');
        setMessage(errorMessage);
        onError?.(errorMessage);
        return;
      }

      const data = (await response.json()) as PredictionResult & { city: City; coords: { lat: number; lng: number } | null };
      
      let fallbackCoords: [number, number] | null = null;
      if (data.coords && typeof data.coords.lat === 'number' && typeof data.coords.lng === 'number' && !isNaN(data.coords.lat) && !isNaN(data.coords.lng)) {
        fallbackCoords = [data.coords.lat, data.coords.lng];
      } else if (CITY_CENTER[data.city]) {
        fallbackCoords = [CITY_CENTER[data.city][0], CITY_CENTER[data.city][1]];
      }
      
      onPredicted?.({
        ...data,
        coords: fallbackCoords,
        area: values.land_area_m2,
        district: trimmedDistrict,
      });
      setMessage(isAr ? 'تم تحديث نتيجة التقدير.' : 'Valuation result updated.');
      addNotification({
        type: 'success',
        title: isAr ? 'تم التقدير بنجاح' : 'Valuation Successful',
        message: isAr
          ? `تم تقدير سعر الأرض في ${data.city}. سعر المتر: ${data.pricePerSqm.toLocaleString('ar-SA')} ر.س`
          : `Land price estimated in ${data.city}. Price per sqm: ${data.pricePerSqm.toLocaleString('en-US')} SAR`,
        duration: 4000,
      });
    } catch (error) {
      const fallback = error instanceof Error ? error.message : (isAr ? 'حدث خطأ غير متوقع.' : 'An unexpected error occurred.');
      setMessage(fallback);
      onError?.(fallback);
      addNotification({
        type: 'error',
        title: isAr ? 'فشل التقدير' : 'Valuation Failed',
        message: fallback,
        duration: 5000,
      });
    } finally {
      setSubmitting(false);
    }
  });

  const fieldProps = useMemo(
    () => ({
      city: register('city', { required: isAr ? 'اختر المدينة' : 'Select city' }),
      district: register('district', {
        required: isAr ? 'اختر الحي' : 'Select district',
      }),
      landArea: register('land_area_m2', {
        required: isAr ? 'أدخل المساحة' : 'Enter area',
        valueAsNumber: true,
        min: { value: 50, message: isAr ? 'الحد الأدنى 50 م²' : 'Minimum 50 sqm' },
      }),
      landUse: register('land_use', { required: isAr ? 'اختر نوع الاستخدام' : 'Select land use' }),
      numStreets: register('num_streets', { required: isAr ? 'حدد عدد الشوارع' : 'Select number of streets' }),
      proximity: register('proximity', { required: isAr ? 'حدد القرب من الخدمات' : 'Select proximity to services' }),
      latitude: register('latitude', { valueAsNumber: true }),
      longitude: register('longitude', { valueAsNumber: true }),
    }),
    [register, isAr]
  );

  const districtOptions = getDistrictsForCity((selectedCity as CityKey) ?? 'الدمام');

  const cityOptions = [
    { value: 'الدمام' as City, label: t.predict.form.city_dammam },
    { value: 'الخبر' as City, label: t.predict.form.city_khobar },
    { value: 'الظهران' as City, label: t.predict.form.city_dhahran },
  ];

  return (
    <section className={clsx('space-y-5', submitting && 'shimmer')} dir={isAr ? 'rtl' : 'ltr'}>
      <form className="grid gap-5" onSubmit={onSubmit} noValidate aria-live="polite">
        <input type="hidden" {...fieldProps.latitude} />
        <input type="hidden" {...fieldProps.longitude} />
        <div className="grid gap-5 md:grid-cols-2">
          <Field label={t.predict.form.city} error={errors.city?.message} htmlFor="city">
            <select id="city" {...fieldProps.city}>
              {cityOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t.predict.form.district} error={errors.district?.message} htmlFor="district">
            <select id="district" {...fieldProps.district}>
              <option value="">{isAr ? 'اختر الحي' : 'Select district'}</option>
              {districtOptions.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t.predict.form.district_hint}</p>
          </Field>
          <Field label={t.predict.form.area_sqm} error={errors.land_area_m2?.message} htmlFor="land_area_m2">
            <input id="land_area_m2" type="number" min={50} step={10} {...fieldProps.landArea} />
          </Field>
          <Field label={t.predict.form.land_use} error={errors.land_use?.message} htmlFor="land_use">
            <select id="land_use" {...fieldProps.landUse}>
              <option value="سكني">{t.predict.form.land_use_res}</option>
              <option value="تجاري">{t.predict.form.land_use_com}</option>
            </select>
          </Field>
          <Field label={t.predict.form.street_count} error={errors.num_streets?.message} htmlFor="num_streets">
            <select id="num_streets" {...fieldProps.numStreets}>
              <option value="1">{isAr ? 'شارع واحد' : 'One Street'}</option>
              <option value="2">{isAr ? 'شارعان' : 'Two Streets'}</option>
            </select>
          </Field>
          <Field label={t.predict.form.proximity} error={errors.proximity?.message} htmlFor="proximity">
            <select id="proximity" {...fieldProps.proximity}>
              <option value="قريب">{isAr ? 'قريب' : 'Close'}</option>
              <option value="متوسط">{isAr ? 'متوسط' : 'Medium'}</option>
              <option value="بعيد">{isAr ? 'بعيد' : 'Far'}</option>
            </select>
          </Field>
        </div>
        {message && <p className="text-xs font-semibold text-raboo3-600 dark:text-raboo3-400">{message}</p>}
        <div className="flex flex-wrap items-center gap-3">
          <button type="submit" className="btn btn-primary px-6 py-3 text-sm" aria-busy={submitting} disabled={submitting}>
            {submitting ? (isAr ? 'جارٍ التقدير…' : 'Valuing...') : t.predict.form.submit}
          </button>
          <button
            type="button"
            className="btn border border-black/10 bg-white/70 text-sm text-slate-600 hover:border-raboo3-400 dark:border-white/20 dark:bg-ink-900/60 dark:text-slate-200"
            onClick={() => {
              reset(defaultValues);
              setMessage(isAr ? 'تمت إعادة تعيين الحقول.' : 'Fields reset.');
            }}
          >
            {isAr ? 'إعادة تعيين' : 'Reset'}
          </button>
        </div>
      </form>
    </section>
  );
}

interface FieldProps {
  label: string;
  error?: string;
  className?: string;
  htmlFor?: string;
  children: React.ReactNode;
}

function Field({ label, error, className, htmlFor, children }: FieldProps) {
  return (
    <div className={clsx('space-y-2', className)}>
      <label className="text-sm font-medium text-ink-900 dark:text-white" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}
