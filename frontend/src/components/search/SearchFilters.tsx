'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useI18n, useT } from '@/i18n/useTranslations';
import type { CityKey } from '@/lib/geo';
import clsx from 'classnames';

interface SearchFiltersProps {
  onSubmit: (data: SearchFormData) => void;
  onReset: () => void;
  loading?: boolean;
}

export interface SearchFormData {
  city: CityKey | '';
  district: string;
  minArea: string;
  maxArea: string;
  landUse: 'res' | 'com' | 'inv' | '';
  minPrice: string;
  maxPrice: string;
}

export default function SearchFilters({ onSubmit, onReset, loading }: SearchFiltersProps) {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const [isExpanded, setIsExpanded] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SearchFormData>({
    defaultValues: {
      city: '',
      district: '',
      minArea: '',
      maxArea: '',
      landUse: '',
      minPrice: '',
      maxPrice: '',
    },
  });

  const handleFormSubmit = (data: SearchFormData) => {
    onSubmit(data);
  };

  const handleReset = () => {
    reset();
    onReset();
  };

  return (
    <div className="card p-6 space-y-6" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-ink-900 dark:text-white">
          {isAr ? 'بحث متقدم' : 'Advanced Search'}
        </h2>
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-sm text-slate-600 hover:text-ink-900 dark:text-slate-400 dark:hover:text-white flex items-center gap-2"
        >
          <span>{isAr ? (isExpanded ? 'إخفاء' : 'إظهار') : (isExpanded ? 'Hide' : 'Show')}</span>
          <span className="text-lg">{isExpanded ? '▲' : '▼'}</span>
        </button>
      </div>

      <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-ink-900 dark:text-white">
              {t.predict.form.city}
            </label>
            <select
              {...register('city')}
              className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white transition-all"
            >
              <option value="">{t.search.all_cities}</option>
              <option value="الدمام">{t.predict.form.city_dammam}</option>
              <option value="الخبر">{t.predict.form.city_khobar}</option>
              <option value="الظهران">{t.predict.form.city_dhahran}</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-semibold text-ink-900 dark:text-white">
              {t.predict.form.district}
            </label>
            <input
              type="text"
              {...register('district')}
              placeholder={isAr ? 'اسم الحي' : 'District name'}
              className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400 transition-all"
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-semibold text-ink-900 dark:text-white">
              {t.predict.form.land_use}
            </label>
            <select
              {...register('landUse')}
              className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white transition-all"
            >
              <option value="">{t.search.all_types}</option>
              <option value="res">{t.predict.form.land_use_res}</option>
              <option value="com">{t.predict.form.land_use_com}</option>
              <option value="inv">{t.predict.form.land_use_inv}</option>
            </select>
          </div>
        </div>

        {isExpanded && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 pt-4 border-t border-slate-200 dark:border-slate-700">
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-ink-900 dark:text-white">
                {isAr ? 'الحد الأدنى للمساحة (م²)' : 'Min Area (sqm)'}
              </label>
              <input
                type="number"
                {...register('minArea', { min: { value: 0, message: isAr ? 'يجب أن يكون أكبر من 0' : 'Must be greater than 0' } })}
                placeholder="50"
                min="0"
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400 transition-all"
              />
              {errors.minArea && (
                <p className="text-xs text-red-600 dark:text-red-400">{errors.minArea.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-semibold text-ink-900 dark:text-white">
                {isAr ? 'الحد الأعلى للمساحة (م²)' : 'Max Area (sqm)'}
              </label>
              <input
                type="number"
                {...register('maxArea', { min: { value: 0, message: isAr ? 'يجب أن يكون أكبر من 0' : 'Must be greater than 0' } })}
                placeholder="1000"
                min="0"
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400 transition-all"
              />
              {errors.maxArea && (
                <p className="text-xs text-red-600 dark:text-red-400">{errors.maxArea.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-semibold text-ink-900 dark:text-white">
                {isAr ? 'الحد الأدنى للسعر (ر.س)' : 'Min Price (SAR)'}
              </label>
              <input
                type="number"
                {...register('minPrice', { min: { value: 0, message: isAr ? 'يجب أن يكون أكبر من 0' : 'Must be greater than 0' } })}
                placeholder="100000"
                min="0"
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400 transition-all"
              />
              {errors.minPrice && (
                <p className="text-xs text-red-600 dark:text-red-400">{errors.minPrice.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-semibold text-ink-900 dark:text-white">
                {isAr ? 'الحد الأعلى للسعر (ر.س)' : 'Max Price (SAR)'}
              </label>
              <input
                type="number"
                {...register('maxPrice', { min: { value: 0, message: isAr ? 'يجب أن يكون أكبر من 0' : 'Must be greater than 0' } })}
                placeholder="5000000"
                min="0"
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-2 focus:ring-raboo3-400/20 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400 transition-all"
              />
              {errors.maxPrice && (
                <p className="text-xs text-red-600 dark:text-red-400">{errors.maxPrice.message}</p>
              )}
            </div>
          </div>
        )}

        <div className="flex items-center gap-3 pt-4">
          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary px-8 py-3 text-base font-semibold shadow-lg shadow-raboo3-500/25 hover:shadow-xl"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="animate-spin">⏳</span>
                {t.search.loading}
              </span>
            ) : (
              isAr ? 'ابحث الآن' : 'Search Now'
            )}
          </button>
          <button
            type="button"
            onClick={handleReset}
            className="btn border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-ink-900/50 dark:text-slate-300 px-6"
          >
            {t.search.reset}
          </button>
        </div>
      </form>
    </div>
  );
}

