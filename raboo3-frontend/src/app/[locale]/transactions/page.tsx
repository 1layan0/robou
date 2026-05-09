'use client';

import { useState, useEffect, useMemo } from 'react';
import { useI18n, useT } from '@/i18n/useTranslations';
import { motion } from 'framer-motion';
import SARIcon from '@/components/SARIcon';
import { translateCity, translateDistrict } from '@/lib/translateLocations';

interface SaleRow {
  city_ar: string;
  district_ar: string;
  year: number;
  quarter: number;
  property_type_ar: string;
  price_per_sqm: number;
  price_total?: number;
  area_sqm?: number;
}

const CITIES = ['الدمام', 'الخبر', 'الظهران'];

export default function TransactionsPage() {
  const t = useT();
  const { locale } = useI18n();
  const isAr = locale === 'ar';
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<SaleRow[]>([]);
  const [page, setPage] = useState(1);
  const [filterCity, setFilterCity] = useState<string>('');
  const [filterDistrict, setFilterDistrict] = useState<string>('');
  const [filterType, setFilterType] = useState<string>('');
  const rowsPerPage = 20;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch('/api/deals?limit=1000')
      .then((res) => {
        if (!res.ok) {
          if (res.status === 404 || res.status === 503) return { transactions: [] };
          return res.json().then((b) => Promise.reject(new Error(b?.error || res.statusText)));
        }
        return res.json();
      })
      .then((data: { transactions?: SaleRow[] }) => {
        if (cancelled) return;
        setRows(Array.isArray(data?.transactions) ? data.transactions : []);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e?.message || t.transactions.error_api);
        setRows([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [t.transactions.error_api]);

  const latestYear = useMemo(() => {
    const yearsSet = new Set<number>();
    rows.forEach((r) => {
      if (typeof r.year === 'number') yearsSet.add(r.year);
    });
    const yearsArr = Array.from(yearsSet).sort((a, b) => b - a);
    return yearsArr[0];
  }, [rows]);

  const latestRows = useMemo(
    () => (latestYear ? rows.filter((r) => r.year === latestYear) : rows),
    [rows, latestYear],
  );

  const { districts, propertyTypes } = useMemo(() => {
    const subset = filterCity ? latestRows.filter((r) => r.city_ar === filterCity) : latestRows;
    const districtSet = new Set<string>();
    const typeSet = new Set<string>();
    subset.forEach((r) => {
      districtSet.add(r.district_ar);
      typeSet.add(r.property_type_ar);
    });
    return {
      districts: Array.from(districtSet).sort((a, b) => a.localeCompare(b, 'ar')),
      propertyTypes: Array.from(typeSet).sort((a, b) => a.localeCompare(b, 'ar')),
    };
  }, [latestRows, filterCity]);

  const filteredRows = useMemo(() => {
    return latestRows.filter((r) => {
      if (filterCity && r.city_ar !== filterCity) return false;
      if (filterDistrict && r.district_ar !== filterDistrict) return false;
      if (filterType && r.property_type_ar !== filterType) return false;
      return true;
    });
  }, [latestRows, filterCity, filterDistrict, filterType]);

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / rowsPerPage));
  const start = (page - 1) * rowsPerPage;
  const pageRows = filteredRows.slice(start, start + rowsPerPage);

  const hasActiveFilters = filterCity || filterDistrict || filterType;
  const clearFilters = () => {
    setFilterCity('');
    setFilterDistrict('');
    setFilterType('');
    setPage(1);
  };

  const formatType = (type: string) => {
    const trimmed = type.trim();
    if (locale !== 'en') return trimmed || type;
    switch (trimmed) {
      case 'قطعة أرض-سكنى':
        return 'Residential land';
      case 'قطعة أرض-تجارى':
        return 'Commercial land';
      case 'شقة':
        return 'Apartment';
      case 'فيلا':
        return 'Villa';
      default:
        return trimmed || type;
    }
  };

  useEffect(() => {
    setPage(1);
  }, [filterCity, filterDistrict, filterType]);

  return (
    <main className="container py-10 space-y-8" dir={isAr ? 'rtl' : 'ltr'}>
      <header className="space-y-3">
        <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl">
          {t.transactions.title}
        </h1>
        <p className="text-base leading-relaxed text-slate-600 dark:text-slate-300">
          {t.transactions.subtitle}
        </p>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {t.transactions.source_note}
        </p>
        <p className="text-xs font-medium text-raboo3-700 dark:text-raboo3-300">
          {isAr
            ? `تعرض هذه الصفحة أحدث الصفقات${latestYear ? ` (سنة ${latestYear})` : ''}.`
            : `This page shows the latest deals${latestYear ? ` (year ${latestYear})` : ''}.`}
        </p>
      </header>

      {loading ? (
        <div className="card p-8 text-center text-slate-500 dark:text-slate-400" aria-busy="true">
          {t.transactions.loading}
        </div>
      ) : error ? (
        <div className="card p-8 text-center text-red-600 dark:text-red-400">
          {error}
        </div>
      ) : rows.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="card p-12 text-center text-slate-500 dark:text-slate-400"
        >
          {t.transactions.no_data}
        </motion.div>
      ) : (
        <>
          <div className="card p-4 sm:p-6 space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm font-medium text-ink-700 dark:text-slate-300">
                {t.transactions.filter_by}
              </span>
              <select
                value={filterCity}
                onChange={(e) => { setFilterCity(e.target.value); setFilterDistrict(''); setFilterType(''); }}
                className="input w-auto min-w-[140px]"
                aria-label={t.transactions.city}
              >
                <option value="">{t.transactions.all_cities}</option>
                {CITIES.map((c) => (
                  <option key={c} value={c}>{translateCity(c, locale)}</option>
                ))}
              </select>
              <select
                value={filterDistrict}
                onChange={(e) => setFilterDistrict(e.target.value)}
                className="input w-auto min-w-[160px]"
                aria-label={t.transactions.district}
              >
                <option value="">{t.transactions.all_districts}</option>
                {districts.map((d) => (
                  <option key={d} value={d}>{translateDistrict(d, locale)}</option>
                ))}
              </select>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="input w-auto min-w-[180px]"
                aria-label={t.transactions.type}
              >
                <option value="">{t.transactions.all_types}</option>
                {propertyTypes.map((pt) => (
                  <option key={pt} value={pt}>{formatType(pt)}</option>
                ))}
              </select>
              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={clearFilters}
                  className="btn border border-slate-300 dark:border-ink-600 text-sm"
                >
                  {t.transactions.clear_filters}
                </button>
              )}
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {filteredRows.length.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} {t.transactions.results_count}
            </p>
          </div>

          {filteredRows.length === 0 ? (
            <div className="card p-12 text-center text-slate-500 dark:text-slate-400">
              {t.transactions.no_match_filters}
            </div>
          ) : (
          <>
          <div className="card p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left text-ink-900 dark:text-white">
                <thead className="bg-slate-100 dark:bg-ink-800 text-slate-600 dark:text-slate-300">
                  <tr>
                    <th className="px-4 py-3 font-semibold">{t.transactions.city}</th>
                    <th className="px-4 py-3 font-semibold">{t.transactions.district}</th>
                    <th className="px-4 py-3 font-semibold">{t.transactions.date}</th>
                    <th className="px-4 py-3 font-semibold">{t.transactions.area}</th>
                    <th className="px-4 py-3 font-semibold">{t.transactions.price}</th>
                    <th className="px-4 py-3 font-semibold">{t.transactions.price_per_sqm}</th>
                    <th className="px-4 py-3 font-semibold">{t.transactions.type}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-ink-700">
                  {pageRows.map((row, i) => (
                    <tr key={`${row.city_ar}-${row.district_ar}-${row.year}-${row.quarter}-${i}`} className="hover:bg-slate-50 dark:hover:bg-ink-800/50">
                      <td className="px-4 py-3">{translateCity(row.city_ar, locale)}</td>
                      <td className="px-4 py-3">{translateDistrict(row.district_ar, locale)}</td>
                      <td className="px-4 py-3">{row.year}</td>
                      <td className="px-4 py-3">
                        {row.area_sqm != null ? `${Number(row.area_sqm).toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} ${t.transactions.area_unit}` : '—'}
                      </td>
                      <td className="px-4 py-3">
                        {row.price_total != null ? <><span className="font-medium">{Number(row.price_total).toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')}</span> <SARIcon /></> : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <span className="font-medium">{Number(row.price_per_sqm).toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')}</span> <SARIcon />
                      </td>
                      <td className="px-4 py-3">{formatType(row.property_type_ar)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {t.transactions.page} {page} {t.transactions.page_of} {totalPages}
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="btn border border-slate-300 dark:border-ink-600 disabled:opacity-50"
                >
                  {t.transactions.prev}
                </button>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="btn border border-slate-300 dark:border-ink-600 disabled:opacity-50"
                >
                  {t.transactions.next}
                </button>
              </div>
            </div>
          )}
          </>
          )}
        </>
      )}
    </main>
  );
}
