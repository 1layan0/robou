'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useNotifications } from '@/contexts/NotificationContext';
import { useI18n, useT } from '@/i18n/useTranslations';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import type { CityKey } from '@/lib/geo';

const MapView = dynamic(() => import('@/components/MapView'), { ssr: false });

export default function EditLandPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;
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
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    // Simulate fetching land data
    const fetchData = async () => {
      setFetching(true);
      await new Promise((resolve) => setTimeout(resolve, 1000));
      // Mock data
      setFormData({
        city: 'الدمام',
        district: 'حي الفيصلية',
        area: '500',
        landUse: 'res',
        streetWidth: '15',
        numStreets: '2',
        isCorner: true,
        description: isAr ? 'قطعة أرض سكنية في موقع ممتاز' : 'Residential land in excellent location',
        price: '1250000',
        coords: { lat: 26.392, lng: 50.196 },
      });
      setFetching(false);
    };
    fetchData();
  }, [id, isAr]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1500));

      addNotification({
        type: 'success',
        title: isAr ? 'تم التحديث بنجاح' : 'Successfully Updated',
        message: isAr ? 'تم تحديث معلومات الأرض بنجاح' : 'Land information updated successfully',
        duration: 3000,
      });

      router.push(`/${locale}/parcel/${id}`);
    } catch (error) {
      addNotification({
        type: 'error',
        title: isAr ? 'خطأ' : 'Error',
        message: isAr ? 'حدث خطأ أثناء تحديث المعلومات' : 'An error occurred while updating information',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  if (fetching) {
    return (
      <main className="container py-10" dir={isAr ? 'rtl' : 'ltr'}>
        <div className="max-w-4xl mx-auto">
          <div className="card p-8 text-center">
            <p>{t.common.loading}</p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="container py-10" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="max-w-4xl mx-auto">
        <header className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white">
                {isAr ? 'تعديل معلومات أرض' : 'Edit Land Details'}
              </h1>
              <p className="mt-2 text-slate-600 dark:text-slate-300">
                {isAr ? `تعديل معلومات قطعة الأرض #${id}` : `Edit land parcel #${id} information`}
              </p>
            </div>
            <Link
              href={`/${locale}/parcel/${id}`}
              className="btn border border-slate-200 dark:border-slate-700"
            >
              {isAr ? 'إلغاء' : 'Cancel'}
            </Link>
          </div>
        </header>

        <div className="grid lg:grid-cols-2 gap-6">
          <form onSubmit={handleSubmit} className="card p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">{t.predict.form.city}</label>
              <select
                value={formData.city}
                onChange={(e) => setFormData({ ...formData, city: e.target.value as CityKey })}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-ink-900"
              >
                <option value="الدمام">{t.predict.form.city_dammam}</option>
                <option value="الخبر">{t.predict.form.city_khobar}</option>
                <option value="الظهران">{t.predict.form.city_dhahran}</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">{t.predict.form.district}</label>
              <input
                type="text"
                value={formData.district}
                onChange={(e) => setFormData({ ...formData, district: e.target.value })}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-ink-900"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">{t.predict.form.area_sqm}</label>
                <input
                  type="number"
                  value={formData.area}
                  onChange={(e) => setFormData({ ...formData, area: e.target.value })}
                  className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-ink-900"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">{t.predict.form.street_width}</label>
                <input
                  type="number"
                  value={formData.streetWidth}
                  onChange={(e) => setFormData({ ...formData, streetWidth: e.target.value })}
                  className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-ink-900"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">{t.predict.form.land_use}</label>
              <select
                value={formData.landUse}
                onChange={(e) => setFormData({ ...formData, landUse: e.target.value as 'res' | 'com' | 'inv' })}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-ink-900"
              >
                <option value="res">{t.predict.form.land_use_res}</option>
                <option value="com">{t.predict.form.land_use_com}</option>
                <option value="inv">{t.predict.form.land_use_inv}</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                {isAr ? 'الوصف' : 'Description'}
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={4}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-ink-900"
              />
            </div>

            <div className="flex gap-4">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 btn btn-primary py-3"
              >
                {loading ? t.common.loading : (isAr ? 'حفظ التغييرات' : 'Save Changes')}
              </button>
              <Link
                href={`/${locale}/parcel/${id}`}
                className="btn border border-slate-200 dark:border-slate-700 px-6"
              >
                {isAr ? 'إلغاء' : 'Cancel'}
              </Link>
            </div>
          </form>

          <div className="card p-0 overflow-hidden">
            <MapView
              city={formData.city}
              coords={formData.coords}
              onSelect={(coords) => setFormData({ ...formData, coords })}
            />
          </div>
        </div>
      </div>
    </main>
  );
}

