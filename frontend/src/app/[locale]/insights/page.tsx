'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useI18n, useT } from '@/i18n/useTranslations';
import { motion } from 'framer-motion';
import type { CityKey } from '@/lib/geo';
import SARIcon from '@/components/SARIcon';

const InsightsChart = dynamic(() => import('@/components/InsightsChart'), {
  ssr: false,
  loading: () => <div className="card shimmer h-72" aria-busy="true" />,
});

interface DistrictStats {
  district: string;
  city: CityKey;
  avgPrice: number;
  transactions: number;
  growth: number;
  demand: number;
}

interface CityStat {
  avgPrice: number;
  totalTransactions: number;
  avgGrowth: number;
  avgDemand: number;
}

const CITIES: CityKey[] = ['الدمام', 'الخبر', 'الظهران'];

export default function InsightsPage() {
  const t = useT();
  const { locale } = useI18n();
  const isAr = locale === 'ar';
  const [cityStats, setCityStats] = useState<Record<string, CityStat>>({});
  const [meta, setMeta] = useState<{ year?: number; quarter?: number }>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch('/api/insights')
      .then((res) => {
        if (!res.ok) return res.json().then((b) => Promise.reject(new Error(b?.error || res.statusText)));
        return res.json();
      })
      .then((data: { districts?: DistrictStats[]; cityStats?: Record<string, CityStat>; meta?: { year?: number; quarter?: number } }) => {
        if (cancelled) return;
        setCityStats(data.cityStats && typeof data.cityStats === 'object' ? data.cityStats : {});
        setMeta(data.meta && typeof data.meta === 'object' ? data.meta : {});
      })
      .catch((e) => {
        if (cancelled) return;
        const msg = e?.message || '';
        const isFetchFailed = /fetch failed|failed to fetch|network error/i.test(msg);
        setError(
          isFetchFailed
            ? (isAr
                ? 'تعذر الاتصال بالخادم. شغّلي الباك اند: من مجلد المشروع نفّذي: cd backend ثم pip install -r requirements.txt ثم uvicorn api.main:app --reload --port 8000'
                : 'Could not reach server. Run the backend: from project root run: cd backend, then pip install -r requirements.txt, then uvicorn api.main:app --reload --port 8000')
            : msg || (isAr ? 'فشل تحميل البيانات' : 'Failed to load data')
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const chartData = CITIES.map((city) => {
    const s = cityStats[city];
    return {
      city: city,
      avgPrice: s?.avgPrice ?? 0,
      demand: s?.avgDemand ?? 0,
    };
  }).filter((r) => r.avgPrice > 0 || r.demand > 0);

  if (loading) {
    return (
      <main className="container py-10 space-y-8" dir={isAr ? 'rtl' : 'ltr'}>
        <header className="space-y-3">
          <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl">
            {t.insights.title}
          </h1>
          <p className="text-base leading-relaxed text-slate-600 dark:text-slate-300">
            {t.insights.subtitle}
          </p>
        </header>
        <div className="card p-8 text-center text-slate-500 dark:text-slate-400" aria-busy="true">
          {t.common.loading}
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="container py-10 space-y-8" dir={isAr ? 'rtl' : 'ltr'}>
        <header className="space-y-3">
          <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl">
            {t.insights.title}
          </h1>
        </header>
        <div className="card p-8 text-center text-red-600 dark:text-red-400">
          {error}
        </div>
      </main>
    );
  }

  return (
    <main className="container py-10 space-y-8" dir={isAr ? 'rtl' : 'ltr'}>
      <header className="space-y-3">
        <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl">
          {t.insights.title}
        </h1>
        <p className="text-base leading-relaxed text-slate-600 dark:text-slate-300">
          {t.insights.subtitle}
        </p>
        {meta.year != null && meta.quarter != null && (
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {isAr ? `البيانات لأحدث فترة متاحة: ربع ${meta.quarter} ${meta.year}` : `Data for latest period: Q${meta.quarter} ${meta.year}`}
          </p>
        )}
      </header>

      {/* Statistics Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        {CITIES.map((city) => {
          const stats = cityStats[city];
          if (!stats) return null;
          return (
            <motion.div
              key={city}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="card p-6 space-y-4"
            >
              <h3 className="text-lg font-bold text-ink-900 dark:text-white">{city}</h3>
              <div className="space-y-3">
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">
                    {isAr ? 'متوسط السعر' : 'Avg Price'}
                  </div>
                  <div className="text-2xl font-bold text-raboo3-600 dark:text-raboo3-400">
                    {stats.avgPrice.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} <SARIcon />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      {isAr ? 'المعاملات' : 'Transactions'}
                    </div>
                    <div className="font-semibold text-ink-900 dark:text-white">{stats.totalTransactions}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      {isAr ? 'النمو' : 'Growth'}
                    </div>
                    <div className="font-semibold text-ink-900 dark:text-white">{stats.avgGrowth.toFixed(1)}%</div>
                  </div>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Chart */}
      <InsightsChart data={chartData} />
    </main>
  );
}
