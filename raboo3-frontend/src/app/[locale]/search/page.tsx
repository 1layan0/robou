'use client';

import { useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'framer-motion';
import { useNotifications } from '@/contexts/NotificationContext';
import { type CityKey } from '@/lib/geo';
import { CITIES } from '@/lib/cities';
import Link from 'next/link';
import { useI18n, useT } from '@/i18n/useTranslations';
import { translateCity, translateDistrict } from '@/lib/translateLocations';
import clsx from 'classnames';

const MapView = dynamic(() => import('@/components/MapView'), { ssr: false });

interface ParcelResult {
  id: string;
  city: CityKey;
  district: string;
  area: number;
  pricePerSqm: number;
  totalPrice: number;
  coordinates: { lat: number; lng: number };
  landUse: 'سكني' | 'تجاري';
  streetWidth: number;
  proximity: string;
}

export default function SearchPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const { addNotification } = useNotifications();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCity, setSelectedCity] = useState<CityKey | ''>('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [minArea, setMinArea] = useState('');
  const [maxArea, setMaxArea] = useState('');
  const [landUse, setLandUse] = useState<'سكني' | 'تجاري' | ''>('');
  const [results, setResults] = useState<ParcelResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedParcel, setSelectedParcel] = useState<ParcelResult | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim() && !selectedCity && !selectedDistrict) {
      addNotification({
        type: 'warning',
        title: isAr ? 'تنبيه' : 'Warning',
        message: isAr ? 'يرجى إدخال معايير البحث' : 'Please enter search criteria',
        duration: 3000,
      });
      return;
    }

    setLoading(true);
    
    setTimeout(() => {
      const mockResults: ParcelResult[] = [
        {
          id: '1',
          city: 'الدمام' as CityKey,
          district: 'الحسام',
          area: 450,
          pricePerSqm: 1850,
          totalPrice: 832500,
          coordinates: { lat: 26.453, lng: 50.087 },
          landUse: 'سكني' as 'سكني' | 'تجاري',
          streetWidth: 20,
          proximity: 'قريب',
        },
        {
          id: '2',
          city: 'الظهران' as CityKey,
          district: 'الحزام الذهبي',
          area: 600,
          pricePerSqm: 2200,
          totalPrice: 1320000,
          coordinates: { lat: 26.306, lng: 50.149 },
          landUse: 'تجاري' as 'سكني' | 'تجاري',
          streetWidth: 30,
          proximity: 'قريب',
        },
        {
          id: '3',
          city: 'الخبر' as CityKey,
          district: 'العقربية',
          area: 350,
          pricePerSqm: 1950,
          totalPrice: 682500,
          coordinates: { lat: 26.297, lng: 50.211 },
          landUse: 'سكني' as 'سكني' | 'تجاري',
          streetWidth: 15,
          proximity: 'متوسط',
        },
        {
          id: '4',
          city: 'الدمام' as CityKey,
          district: 'الفناتير',
          area: 520,
          pricePerSqm: 1980,
          totalPrice: 1029600,
          coordinates: { lat: 26.420, lng: 50.095 },
          landUse: 'سكني' as 'سكني' | 'تجاري',
          streetWidth: 25,
          proximity: 'قريب',
        },
        {
          id: '5',
          city: 'الخبر' as CityKey,
          district: 'الكورنيش',
          area: 380,
          pricePerSqm: 2100,
          totalPrice: 798000,
          coordinates: { lat: 26.280, lng: 50.220 },
          landUse: 'تجاري' as 'سكني' | 'تجاري',
          streetWidth: 30,
          proximity: 'قريب',
        },
      ].filter((parcel) => {
        if (selectedCity && parcel.city !== selectedCity) return false;
        if (selectedDistrict && !parcel.district.includes(selectedDistrict)) return false;
        if (minArea && parcel.area < Number(minArea)) return false;
        if (maxArea && parcel.area > Number(maxArea)) return false;
        if (landUse && parcel.landUse !== landUse) return false;
        if (searchQuery && !parcel.district.includes(searchQuery)) return false;
        return true;
      });

      setResults(mockResults);
      setLoading(false);
      
      if (mockResults.length === 0) {
        addNotification({
          type: 'info',
          title: t.search.no_results,
          message: isAr ? 'لم يتم العثور على قطع أراضي تطابق معايير البحث' : 'No land parcels found matching search criteria',
          duration: 4000,
        });
      } else {
        addNotification({
          type: 'success',
          title: isAr ? 'تم العثور على نتائج' : 'Results Found',
          message: t.search.results_found.replace('{count}', mockResults.length.toString()),
          duration: 3000,
        });
      }
    }, 1000);
  }, [searchQuery, selectedCity, selectedDistrict, minArea, maxArea, landUse, addNotification, isAr, t]);

  const resetFilters = () => {
    setSearchQuery('');
    setSelectedCity('');
    setSelectedDistrict('');
    setMinArea('');
    setMaxArea('');
    setLandUse('');
    setResults([]);
    setSelectedParcel(null);
  };

  return (
    <main className="section min-h-screen bg-gradient-to-br from-slate-50 via-white to-raboo3-50/20 dark:from-ink-900 dark:via-ink-900 dark:to-raboo3-900/10" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container space-y-8">
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="space-y-2">
              <h1 className="text-4xl font-extrabold text-ink-900 dark:text-white sm:text-5xl">
                {t.search.title}
              </h1>
              <p className="text-lg leading-relaxed text-slate-600 dark:text-slate-300 max-w-2xl">
                {t.search.subtitle}
              </p>
            </div>
            <Link
              href={`/${locale}/land/add`}
              className="btn btn-primary inline-flex items-center gap-2 px-6 py-3 shadow-lg shadow-raboo3-500/25 hover:shadow-xl hover:shadow-raboo3-500/30"
            >
              <span className="text-xl">+</span>
              {isAr ? 'إضافة أرض جديدة' : 'Add New Land'}
            </Link>
          </div>
        </motion.header>

        {/* Search Bar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card p-6"
        >
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <span className="absolute top-1/2 -translate-y-1/2 right-4 text-slate-400 text-xl">🔍</span>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder={isAr ? 'ابحث عن حي أو موقع...' : 'Search for district or location...'}
                className="w-full pl-4 pr-12 py-4 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={loading}
              className="btn btn-primary px-8 py-4 text-base font-semibold shadow-lg shadow-raboo3-500/25 hover:shadow-xl"
              aria-busy={loading}
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin">⏳</span>
                  {t.search.loading}
                </span>
              ) : (
                t.search.search_button
              )}
            </button>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={clsx(
                'btn px-4 py-4 border border-slate-200 dark:border-slate-700',
                showFilters && 'bg-raboo3-50 border-raboo3-300 dark:bg-raboo3-900/30'
              )}
              aria-label={isAr ? 'إظهار/إخفاء الفلاتر' : 'Toggle filters'}
            >
              <span className="text-xl">⚙️</span>
            </button>
          </div>

          {/* Advanced Filters */}
          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-700"
              >
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
                  <div className="space-y-2">
                    <label className="block text-sm font-semibold text-ink-900 dark:text-white">
                      {t.search.city}
                    </label>
                    <select
                      value={selectedCity}
                      onChange={(e) => setSelectedCity(e.target.value as CityKey | '')}
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white"
                    >
                      <option value="">{t.search.all_cities}</option>
                      {CITIES.map((city) => (
                        <option key={city} value={city}>
                          {city}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2">
                    <label className="block text-sm font-semibold text-ink-900 dark:text-white">
                      {t.search.district}
                    </label>
                    <input
                      type="text"
                      value={selectedDistrict}
                      onChange={(e) => setSelectedDistrict(e.target.value)}
                      placeholder={isAr ? 'اسم الحي' : 'District name'}
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="block text-sm font-semibold text-ink-900 dark:text-white">
                      {t.search.min_area}
                    </label>
                    <input
                      type="number"
                      value={minArea}
                      onChange={(e) => setMinArea(e.target.value)}
                      placeholder="50"
                      min="50"
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="block text-sm font-semibold text-ink-900 dark:text-white">
                      {t.search.max_area}
                    </label>
                    <input
                      type="number"
                      value={maxArea}
                      onChange={(e) => setMaxArea(e.target.value)}
                      placeholder="1000"
                      min="50"
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="block text-sm font-semibold text-ink-900 dark:text-white">
                      {t.search.land_use}
                    </label>
                    <select
                      value={landUse}
                      onChange={(e) => setLandUse(e.target.value as 'سكني' | 'تجاري' | '')}
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white"
                    >
                      <option value="">{t.search.all_types}</option>
                      <option value="سكني">{t.predict.form.land_use_res}</option>
                      <option value="تجاري">{t.predict.form.land_use_com}</option>
                    </select>
                  </div>
                </div>
                <div className="mt-4 flex justify-end">
                  <button
                    onClick={resetFilters}
                    className="btn border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-ink-900/50 dark:text-slate-300 px-4"
                  >
                    {t.search.reset}
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Results */}
        <AnimatePresence mode="wait">
          {results.length > 0 ? (
            <motion.div
              key="results"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid gap-6 lg:grid-cols-3"
            >
              <div className="lg:col-span-2 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-bold text-ink-900 dark:text-white">
                    {t.search.results_found.replace('{count}', results.length.toString())}
                  </h2>
                </div>
                {results.map((parcel, index) => (
                  <motion.div
                    key={parcel.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className={clsx(
                      'card p-6 cursor-pointer transition-all duration-300',
                      selectedParcel?.id === parcel.id
                        ? 'ring-2 ring-raboo3-500 shadow-xl'
                        : 'hover:shadow-xl hover:scale-[1.01]'
                    )}
                    onClick={() => setSelectedParcel(parcel)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 space-y-3">
                        <div className="flex items-center gap-3 flex-wrap">
                          <h3 className="text-xl font-bold text-ink-900 dark:text-white">
                            {translateDistrict(parcel.district, locale)}
                          </h3>
                          <span className="px-3 py-1 text-xs font-semibold rounded-full bg-raboo3-100 text-raboo3-700 dark:bg-raboo3-900/30 dark:text-raboo3-300">
                            {translateCity(parcel.city, locale)}
                          </span>
                          <span className={clsx(
                            'px-3 py-1 text-xs font-semibold rounded-full',
                            parcel.landUse === 'سكني'
                              ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                              : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                          )}>
                            {parcel.landUse}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div className="space-y-1">
                            <div className="text-xs text-slate-500 dark:text-slate-400">{t.search.area}</div>
                            <div className="text-base font-bold text-ink-900 dark:text-white">
                              {parcel.area.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} {t.predict.area_unit}
                            </div>
                          </div>
                          <div className="space-y-1">
                            <div className="text-xs text-slate-500 dark:text-slate-400">{t.search.price_per_sqm}</div>
                            <div className="text-base font-bold text-ink-900 dark:text-white">
                              {parcel.pricePerSqm.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} {t.predict.result.currency}
                            </div>
                          </div>
                          <div className="space-y-1">
                            <div className="text-xs text-slate-500 dark:text-slate-400">{t.search.total_price}</div>
                            <div className="text-lg font-bold text-raboo3-600 dark:text-raboo3-400">
                              {parcel.totalPrice.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} {t.predict.result.currency}
                            </div>
                          </div>
                          <div className="space-y-1">
                            <div className="text-xs text-slate-500 dark:text-slate-400">{t.predict.form.street_width}</div>
                            <div className="text-base font-semibold text-ink-900 dark:text-white">
                              {parcel.streetWidth} {t.parcel.meters}
                            </div>
                          </div>
                        </div>
                      </div>
                      <Link
                        href={`/${locale}/parcel/${parcel.id}`}
                        className="btn btn-primary text-sm px-5 py-2.5 whitespace-nowrap"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {t.search.view_details}
                      </Link>
                    </div>
                  </motion.div>
                ))}
              </div>

              {selectedParcel && (
                <motion.div
                  initial={{ opacity: 0, x: isAr ? 20 : -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="lg:col-span-1"
                >
                  <div className="card p-0 overflow-hidden sticky top-24">
                    <MapView
                      city={selectedParcel.city}
                      district={selectedParcel.district}
                      coords={selectedParcel.coordinates}
                    />
                    <div className="p-5 space-y-4 border-t border-slate-200 dark:border-slate-700">
                      <h4 className="font-bold text-lg text-ink-900 dark:text-white">
                        {isAr ? 'معلومات إضافية' : 'Additional Information'}
                      </h4>
                      <div className="space-y-3 text-sm">
                        <div className="flex justify-between">
                          <span className="text-slate-600 dark:text-slate-400">{t.predict.form.street_width}:</span>
                          <span className="font-semibold text-ink-900 dark:text-white">
                            {selectedParcel.streetWidth} {t.parcel.meters}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-600 dark:text-slate-400">{t.predict.form.proximity}:</span>
                          <span className="font-semibold text-ink-900 dark:text-white">
                            {selectedParcel.proximity}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </motion.div>
          ) : results.length === 0 && !loading ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="card p-12 text-center"
            >
              <div className="text-6xl mb-4">🔍</div>
              <h3 className="text-xl font-bold text-ink-900 dark:text-white mb-2">
                {t.search.no_results}
              </h3>
              <p className="text-slate-600 dark:text-slate-400">
                {isAr ? 'ابدأ البحث باستخدام المعايير أعلاه' : 'Start searching using the criteria above'}
              </p>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </main>
  );
}
