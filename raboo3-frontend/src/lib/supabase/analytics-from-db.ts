import type { SupabaseClient } from '@supabase/supabase-js';

/** يطابق services/recommender.py */
export const INSIGHTS_DEFAULT_PROPERTY_TYPE_AR = 'قطعة أرض-سكنى';

const ALLOWED_CITIES = new Set(['الدمام', 'الخبر', 'الظهران']);
const CITY_ORDER = ['الدمام', 'الخبر', 'الظهران'] as const;
const MAX_DISPLAY_GROWTH_PCT = 30;
const MIN_DISPLAY_GROWTH_PCT = -20;

const BAD_DISTRICTS = new Set(['أخرى', 'اخرى', 'غير محدد', 'غير معروف']);

export interface InsightsDistrictRow {
  district: string;
  city: string;
  avgPrice: number;
  transactions: number;
  growth: number;
  demand: number;
}

export interface CityStat {
  avgPrice: number;
  totalTransactions: number;
  avgGrowth: number;
  avgDemand: number;
}

export interface InsightsPayload {
  districts: InsightsDistrictRow[];
  cityStats: Record<string, CityStat>;
  meta: { year: number; quarter: number; property_type_ar: string };
}

export interface DealRow {
  city_ar: string;
  district_ar: string;
  year: number;
  quarter: number;
  property_type_ar: string;
  price_per_sqm: number;
  price_total: number | null;
  area_sqm: number | null;
}

function buildDemandIndex(dealsCounts: number[]): Map<number, number> {
  const cleaned = dealsCounts
    .map((v) => Math.max(0, Number(v) || 0))
    .filter((v) => Number.isFinite(v));
  const unique = Array.from(new Set(cleaned)).sort((a, b) => a - b);
  const out = new Map<number, number>();
  if (!unique.length) return out;
  if (unique.length === 1) {
    const only = unique[0];
    out.set(only, only > 0 ? 50 : 0);
    return out;
  }
  const denom = unique.length - 1;
  unique.forEach((value, idx) => {
    out.set(value, Math.round((idx / denom) * 1000) / 10);
  });
  return out;
}

/**
 * تحليلات من جداول Supabase (تجميع حي-ربع + نمو YoY)، بنفس شكل GET /insights في raboo3-ml.
 */
export async function fetchInsightsFromSupabase(
  supabase: SupabaseClient,
  propertyTypeAr?: string | null,
): Promise<InsightsPayload | null> {
  const prop = (propertyTypeAr || INSIGHTS_DEFAULT_PROPERTY_TYPE_AR).trim();

  const { data: periodRow, error: periodErr } = await supabase
    .from('districtquarteraggregate')
    .select('year, quarter')
    .eq('property_type_ar', prop)
    .order('year', { ascending: false })
    .order('quarter', { ascending: false })
    .limit(1)
    .maybeSingle();

  if (periodErr || !periodRow) return null;

  const year = Number(periodRow.year);
  const quarter = Number(periodRow.quarter);

  const { data: aggRows, error: aggErr } = await supabase
    .from('districtquarteraggregate')
    .select('district_id, target_median_price_per_sqm, deals_count')
    .eq('property_type_ar', prop)
    .eq('year', year)
    .eq('quarter', quarter);

  if (aggErr || !aggRows?.length) return null;

  const districtIds = [...new Set(aggRows.map((r) => r.district_id))];

  const { data: districts, error: distErr } = await supabase
    .from('district')
    .select('district_id, city_ar, district_ar')
    .in('district_id', districtIds);

  if (distErr || !districts?.length) return null;

  const { data: growthRows } = await supabase
    .from('districtgrowthyoy')
    .select('district_id, yoy_growth_pct')
    .eq('property_type_ar', prop)
    .in('district_id', districtIds);

  const growthMap = new Map<number, number>();
  for (const g of growthRows || []) {
    growthMap.set(g.district_id, Number(g.yoy_growth_pct));
  }

  const dMap = new Map(districts.map((d) => [d.district_id, d]));
  const demandIndex = buildDemandIndex(aggRows.map((r) => Number(r.deals_count) || 0));

  const districtsOut: InsightsDistrictRow[] = [];
  for (const r of aggRows) {
    const d = dMap.get(r.district_id);
    if (!d) continue;
    const city = (d.city_ar || '').trim();
    if (!ALLOWED_CITIES.has(city)) continue;

    const deals = Math.max(0, Number(r.deals_count) || 0);
    const price = Number(r.target_median_price_per_sqm) || 0;
    const growth = growthMap.get(r.district_id) ?? 0;

    districtsOut.push({
      district: (d.district_ar || '').trim(),
      city,
      avgPrice: Math.round(price * 100) / 100,
      transactions: deals,
      growth: Math.round(growth * 100) / 100,
      demand: demandIndex.get(deals) ?? 0,
    });
  }

  districtsOut.sort(
    (a, b) => a.city.localeCompare(b.city, 'ar') || a.district.localeCompare(b.district, 'ar'),
  );

  const cityStats: Record<string, CityStat> = {};
  for (const c of CITY_ORDER) {
    const subset = districtsOut.filter((row) => row.city === c);
    if (!subset.length) {
      cityStats[c] = { avgPrice: 0, totalTransactions: 0, avgGrowth: 0, avgDemand: 0 };
      continue;
    }
    let avgGrowth = subset.reduce((s, row) => s + row.growth, 0) / subset.length;
    avgGrowth = Math.round(avgGrowth * 10) / 10;
    avgGrowth = Math.max(MIN_DISPLAY_GROWTH_PCT, Math.min(MAX_DISPLAY_GROWTH_PCT, avgGrowth));
    cityStats[c] = {
      avgPrice: Math.round(subset.reduce((s, row) => s + row.avgPrice, 0) / subset.length),
      totalTransactions: subset.reduce((s, row) => s + row.transactions, 0),
      avgGrowth,
      avgDemand: Math.round(subset.reduce((s, row) => s + row.demand, 0) / subset.length),
    };
  }

  return {
    districts: districtsOut,
    cityStats,
    meta: { year, quarter, property_type_ar: prop },
  };
}

/**
 * صفقات من RealSale + District، بنفس حقول استجابة GET /deals في raboo3-ml.
 */
export async function fetchDealsFromSupabase(
  supabase: SupabaseClient,
  limit: number,
): Promise<DealRow[] | null> {
  const lim = Math.min(Math.max(1, limit), 2000);

  const { data: sales, error: salesErr } = await supabase
    .from('realsale')
    .select('district_id, year, quarter, property_type_ar, price_per_sqm, price_total, area_sqm')
    .order('year', { ascending: false })
    .order('quarter', { ascending: false })
    .limit(lim);

  if (salesErr || !sales?.length) return null;

  const ids = [...new Set(sales.map((s) => s.district_id))];
  const { data: districts, error: dErr } = await supabase
    .from('district')
    .select('district_id, city_ar, district_ar')
    .in('district_id', ids);

  if (dErr || !districts?.length) return null;

  const dMap = new Map(districts.map((d) => [d.district_id, d]));
  const out: DealRow[] = [];

  for (const s of sales) {
    const d = dMap.get(s.district_id);
    if (!d) continue;
    const city = (d.city_ar || '').trim();
    const district = (d.district_ar || '').trim();
    if (!city || !district) continue;
    if (BAD_DISTRICTS.has(district)) continue;

    out.push({
      city_ar: city,
      district_ar: district,
      year: Number(s.year),
      quarter: Number(s.quarter),
      property_type_ar: (s.property_type_ar || '').trim(),
      price_per_sqm: Number(s.price_per_sqm) || 0,
      price_total: s.price_total != null ? Number(s.price_total) : null,
      area_sqm: s.area_sqm != null ? Number(s.area_sqm) : null,
    });
  }

  return out.length ? out : null;
}
