'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useNotifications } from '@/contexts/NotificationContext';
import { useI18n, useT } from '@/i18n/useTranslations';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import type { CityKey } from '@/lib/geo';
import clsx from 'classnames';

const MapView = dynamic(() => import('@/components/MapView'), { ssr: false });

export default function AddLandPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const router = useRouter();
  const { addNotification } = useNotifications();
  const [formData, setFormData] = useState({
    city: 'الدمام' as CityKey,
    district: '',
    area: '',
    landUse: 'res' as 'res' | 'com' | 'inv',
    streetWidth: '',
    numStreets: '1' as '1' | '2',
    isCorner: false,
    description: '',
    price: '',
    coords: null as { lat: number; lng: number } | null,
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.district.trim()) {
      newErrors.district = isAr ? 'اسم الحي مطلوب' : 'District name is required';
    }
    if (!formData.area || Number(formData.area) < 50) {
      newErrors.area = isAr ? 'المساحة يجب أن تكون 50 م² على الأقل' : 'Area must be at least 50 sqm';
    }
    if (!formData.streetWidth || Number(formData.streetWidth) < 10) {
      newErrors.streetWidth = isAr ? 'عرض الشارع يجب أن يكون 10 م على الأقل' : 'Street width must be at least 10m';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) {
      addNotification({
        type: 'error',
        title: isAr ? 'خطأ في التحقق' : 'Validation Error',
        message: isAr ? 'يرجى تصحيح الأخطاء في النموذج' : 'Please correct the errors in the form',
        duration: 4000,
      });
      return;
    }

    setLoading(true);

    try {
      await new Promise((resolve) => setTimeout(resolve, 1500));

      addNotification({
        type: 'success',
        title: isAr ? 'تم الإضافة بنجاح' : 'Successfully Added',
        message: isAr ? 'تم إضافة معلومات الأرض بنجاح' : 'Land information added successfully',
        duration: 3000,
      });

      router.push(`/${locale}/predict`);
    } catch (error) {
      addNotification({
        type: 'error',
        title: isAr ? 'خطأ' : 'Error',
        message: isAr ? 'حدث خطأ أثناء إضافة المعلومات' : 'An error occurred while adding information',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="section min-h-screen bg-gradient-to-br from-slate-50 via-white to-raboo3-50/20 dark:from-ink-900 dark:via-ink-900 dark:to-raboo3-900/10" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container max-w-6xl">
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 space-y-3"
        >
          <h1 className="text-4xl font-extrabold text-ink-900 dark:text-white sm:text-5xl">
            {isAr ? 'إضافة معلومات أرض' : 'Add Land Information'}
          </h1>
          <p className="text-lg leading-relaxed text-slate-600 dark:text-slate-300 max-w-2xl">
            {isAr ? 'أضف معلومات قطعة الأرض الجديدة إلى قاعدة البيانات' : 'Add information for a new land parcel to the database'}
          </p>
        </motion.header>

        <div className="grid lg:grid-cols-2 gap-8">
          <motion.form
            initial={{ opacity: 0, x: isAr ? 20 : -20 }}
            animate={{ opacity: 1, x: 0 }}
            onSubmit={handleSubmit}
            className="card p-8 space-y-6"
          >
            <div className="space-y-1">
              <label className="block text-sm font-semibold text-ink-900 dark:text-white mb-2">
                {t.predict.form.city}
              </label>
              <select
                value={formData.city}
                onChange={(e) => setFormData({ ...formData, city: e.target.value as CityKey })}
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white transition-all"
              >
                <option value="الدمام">{t.predict.form.city_dammam}</option>
                <option value="الخبر">{t.predict.form.city_khobar}</option>
                <option value="الظهران">{t.predict.form.city_dhahran}</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="block text-sm font-semibold text-ink-900 dark:text-white mb-2">
                {t.predict.form.district} <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.district}
                onChange={(e) => {
                  setFormData({ ...formData, district: e.target.value });
                  if (errors.district) setErrors({ ...errors, district: '' });
                }}
                className={clsx(
                  'w-full px-4 py-3 rounded-xl border shadow-sm transition-all',
                  errors.district
                    ? 'border-red-300 focus:border-red-400 focus:ring-2 focus:ring-red-400/20'
                    : 'border-slate-200 focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700',
                  'bg-white text-ink-900 dark:bg-ink-900/50 dark:text-white'
                )}
                required
              />
              {errors.district && (
                <p className="text-xs text-red-600 dark:text-red-400 mt-1">{errors.district}</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="block text-sm font-semibold text-ink-900 dark:text-white mb-2">
                  {t.predict.form.area_sqm} <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  value={formData.area}
                  onChange={(e) => {
                    setFormData({ ...formData, area: e.target.value });
                    if (errors.area) setErrors({ ...errors, area: '' });
                  }}
                  min="50"
                  className={clsx(
                    'w-full px-4 py-3 rounded-xl border shadow-sm transition-all',
                    errors.area
                      ? 'border-red-300 focus:border-red-400 focus:ring-2 focus:ring-red-400/20'
                      : 'border-slate-200 focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700',
                    'bg-white text-ink-900 dark:bg-ink-900/50 dark:text-white'
                  )}
                  required
                />
                {errors.area && (
                  <p className="text-xs text-red-600 dark:text-red-400 mt-1">{errors.area}</p>
                )}
              </div>
              <div className="space-y-1">
                <label className="block text-sm font-semibold text-ink-900 dark:text-white mb-2">
                  {t.predict.form.street_width} <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  value={formData.streetWidth}
                  onChange={(e) => {
                    setFormData({ ...formData, streetWidth: e.target.value });
                    if (errors.streetWidth) setErrors({ ...errors, streetWidth: '' });
                  }}
                  min="10"
                  className={clsx(
                    'w-full px-4 py-3 rounded-xl border shadow-sm transition-all',
                    errors.streetWidth
                      ? 'border-red-300 focus:border-red-400 focus:ring-2 focus:ring-red-400/20'
                      : 'border-slate-200 focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700',
                    'bg-white text-ink-900 dark:bg-ink-900/50 dark:text-white'
                  )}
                  required
                />
                {errors.streetWidth && (
                  <p className="text-xs text-red-600 dark:text-red-400 mt-1">{errors.streetWidth}</p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="block text-sm font-semibold text-ink-900 dark:text-white mb-2">
                  {t.predict.form.street_count}
                </label>
                <select
                  value={formData.numStreets}
                  onChange={(e) => setFormData({ ...formData, numStreets: e.target.value as '1' | '2' })}
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white transition-all"
                >
                  <option value="1">1</option>
                  <option value="2">2</option>
                </select>
              </div>
              <div className="space-y-1">
                <label className="block text-sm font-semibold text-ink-900 dark:text-white mb-2">
                  {t.predict.form.land_use}
                </label>
                <select
                  value={formData.landUse}
                  onChange={(e) => setFormData({ ...formData, landUse: e.target.value as 'res' | 'com' | 'inv' })}
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white transition-all"
                >
                  <option value="res">{t.predict.form.land_use_res}</option>
                  <option value="com">{t.predict.form.land_use_com}</option>
                  <option value="inv">{t.predict.form.land_use_inv}</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-3 p-4 rounded-xl bg-slate-50 dark:bg-ink-900/50 border border-slate-200 dark:border-slate-700">
              <input
                id="corner"
                type="checkbox"
                checked={formData.isCorner}
                onChange={(e) => setFormData({ ...formData, isCorner: e.target.checked })}
                className="h-5 w-5 rounded border-slate-300 text-raboo3-600 focus:ring-raboo3-500"
              />
              <label htmlFor="corner" className="text-sm font-medium text-ink-900 dark:text-white cursor-pointer">
                {t.predict.form.is_corner}
              </label>
            </div>

            <div className="space-y-1">
              <label className="block text-sm font-semibold text-ink-900 dark:text-white mb-2">
                {isAr ? 'الوصف (اختياري)' : 'Description (Optional)'}
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={4}
                placeholder={isAr ? 'وصف إضافي عن قطعة الأرض...' : 'Additional description about the land parcel...'}
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400 transition-all resize-none"
              />
            </div>

            <div className="flex gap-4 pt-4">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 btn btn-primary py-4 text-base font-semibold shadow-lg shadow-raboo3-500/25 hover:shadow-xl"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="animate-spin">⏳</span>
                    {t.common.loading}
                  </span>
                ) : (
                  isAr ? 'إضافة الأرض' : 'Add Land'
                )}
              </button>
              <button
                type="button"
                onClick={() => router.back()}
                className="btn border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-ink-900/50 dark:text-slate-300 px-6"
              >
                {isAr ? 'إلغاء' : 'Cancel'}
              </button>
            </div>
          </motion.form>

          <motion.div
            initial={{ opacity: 0, x: isAr ? -20 : 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="space-y-6"
          >
            <div className="card p-0 overflow-hidden">
              <div className="p-4 bg-slate-50 dark:bg-ink-900/50 border-b border-slate-200 dark:border-slate-700">
                <h3 className="font-semibold text-ink-900 dark:text-white">
                  {isAr ? 'تحديد الموقع على الخريطة' : 'Select Location on Map'}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  {isAr ? 'انقر على الخريطة لتحديد موقع قطعة الأرض' : 'Click on the map to set the land parcel location'}
                </p>
              </div>
              <MapView
                city={formData.city}
                coords={formData.coords}
                onSelect={(coords) => setFormData({ ...formData, coords })}
              />
              {formData.coords && (
                <div className="p-4 bg-raboo3-50 dark:bg-raboo3-900/20 border-t border-slate-200 dark:border-slate-700">
                  <div className="text-sm text-raboo3-700 dark:text-raboo3-300">
                    <span className="font-semibold">{isAr ? 'الموقع المحدد:' : 'Selected Location:'}</span>{' '}
                    {formData.coords.lat.toFixed(6)}, {formData.coords.lng.toFixed(6)}
                  </div>
                </div>
              )}
            </div>

            <div className="card p-6 space-y-4">
              <h3 className="font-semibold text-ink-900 dark:text-white">
                {isAr ? 'نصائح' : 'Tips'}
              </h3>
              <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
                <li className="flex items-start gap-2">
                  <span className="text-raboo3-500 mt-0.5">✓</span>
                  <span>{isAr ? 'تأكد من دقة المعلومات المدخلة' : 'Ensure the accuracy of entered information'}</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-raboo3-500 mt-0.5">✓</span>
                  <span>{isAr ? 'حدد الموقع بدقة على الخريطة' : 'Set the location accurately on the map'}</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-raboo3-500 mt-0.5">✓</span>
                  <span>{isAr ? 'يمكنك إضافة وصف تفصيلي لاحقاً' : 'You can add detailed description later'}</span>
                </li>
              </ul>
            </div>
          </motion.div>
        </div>
      </div>
    </main>
  );
}
