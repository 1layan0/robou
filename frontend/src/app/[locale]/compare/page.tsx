'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { useI18n, useT } from '@/i18n/useTranslations';
import type { CityKey } from '@/lib/geo';
import SARIcon from '@/components/SARIcon';

const MapView = dynamic(() => import('@/components/MapView'), { ssr: false });

export default function ComparePage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const [region1, setRegion1] = useState<CityKey>('الدمام');
  const [region2, setRegion2] = useState<CityKey>('الخبر');

  const mockStats1 = {
    avgPrice: 2500,
    totalTransactions: 145,
    growthRate: 12.5,
    demandIndex: 85,
  };

  const mockStats2 = {
    avgPrice: 2800,
    totalTransactions: 132,
    growthRate: 8.3,
    demandIndex: 78,
  };

  return (
    <main className="section" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container space-y-8">
        <header className="space-y-3">
          <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl">
            {t.compare.title}
          </h1>
          <p className="text-base leading-relaxed text-slate-600 dark:text-slate-300">
            {t.compare.subtitle}
          </p>
        </header>

        <div className="grid gap-6 md:grid-cols-2">
          <div className="card p-6 space-y-4">
            <h2 className="text-xl font-bold text-ink-900 dark:text-white">{t.compare.region_1}</h2>
            <select
              value={region1}
              onChange={(e) => setRegion1(e.target.value as CityKey)}
              className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
            >
              <option value="الدمام">{t.predict.form.city_dammam}</option>
              <option value="الخبر">{t.predict.form.city_khobar}</option>
              <option value="الظهران">{t.predict.form.city_dhahran}</option>
            </select>

            <div className="space-y-3 pt-4 border-t border-slate-200 dark:border-slate-800">
              <div className="flex justify-between">
                <span className="text-slate-600 dark:text-slate-400">{t.compare.avg_price}:</span>
                <span className="font-semibold text-ink-900 dark:text-white">
                  {mockStats1.avgPrice.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} <SARIcon />
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600 dark:text-slate-400">{t.compare.transactions}:</span>
                <span className="font-semibold text-ink-900 dark:text-white">{mockStats1.totalTransactions}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600 dark:text-slate-400">{t.compare.growth_rate}:</span>
                <span className="font-semibold text-green-600 dark:text-green-400">+{mockStats1.growthRate}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600 dark:text-slate-400">{t.compare.demand_index}:</span>
                <span className="font-semibold text-ink-900 dark:text-white">{mockStats1.demandIndex}</span>
              </div>
            </div>
          </div>

          <div className="card p-6 space-y-4">
            <h2 className="text-xl font-bold text-ink-900 dark:text-white">{t.compare.region_2}</h2>
            <select
              value={region2}
              onChange={(e) => setRegion2(e.target.value as CityKey)}
              className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
            >
              <option value="الدمام">{t.predict.form.city_dammam}</option>
              <option value="الخبر">{t.predict.form.city_khobar}</option>
              <option value="الظهران">{t.predict.form.city_dhahran}</option>
            </select>

            <div className="space-y-3 pt-4 border-t border-slate-200 dark:border-slate-800">
              <div className="flex justify-between">
                <span className="text-slate-600 dark:text-slate-400">{t.compare.avg_price}:</span>
                <span className="font-semibold text-ink-900 dark:text-white">
                  {mockStats2.avgPrice.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} <SARIcon />
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600 dark:text-slate-400">{t.compare.transactions}:</span>
                <span className="font-semibold text-ink-900 dark:text-white">{mockStats2.totalTransactions}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600 dark:text-slate-400">{t.compare.growth_rate}:</span>
                <span className="font-semibold text-green-600 dark:text-green-400">+{mockStats2.growthRate}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600 dark:text-slate-400">{t.compare.demand_index}:</span>
                <span className="font-semibold text-ink-900 dark:text-white">{mockStats2.demandIndex}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <h2 className="text-xl font-bold text-ink-900 dark:text-white mb-4">{t.compare.comparison_summary}</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-ink-900/50 rounded-lg">
              <span className="text-slate-600 dark:text-slate-400">{t.compare.price_difference}:</span>
              <span className="font-semibold text-ink-900 dark:text-white">
                {((mockStats2.avgPrice - mockStats1.avgPrice) / mockStats1.avgPrice * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-ink-900/50 rounded-lg">
              <span className="text-slate-600 dark:text-slate-400">{t.compare.transaction_difference}:</span>
              <span className="font-semibold text-ink-900 dark:text-white">
                {mockStats1.totalTransactions - mockStats2.totalTransactions}
              </span>
            </div>
          </div>
        </div>

        <div className="card p-0 overflow-hidden" style={{ height: '500px' }}>
          <MapView city={region1} />
        </div>
      </div>
    </main>
  );
}

