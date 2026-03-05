'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useI18n, useT } from '@/i18n/useTranslations';

const PAGE_SIZE_OPTIONS = [10, 20, 50] as const;
const DEFAULT_PAGE_SIZE = 10;

type Deal = {
  Date?: string;
  Category?: string;
  DType?: string;
  Dtype?: string;
  Meter_price?: number;
  Deal_price?: number;
  Area?: number;
  State?: number;
  City?: string;
  Hai?: string;
  M566?: string;
  Unit?: string;
};

const CITIES = [
  { value: '', labelAr: 'جميع المدن', labelEn: 'All cities' },
  { value: 'الدمام', labelAr: 'الدمام', labelEn: 'Dammam' },
  { value: 'الخبر', labelAr: 'الخبر', labelEn: 'Khobar' },
  { value: 'الظهران', labelAr: 'الظهران', labelEn: 'Dhahran' },
] as const;

const CATEGORY_OPTIONS = [
  { value: '', labelAr: 'جميع التصنيفات', labelEn: 'All categories' },
  { value: 'سكني', labelAr: 'سكني', labelEn: 'Residential' },
  { value: 'تجاري', labelAr: 'تجاري', labelEn: 'Commercial' },
] as const;

const DISTRICT_OPTIONS = [
  { value: '', labelAr: 'جميع الأحياء', labelEn: 'All districts' },
  { value: 'الفيصلية', labelAr: 'الفيصلية', labelEn: 'Al Faisaliyah' },
  { value: 'الشاطئ', labelAr: 'الشاطئ', labelEn: 'Al Shati' },
  { value: 'المنطقة المركزية', labelAr: 'المنطقة المركزية', labelEn: 'Central' },
  { value: 'الربوة', labelAr: 'الربوة', labelEn: 'Al Rawdah' },
  { value: 'الدمام الندى', labelAr: 'الدمام الندى', labelEn: 'AlDmam AlNda' },
  { value: 'الراكة', labelAr: 'الراكة', labelEn: 'Al Rakah' },
  { value: 'الحزام الذهبي', labelAr: 'الحزام الذهبي', labelEn: 'Golden Belt' },
  { value: 'الجلوية', labelAr: 'الجلوية', labelEn: 'Al Jalawiya' },
  { value: 'النسيم', labelAr: 'النسيم', labelEn: 'Al Naseem' },
  { value: 'الظهران الشرقية', labelAr: 'الظهران الشرقية', labelEn: 'Dhahran East' },
  { value: 'الظهران الغربية', labelAr: 'الظهران الغربية', labelEn: 'Dhahran West' },
] as const;

/** للفلترة: قبول الاسم العربي أو الإنجليزي للمدينة */
const CITY_ALIASES: Record<string, string[]> = {
  'الدمام': ['الدمام', 'Dammam'],
  'الخبر': ['الخبر', 'Khobar'],
  'الظهران': ['الظهران', 'Dhahran'],
};
function matchCity(rowCity: string | undefined, filterValue: string): boolean {
  if (!filterValue) return true;
  const aliases = CITY_ALIASES[filterValue];
  if (!aliases) return rowCity === filterValue;
  return !!rowCity && aliases.includes(rowCity);
}

/** قيم التصنيف التي تعتبر سكني أو تجاري (للفلترة) */
const CATEGORY_RESIDENTIAL = new Set(['سكني', 'Residential', 'Land-Residential', 'قطعة أرض سكني']);
const CATEGORY_COMMERCIAL = new Set(['تجاري', 'Commercial', 'Land-Commercial', 'قطعة أرض تجاري']);

function matchCategory(row: Deal, filterValue: string): boolean {
  if (!filterValue) return true;
  const cat = (row.Category ?? '').trim();
  const dtype = (row.DType ?? row.Dtype ?? '').trim();
  if (filterValue === 'سكني') return CATEGORY_RESIDENTIAL.has(cat) || CATEGORY_RESIDENTIAL.has(dtype);
  if (filterValue === 'تجاري') return CATEGORY_COMMERCIAL.has(cat) || CATEGORY_COMMERCIAL.has(dtype);
  return true;
}

/** للفلترة: قبول الاسم العربي أو الإنجليزي للحي */
const DISTRICT_ALIASES: Record<string, string[]> = {
  'الفيصلية': ['الفيصلية', 'Al Faisaliyah', 'Al Faisaliya'],
  'الشاطئ': ['الشاطئ', 'Al Shati'],
  'المنطقة المركزية': ['المنطقة المركزية', 'Central'],
  'الربوة': ['الربوة', 'Al Rawdah', 'Rawdah'],
  'الدمام الندى': ['الدمام الندى', 'AlDmam AlNda'],
  'الراكة': ['الراكة', 'Al Rakah', 'Rakah'],
  'الحزام الذهبي': ['الحزام الذهبي', 'Golden Belt'],
  'الجلوية': ['الجلوية', 'Al Jalawiya', 'Jalawiya'],
  'النسيم': ['النسيم', 'Al Naseem', 'Naseem'],
  'الظهران الشرقية': ['الظهران الشرقية', 'Dhahran East'],
  'الظهران الغربية': ['الظهران الغربية', 'Dhahran West'],
};

function matchDistrict(row: Deal, filterValue: string): boolean {
  if (!filterValue) return true;
  const hai = (row.Hai ?? '').trim();
  if (!hai) return false;
  const aliases = DISTRICT_ALIASES[filterValue];
  if (!aliases) return hai === filterValue;
  return aliases.some((a) => a === hai || a.toLowerCase() === hai.toLowerCase());
}

/** تعريب العرض: المدينة، الحي، التصنيف، النوع عند الواجهة بالعربية */
const CITY_TO_AR: Record<string, string> = {
  Dammam: 'الدمام',
  Khobar: 'الخبر',
  Dhahran: 'الظهران',
};
const CATEGORY_TYPE_TO_AR: Record<string, string> = {
  'Land-Residential': 'سكني',
  'Land-Commercial': 'تجاري',
  Residential: 'سكني',
  Commercial: 'تجاري',
  سكني: 'سكني',
  تجاري: 'تجاري',
};
const DTYPE_TO_AR: Record<string, string> = {
  'Land-Residential': 'قطعة أرض سكني',
  'Land-Commercial': 'قطعة أرض تجاري',
  'قطعة أرض': 'قطعة أرض',
  'قطعة أرض سكني': 'قطعة أرض سكني',
  'قطعة أرض تجاري': 'قطعة أرض تجاري',
};
const DISTRICT_TO_AR: Record<string, string> = {
  'AlDmam AlNda': 'الدمام الندى',
  'Al Faisaliyah': 'الفيصلية',
  'Al Rakah': 'الراكة',
  'Dhahran East': 'الظهران الشرقية',
  'Al Shati': 'الشاطئ',
  'Golden Belt': 'الحزام الذهبي',
  'Dhahran West': 'الظهران الغربية',
  'Al Jalawiya': 'الجلوية',
};
function toArDisplay(isAr: boolean, value: string | undefined, map: Record<string, string>): string {
  if (!value || !isAr) return value || '—';
  const trimmed = value.trim();
  return map[trimmed] ?? map[trimmed as keyof typeof map] ?? trimmed;
}
function cityAr(isAr: boolean, city: string | undefined): string {
  return toArDisplay(isAr, city, CITY_TO_AR) || city || '—';
}
function districtAr(isAr: boolean, hai: string | undefined): string {
  return toArDisplay(isAr, hai, DISTRICT_TO_AR) || hai || '—';
}
function categoryAr(isAr: boolean, cat: string | undefined, dtype: string | undefined): string {
  if (!isAr) return [cat, dtype].filter(Boolean).join(' / ') || '—';
  const c = toArDisplay(true, cat, CATEGORY_TYPE_TO_AR);
  const d = toArDisplay(true, dtype, DTYPE_TO_AR);
  if (c && d) return `${c} / ${d}`;
  if (d) return d;
  if (c) return c;
  return [cat, dtype].filter(Boolean).join(' / ') || '—';
}

/** بيانات تجريبية عند عدم وجود مفتاح API */
const MOCK_DEALS: Deal[] = [
  { Date: '2025-02-15', City: 'الدمام', Hai: 'الفيصلية', Category: 'سكني', DType: 'قطعة أرض', Area: 450, Deal_price: 1250000, Meter_price: 2778 },
  { Date: '2025-02-14', City: 'الخبر', Hai: 'الراكة', Category: 'سكني', DType: 'قطعة أرض', Area: 600, Deal_price: 2100000, Meter_price: 3500 },
  { Date: '2025-02-12', City: 'الظهران', Hai: 'الظهران الشرقية', Category: 'سكني', DType: 'قطعة أرض', Area: 380, Deal_price: 950000, Meter_price: 2500 },
  { Date: '2025-02-10', City: 'الدمام', Hai: 'الشاطئ', Category: 'تجاري', DType: 'قطعة أرض', Area: 520, Deal_price: 1560000, Meter_price: 3000 },
  { Date: '2025-02-08', City: 'الخبر', Hai: 'الحزام الذهبي', Category: 'سكني', DType: 'قطعة أرض', Area: 700, Deal_price: 2800000, Meter_price: 4000 },
];

export default function TransactionsPage() {
  const t = useT();
  const { locale } = useI18n();
  const isAr = locale === 'ar';
  const [cityFilter, setCityFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [districtFilter, setDistrictFilter] = useState('');
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<'api' | 'file' | 'mock'>('api');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(deals.length / pageSize)), [deals.length, pageSize]);
  const paginatedDeals = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return deals.slice(start, start + pageSize);
  }, [deals, currentPage, pageSize]);

  useEffect(() => {
    setCurrentPage(1);
  }, [cityFilter, categoryFilter, districtFilter]);

  useEffect(() => {
    setCurrentPage(1);
  }, [pageSize]);

  useEffect(() => {
    if (currentPage > totalPages) setCurrentPage(totalPages);
  }, [totalPages, currentPage]);

  const fetchDeals = useCallback(async () => {
    setLoading(true);
    setError(null);
    setDataSource('api');
    try {
      const res = await fetch('/api/deals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          state: 4,
          ...(cityFilter && { city: cityFilter }),
          ...(categoryFilter && { category: categoryFilter }),
          ...(districtFilter && { hai: districtFilter }),
          calendar: 'gregorian',
        }),
      });
      const data = await res.json();
      if (data.Error_code !== 0) {
        const isNoKey = data.no_api_key || (data.Error_msg && String(data.Error_msg).toLowerCase().includes('api key'));
        setError(isNoKey ? t.transactions.no_api_key : (data.Error_msg || t.transactions.error_api));
        if (isNoKey) {
          try {
            const fileRes = await fetch('/data/transactions.json');
            if (fileRes.ok) {
              const fileData = await fileRes.json();
              const list = Array.isArray(fileData) ? fileData : [];
              let filtered = cityFilter ? list.filter((d: Deal) => matchCity(d.City, cityFilter)) : list;
              filtered = categoryFilter ? filtered.filter((d: Deal) => matchCategory(d, categoryFilter)) : filtered;
              filtered = districtFilter ? filtered.filter((d: Deal) => matchDistrict(d, districtFilter)) : filtered;
              if (filtered.length > 0) {
                setDeals(filtered);
                setDataSource('file');
                setError(null);
              } else {
                let fallback = cityFilter ? MOCK_DEALS.filter((d) => d.City === cityFilter) : MOCK_DEALS;
                fallback = categoryFilter ? fallback.filter((d) => matchCategory(d, categoryFilter)) : fallback;
                fallback = districtFilter ? fallback.filter((d) => matchDistrict(d, districtFilter)) : fallback;
                setDeals(fallback);
                setDataSource('mock');
              }
            } else {
              let fallback = cityFilter ? MOCK_DEALS.filter((d) => d.City === cityFilter) : MOCK_DEALS;
              fallback = categoryFilter ? fallback.filter((d) => matchCategory(d, categoryFilter)) : fallback;
              fallback = districtFilter ? fallback.filter((d) => matchDistrict(d, districtFilter)) : fallback;
              setDeals(fallback);
              setDataSource('mock');
            }
          } catch {
            let fallback = cityFilter ? MOCK_DEALS.filter((d) => d.City === cityFilter) : MOCK_DEALS;
            fallback = categoryFilter ? fallback.filter((d) => matchCategory(d, categoryFilter)) : fallback;
            fallback = districtFilter ? fallback.filter((d) => matchDistrict(d, districtFilter)) : fallback;
            setDeals(fallback);
            setDataSource('mock');
          }
        } else {
          setDeals([]);
        }
      } else {
        setDeals(Array.isArray(data.Deals_list) ? data.Deals_list : []);
      }
    } catch {
      setError(t.transactions.error_api);
      setDeals([]);
    } finally {
      setLoading(false);
    }
  }, [cityFilter, categoryFilter, districtFilter, t.transactions.error_api, t.transactions.no_api_key]);

  useEffect(() => {
    fetchDeals();
  }, [fetchDeals]);

  const formatPrice = (n: number) =>
    isAr ? `${n.toLocaleString('ar-SA')} ر.س` : `${n.toLocaleString('en')} SAR`;
  const formatDate = (d: string) => {
    if (!d) return '—';
    const parts = d.split('/');
    if (parts.length >= 3) {
      const [day, month, year] = parts;
      const date = new Date(`${year}-${month}-${day}`);
      if (!isNaN(date.getTime()))
        return isAr ? d : date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
    }
    return d;
  };

  return (
    <main className="section min-h-screen py-12" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container max-w-6xl mx-auto px-4">
        <header className="mb-8">
          <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white">
            {t.transactions.title}
          </h1>
          <p className="mt-2 text-slate-600 dark:text-slate-300">
            {t.transactions.subtitle}
          </p>
        </header>

        <div className="mb-6 flex flex-wrap items-center gap-4">
          <label className="text-sm font-medium text-ink-900 dark:text-white">
            {t.transactions.city}:
          </label>
          <select
            value={cityFilter}
            onChange={(e) => setCityFilter(e.target.value)}
            className="rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-ink-800 text-ink-900 dark:text-white py-2 ps-4 pe-10 text-sm focus:ring-2 focus:ring-raboo3-400 focus:border-raboo3-400 appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%236b7280%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] bg-[length:1.25rem] bg-[right_0.5rem_center] bg-no-repeat dark:bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%239ca3af%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] rtl:bg-[right_auto] rtl:bg-[left_0.5rem_center]"
          >
            {CITIES.map((c) => (
              <option key={c.value || 'all'} value={c.value}>
                {isAr ? c.labelAr : c.labelEn}
              </option>
            ))}
          </select>
          <label className="text-sm font-medium text-ink-900 dark:text-white ms-2">
            {t.transactions.category}:
          </label>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-ink-800 text-ink-900 dark:text-white py-2 ps-4 pe-10 text-sm focus:ring-2 focus:ring-raboo3-400 focus:border-raboo3-400 appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%236b7280%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] bg-[length:1.25rem] bg-[right_0.5rem_center] bg-no-repeat dark:bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%239ca3af%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] rtl:bg-[right_auto] rtl:bg-[left_0.5rem_center]"
          >
            {CATEGORY_OPTIONS.map((opt) => (
              <option key={opt.value || 'all'} value={opt.value}>
                {isAr ? opt.labelAr : opt.labelEn}
              </option>
            ))}
          </select>
          <label className="text-sm font-medium text-ink-900 dark:text-white ms-2">
            {t.transactions.district}:
          </label>
          <select
            value={districtFilter}
            onChange={(e) => setDistrictFilter(e.target.value)}
            className="rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-ink-800 text-ink-900 dark:text-white py-2 ps-4 pe-10 text-sm focus:ring-2 focus:ring-raboo3-400 focus:border-raboo3-400 appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%236b7280%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] bg-[length:1.25rem] bg-[right_0.5rem_center] bg-no-repeat dark:bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%239ca3af%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] rtl:bg-[right_auto] rtl:bg-[left_0.5rem_center]"
          >
            {DISTRICT_OPTIONS.map((opt) => (
              <option key={opt.value || 'all'} value={opt.value}>
                {isAr ? opt.labelAr : opt.labelEn}
              </option>
            ))}
          </select>
        </div>

        {error && dataSource !== 'file' && (
          <div
            className={`mb-6 rounded-xl border px-4 py-3 text-sm ${
              dataSource === 'mock'
                ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200'
                : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300'
            }`}
          >
            {error}
          </div>
        )}

        <div className="rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden bg-white dark:bg-ink-900/50 shadow-sm">
          {loading ? (
            <div className="p-12 text-center text-slate-500 dark:text-slate-400">
              {t.transactions.loading}
            </div>
          ) : deals.length === 0 ? (
            <div className="p-12 text-center text-slate-500 dark:text-slate-400">
              {t.transactions.no_data}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                    <th className="text-start py-4 px-4 font-semibold text-ink-900 dark:text-white">#</th>
                    <th className="text-start py-4 px-4 font-semibold text-ink-900 dark:text-white">
                      {t.transactions.date}
                    </th>
                    <th className="text-start py-4 px-4 font-semibold text-ink-900 dark:text-white">
                      {t.transactions.city}
                    </th>
                    <th className="text-start py-4 px-4 font-semibold text-ink-900 dark:text-white">
                      {t.transactions.district}
                    </th>
                    <th className="text-start py-4 px-4 font-semibold text-ink-900 dark:text-white">
                      {t.transactions.category}
                    </th>
                    <th className="text-end py-4 px-4 font-semibold text-ink-900 dark:text-white">
                      {t.transactions.area} ({t.transactions.area_unit})
                    </th>
                    <th className="text-end py-4 px-4 font-semibold text-ink-900 dark:text-white">
                      {t.transactions.price}
                    </th>
                    <th className="text-end py-4 px-4 font-semibold text-ink-900 dark:text-white">
                      {t.transactions.price_per_sqm}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedDeals.map((row, i) => {
                    const globalIndex = (currentPage - 1) * pageSize + i + 1;
                    return (
                      <tr
                        key={`${row.Date}-${row.City}-${row.Hai}-${row.Unit}-${globalIndex}`}
                        className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors"
                      >
                        <td className="py-3 px-4 text-slate-500 dark:text-slate-400">{globalIndex}</td>
                        <td className="py-3 px-4 text-ink-800 dark:text-slate-200">
                          {formatDate(row.Date ?? '')}
                        </td>
                        <td className="py-3 px-4 text-ink-800 dark:text-slate-200">{cityAr(isAr, row.City)}</td>
                        <td className="py-3 px-4 text-ink-800 dark:text-slate-200">{districtAr(isAr, row.Hai)}</td>
                        <td className="py-3 px-4 text-ink-800 dark:text-slate-200">
                          {categoryAr(isAr, row.Category, row.DType ?? row.Dtype)}
                        </td>
                        <td className="py-3 px-4 text-end text-ink-800 dark:text-slate-200">
                          {row.Area != null ? row.Area.toLocaleString(isAr ? 'ar-SA' : 'en') : '—'}
                        </td>
                        <td className="py-3 px-4 text-end font-medium text-ink-900 dark:text-white">
                          {row.Deal_price != null ? formatPrice(row.Deal_price) : '—'}
                        </td>
                        <td className="py-3 px-4 text-end text-raboo3-600 dark:text-raboo3-400 font-medium">
                          {row.Meter_price != null ? formatPrice(row.Meter_price) : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {!loading && deals.length > pageSize && (
            <div className="flex flex-wrap items-center justify-center gap-4 py-4 px-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/30">
              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage <= 1}
                className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-ink-800 text-ink-900 dark:text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                {t.transactions.prev}
              </button>
              <span className="text-sm text-slate-600 dark:text-slate-300">
                {t.transactions.page} {currentPage} {t.transactions.page_of} {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage >= totalPages}
                className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-ink-800 text-ink-900 dark:text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                {t.transactions.next}
              </button>
            </div>
          )}

          {!loading && deals.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 py-3 px-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50/30 dark:bg-slate-800/20">
              <label className="text-sm font-medium text-ink-700 dark:text-slate-300">
                {t.transactions.rows_per_page}:
              </label>
              <select
                value={pageSize}
                onChange={(e) => setPageSize(Number(e.target.value) as 10 | 20 | 50)}
                className="rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-ink-800 text-ink-900 dark:text-white py-2 ps-4 pe-10 text-sm focus:ring-2 focus:ring-raboo3-400 focus:border-raboo3-400 appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%236b7280%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] bg-[length:1.25rem] bg-[right_0.5rem_center] bg-no-repeat dark:bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%239ca3af%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] rtl:bg-[right_auto] rtl:bg-[left_0.5rem_center]"
              >
                {PAGE_SIZE_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
          {dataSource === 'file'
            ? t.transactions.source_from_file
            : dataSource === 'mock'
              ? (isAr ? 'البيانات أعلاه تجريبية. لتحميل بياناتك: شغّل سكربت excel_to_transactions_json.py ثم ضع الملف في frontend/public/data/transactions.json' : 'Data above is sample. To use your data: run excel_to_transactions_json.py and place output in frontend/public/data/transactions.json')
              : t.transactions.source_note}
        </p>
      </div>
    </main>
  );
}
