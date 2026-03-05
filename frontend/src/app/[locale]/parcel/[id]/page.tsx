'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { type CityKey } from '@/lib/geo';
import { useI18n, useT } from '@/i18n/useTranslations';
import SARIcon from '@/components/SARIcon';

const MapView = dynamic(() => import('@/components/MapView'), { ssr: false });

interface ParcelDetails {
  id: string;
  city: string;
  district: string;
  area: number;
  pricePerSqm: number;
  totalPrice: number;
  range: [number, number];
  coordinates: { lat: number; lng: number };
  landUse: 'سكني' | 'تجاري';
  streetWidth: number;
  numStreets: number;
  proximity: string;
  description: string;
  features: string[];
  nearbyFacilities: {
    name: string;
    type: string;
    distance: number;
  }[];
}

export default function ParcelDetailPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const params = useParams();
  const router = useRouter();
  const [parcel, setParcel] = useState<ParcelDetails | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mock data - replace with actual API call
    const mockParcel: ParcelDetails = {
      id: params.id as string,
      city: 'الدمام',
      district: 'الحسام',
      area: 450,
      pricePerSqm: 1850,
      totalPrice: 832500,
      range: [749250, 915750],
      coordinates: { lat: 26.453, lng: 50.087 },
      landUse: 'سكني',
      streetWidth: 20,
      numStreets: 2,
      proximity: 'قريب',
      description: 'قطعة أرض سكنية ممتازة في حي الحسام بمدينة الدمام. موقع استراتيجي قريب من الخدمات الأساسية.',
      features: [
        'موقع استراتيجي',
        'قريب من المدارس',
        'قريب من المراكز التجارية',
        'شوارع واسعة',
        'خدمات متوفرة',
      ],
      nearbyFacilities: [
        { name: 'مدرسة الحسام', type: 'تعليم', distance: 0.5 },
        { name: 'مركز صحي الحسام', type: 'صحة', distance: 0.8 },
        { name: 'سوق الحسام', type: 'تجاري', distance: 1.2 },
        { name: 'مسجد الحسام', type: 'ديني', distance: 0.6 },
      ],
    };

    setTimeout(() => {
      setParcel(mockParcel);
      setLoading(false);
    }, 500);
  }, [params.id]);

  if (loading) {
    return (
      <main className="section">
        <div className="container">
          <div className="card p-8">
            <div className="animate-pulse space-y-4">
              <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-1/3" />
              <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-2/3" />
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (!parcel) {
    return (
      <main className="section" dir={isAr ? 'rtl' : 'ltr'}>
        <div className="container">
          <div className="card p-8 text-center">
            <h2 className="text-2xl font-bold text-ink-900 dark:text-white mb-4">
              {t.parcel.not_found}
            </h2>
            <p className="text-slate-600 dark:text-slate-400 mb-4">{t.parcel.not_found_message}</p>
            <Link href={`/${locale}/predict`} className="btn btn-primary">
              {t.parcel.back_to_search}
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="section" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.back()}
              className="btn border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-ink-900/50 dark:text-slate-300"
            >
              {isAr ? '← رجوع' : '← Back'}
            </button>
            <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white">
              {parcel.district} - {parcel.city}
            </h1>
          </div>
          <Link
            href={`/${locale}/land/edit/${parcel.id}`}
            className="btn btn-primary"
          >
            {isAr ? 'تعديل' : 'Edit'}
          </Link>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <div className="card p-6 space-y-4">
              <h2 className="text-2xl font-bold text-ink-900 dark:text-white">{t.parcel.basic_info}</h2>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-1">
                  <div className="text-sm text-slate-600 dark:text-slate-400">{t.parcel.city}</div>
                  <div className="font-semibold text-ink-900 dark:text-white">{parcel.city}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-sm text-slate-600 dark:text-slate-400">{t.parcel.district}</div>
                  <div className="font-semibold text-ink-900 dark:text-white">{parcel.district}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-sm text-slate-600 dark:text-slate-400">{t.parcel.area}</div>
                  <div className="font-semibold text-ink-900 dark:text-white">
                    {parcel.area.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} {t.parcel.area_unit || 'م²'}
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="text-sm text-slate-600 dark:text-slate-400">{t.parcel.land_use}</div>
                  <div className="font-semibold text-ink-900 dark:text-white">{parcel.landUse}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-sm text-slate-600 dark:text-slate-400">{t.parcel.street_width}</div>
                  <div className="font-semibold text-ink-900 dark:text-white">
                    {parcel.streetWidth} {t.parcel.meters}
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="text-sm text-slate-600 dark:text-slate-400">{t.parcel.num_streets}</div>
                  <div className="font-semibold text-ink-900 dark:text-white">
                    {parcel.numStreets === 2 ? t.parcel.num_streets_two : t.parcel.num_streets_one}
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="text-sm text-slate-600 dark:text-slate-400">{t.parcel.proximity}</div>
                  <div className="font-semibold text-ink-900 dark:text-white">{parcel.proximity}</div>
                </div>
              </div>
            </div>

            <div className="card p-6 space-y-4">
              <h2 className="text-2xl font-bold text-ink-900 dark:text-white">{t.parcel.description}</h2>
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed">{parcel.description}</p>
            </div>

            <div className="card p-6 space-y-4">
              <h2 className="text-2xl font-bold text-ink-900 dark:text-white">{t.parcel.features}</h2>
              <ul className="grid gap-2 md:grid-cols-2">
                {parcel.features.map((feature, index) => (
                  <li key={index} className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
                    <span className="text-raboo3-600">✓</span>
                    {feature}
                  </li>
                ))}
              </ul>
            </div>

            <div className="card p-6 space-y-4">
              <h2 className="text-2xl font-bold text-ink-900 dark:text-white">{t.parcel.nearby_facilities}</h2>
              <div className="space-y-3">
                {parcel.nearbyFacilities.map((facility, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-ink-900/50"
                  >
                    <div>
                      <div className="font-semibold text-ink-900 dark:text-white">{facility.name}</div>
                      <div className="text-sm text-slate-600 dark:text-slate-400">{facility.type}</div>
                    </div>
                    <div className="text-sm font-semibold text-raboo3-600 dark:text-raboo3-400">
                      {facility.distance} كم
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="lg:col-span-1 space-y-6">
            <div className="card p-6 space-y-4 sticky top-24">
              <h2 className="text-xl font-bold text-ink-900 dark:text-white">{t.parcel.pricing}</h2>
              <div className="space-y-3">
                <div>
                  <div className="text-sm text-slate-600 dark:text-slate-400">{t.parcel.price_per_sqm}</div>
                  <div className="text-2xl font-bold text-ink-900 dark:text-white">
                    {parcel.pricePerSqm.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} <SARIcon />
                  </div>
                </div>
                <div>
                  <div className="text-sm text-slate-600 dark:text-slate-400">{t.parcel.total_price}</div>
                  <div className="text-3xl font-extrabold text-raboo3-600 dark:text-raboo3-400">
                    {parcel.totalPrice.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} <SARIcon />
                  </div>
                </div>
                <div>
                  <div className="text-sm text-slate-600 dark:text-slate-400">{t.parcel.expected_range}</div>
                  <div className="font-semibold text-ink-900 dark:text-white">
                    {parcel.range[0].toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} - {parcel.range[1].toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} <SARIcon />
                  </div>
                </div>
              </div>
              <Link href={`/${locale}/predict`} className="btn btn-primary w-full">
                {t.parcel.request_custom}
              </Link>
            </div>

            <div className="card p-0 overflow-hidden">
              <MapView
                city={parcel.city as CityKey}
                district={parcel.district}
                coords={parcel.coordinates}
              />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

