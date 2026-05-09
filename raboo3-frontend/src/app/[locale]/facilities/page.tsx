'use client';

import { useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import { useNotifications } from '@/contexts/NotificationContext';
import { type CityKey } from '@/lib/geo';
import { CITIES } from '@/lib/cities';
import { useI18n, useT } from '@/i18n/useTranslations';
import { translateCity, translateDistrict } from '@/lib/translateLocations';

const MapView = dynamic(() => import('@/components/MapView'), { ssr: false });

interface Facility {
  id: string;
  name: string;
  type: 'مدرسة' | 'مستشفى' | 'سوق' | 'مسجد' | 'حديقة' | 'مطار' | 'جامعة' | 'مول';
  city: CityKey;
  district: string;
  coordinates: { lat: number; lng: number };
  distance?: number;
  rating?: number;
}

const facilityTypes = ['مدرسة', 'مستشفى', 'سوق', 'مسجد', 'حديقة', 'مطار', 'جامعة', 'مول'];

const mockFacilities: Facility[] = [
  { id: '1', name: 'مدرسة الحسام', type: 'مدرسة', city: 'الدمام', district: 'الحسام', coordinates: { lat: 26.455, lng: 50.089 } },
  { id: '2', name: 'مستشفى الملك فهد', type: 'مستشفى', city: 'الدمام', district: 'الفناتير', coordinates: { lat: 26.42, lng: 50.11 } },
  { id: '3', name: 'سوق الحسام', type: 'سوق', city: 'الدمام', district: 'الحسام', coordinates: { lat: 26.451, lng: 50.085 } },
  { id: '4', name: 'مسجد الحسام', type: 'مسجد', city: 'الدمام', district: 'الحسام', coordinates: { lat: 26.453, lng: 50.087 } },
  { id: '5', name: 'حديقة الملك فهد', type: 'حديقة', city: 'الدمام', district: 'الكورنيش', coordinates: { lat: 26.40, lng: 50.10 } },
  { id: '6', name: 'مطار الملك فهد', type: 'مطار', city: 'الظهران', district: 'المطار', coordinates: { lat: 26.265, lng: 50.152 } },
  { id: '7', name: 'جامعة الملك فهد', type: 'جامعة', city: 'الظهران', district: 'الظهران', coordinates: { lat: 26.31, lng: 50.14 } },
  { id: '8', name: 'مول الظهران', type: 'مول', city: 'الظهران', district: 'الحزام الذهبي', coordinates: { lat: 26.306, lng: 50.149 } },
];

export default function FacilitiesPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const { addNotification } = useNotifications();
  const [selectedCity, setSelectedCity] = useState<CityKey | ''>('');
  const [selectedType, setSelectedType] = useState<string>('');
  const [selectedFacility, setSelectedFacility] = useState<Facility | null>(null);
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(null);

  const filteredFacilities = mockFacilities.filter((facility) => {
    if (selectedCity && facility.city !== selectedCity) return false;
    if (selectedType && facility.type !== selectedType) return false;
    return true;
  });

  const handleGetLocation = useCallback(() => {
    if (!navigator.geolocation) {
      addNotification({
        type: 'error',
        title: isAr ? 'غير مدعوم' : 'Not Supported',
        message: isAr ? 'المتصفح لا يدعم تحديد الموقع' : 'Browser does not support geolocation',
        duration: 4000,
      });
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const coords = {
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        };
        setUserLocation(coords);
        addNotification({
          type: 'success',
          title: isAr ? 'تم تحديد الموقع' : 'Location Set',
          message: isAr ? 'سيتم حساب المسافات من موقعك' : 'Distances will be calculated from your location',
          duration: 3000,
        });
      },
      () => {
        addNotification({
          type: 'error',
          title: isAr ? 'فشل تحديد الموقع' : 'Location Failed',
          message: isAr ? 'يرجى السماح بالوصول إلى الموقع' : 'Please allow access to location',
          duration: 4000,
        });
      }
    );
  }, [addNotification]);

  const calculateDistance = (facility: Facility) => {
    if (!userLocation) return null;
    // Simple distance calculation (Haversine formula simplified)
    const R = 6371; // Earth radius in km
    const dLat = ((facility.coordinates.lat - userLocation.lat) * Math.PI) / 180;
    const dLon = ((facility.coordinates.lng - userLocation.lng) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((userLocation.lat * Math.PI) / 180) *
        Math.cos((facility.coordinates.lat * Math.PI) / 180) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return Math.round(R * c * 10) / 10;
  };

  return (
    <main className="section" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container space-y-8">
        <header className="space-y-3">
          <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl">
            {t.facilities.title}
          </h1>
          <p className="text-base leading-relaxed text-slate-600 dark:text-slate-300">
            {t.facilities.subtitle}
          </p>
        </header>

        <div className="card p-6 space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-ink-900 dark:text-white">
                {t.facilities.city}
              </label>
              <select
                value={selectedCity}
                onChange={(e) => setSelectedCity(e.target.value as CityKey | '')}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
              >
                <option value="">{t.facilities.all_cities}</option>
                {CITIES.map((city) => (
                  <option key={city} value={city}>
                    {city}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-ink-900 dark:text-white">
                {t.facilities.facility_type}
              </label>
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
              >
                <option value="">{t.facilities.all_types}</option>
                {facilityTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-ink-900 dark:text-white">
                {t.facilities.your_location}
              </label>
              <button
                onClick={handleGetLocation}
                className="w-full btn border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-ink-900/50 dark:text-slate-300"
              >
                {userLocation ? t.facilities.location_set : isAr ? 'تحديد موقعي' : 'Get My Location'}
              </button>
            </div>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-4">
            {filteredFacilities.length === 0 ? (
              <div className="card p-8 text-center">
                <p className="text-slate-600 dark:text-slate-400">
                  {isAr ? 'لا توجد مرافق تطابق المعايير' : 'No facilities match the criteria'}
                </p>
              </div>
            ) : (
              filteredFacilities.map((facility) => {
                const distance = calculateDistance(facility);
                return (
                  <motion.div
                    key={facility.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card p-6 cursor-pointer hover:shadow-xl transition-shadow"
                    onClick={() => setSelectedFacility(facility)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2">
                          <h3 className="text-lg font-bold text-ink-900 dark:text-white">
                            {facility.name}
                          </h3>
                          <span className="px-2 py-1 text-xs font-semibold rounded-full bg-raboo3-100 text-raboo3-700 dark:bg-raboo3-900/30 dark:text-raboo3-300">
                            {facility.type}
                          </span>
                        </div>
                        <div className="text-sm text-slate-600 dark:text-slate-400">
                          {translateDistrict(facility.district, locale)} - {translateCity(facility.city, locale)}
                        </div>
                        {distance && (
                          <div className="text-sm font-semibold text-raboo3-600 dark:text-raboo3-400">
                            {t.facilities.distance} {distance} {t.facilities.km}
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                );
              })
            )}
          </div>

          <div className="lg:col-span-1 space-y-6">
            {selectedFacility && (
              <div className="card p-6 space-y-4 sticky top-24">
                <h3 className="text-xl font-bold text-ink-900 dark:text-white">
                  {selectedFacility.name}
                </h3>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-slate-600 dark:text-slate-400">النوع:</span>
                    <span className="font-semibold text-ink-900 dark:text-white mr-2">
                      {selectedFacility.type}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-600 dark:text-slate-400">{isAr ? 'الموقع:' : 'Location:'}</span>
                    <span className="font-semibold text-ink-900 dark:text-white mr-2">
                      {translateDistrict(selectedFacility.district, locale)} - {translateCity(selectedFacility.city, locale)}
                    </span>
                  </div>
                  {userLocation && (
                    <div>
                      <span className="text-slate-600 dark:text-slate-400">{t.facilities.distance}</span>
                      <span className="font-semibold text-raboo3-600 dark:text-raboo3-400 mr-2">
                        {calculateDistance(selectedFacility)} {t.facilities.km}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="card p-0 overflow-hidden">
              <MapView
                city={selectedFacility?.city || selectedCity || 'الدمام'}
                district={selectedFacility?.district}
                coords={selectedFacility?.coordinates || userLocation}
              />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

