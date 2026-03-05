'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { useI18n, useT } from '@/i18n/useTranslations';
import type { CityKey } from '@/lib/geo';
import SARIcon from '@/components/SARIcon';
import clsx from 'classnames';

export interface LandCardData {
  id: string;
  city: CityKey;
  district: string;
  area: number;
  landUse: 'res' | 'com' | 'inv';
  pricePerSqm?: number;
  totalPrice?: number;
  isCorner: boolean;
  numStreets: 1 | 2;
  coordinates: { lat: number; lng: number };
  description?: string;
}

interface LandCardProps {
  data: LandCardData;
  isSelected?: boolean;
  onHover?: () => void;
  onLeave?: () => void;
}

export default function LandCard({ data, isSelected, onHover, onLeave }: LandCardProps) {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';

  const landUseLabels = {
    res: t.predict.form.land_use_res,
    com: t.predict.form.land_use_com,
    inv: t.predict.form.land_use_inv,
  };

  const landUseColors = {
    res: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    com: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
    inv: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02 }}
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
      className={clsx(
        'card p-6 cursor-pointer transition-all duration-300',
        isSelected
          ? 'ring-2 ring-raboo3-500 shadow-xl'
          : 'hover:shadow-xl'
      )}
      dir={isAr ? 'rtl' : 'ltr'}
    >
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <h3 className="text-xl font-bold text-ink-900 dark:text-white">
                {data.district}
              </h3>
              <span className="px-3 py-1 text-xs font-semibold rounded-full bg-raboo3-100 text-raboo3-700 dark:bg-raboo3-900/30 dark:text-raboo3-300">
                {data.city}
              </span>
              <span className={clsx('px-3 py-1 text-xs font-semibold rounded-full', landUseColors[data.landUse])}>
                {landUseLabels[data.landUse]}
              </span>
            </div>
            {data.description && (
              <p className="text-sm text-slate-600 dark:text-slate-400 line-clamp-2">
                {data.description}
              </p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
              <span>📐</span>
              <span>{t.search.area}</span>
            </div>
            <div className="text-base font-bold text-ink-900 dark:text-white">
              {data.area.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} {t.predict.area_unit}
            </div>
          </div>

          {data.pricePerSqm && (
            <div className="space-y-1">
              <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                <span>💰</span>
                <span>{t.search.price_per_sqm}</span>
              </div>
              <div className="text-base font-bold text-ink-900 dark:text-white">
                {data.pricePerSqm.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} <SARIcon />
              </div>
            </div>
          )}

          {data.totalPrice && (
            <div className="space-y-1">
              <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                <span>💵</span>
                <span>{t.search.total_price}</span>
              </div>
              <div className="text-lg font-bold text-raboo3-600 dark:text-raboo3-400">
                {data.totalPrice.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} <SARIcon />
              </div>
            </div>
          )}

          <div className="space-y-1">
            <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
              <span>⭐</span>
              <span>{isAr ? 'الحالة' : 'Status'}</span>
            </div>
            <div className="text-sm font-semibold text-ink-900 dark:text-white">
              {data.isCorner && (isAr ? 'زاوية' : 'Corner')}
              {data.numStreets === 2 && (isAr ? ' • شارعان' : ' • Two Streets')}
              {!data.isCorner && data.numStreets === 1 && (isAr ? 'شارع واحد' : 'One Street')}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-slate-200 dark:border-slate-700">
          <div className="text-xs text-slate-500 dark:text-slate-400">
            <span className="flex items-center gap-1">
              <span>📍</span>
              <span>
                {data.coordinates.lat.toFixed(4)}, {data.coordinates.lng.toFixed(4)}
              </span>
            </span>
          </div>
          <div className="flex gap-2">
            <Link
              href={`/${locale}/parcel/${data.id}`}
              className="btn btn-primary text-sm px-4 py-2"
              onClick={(e) => e.stopPropagation()}
            >
              {t.search.view_details}
            </Link>
            <Link
              href={`/${locale}/predict?city=${data.city}&district=${data.district}`}
              className="btn border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-ink-900/50 dark:text-slate-300 text-sm px-4 py-2"
              onClick={(e) => e.stopPropagation()}
            >
              {isAr ? 'تقدير' : 'Estimate'}
            </Link>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

