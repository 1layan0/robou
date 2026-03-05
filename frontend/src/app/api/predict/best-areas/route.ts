import { NextResponse } from 'next/server'
import { z } from 'zod'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const BodySchema = z.object({
  bbox: z.tuple([z.number(), z.number(), z.number(), z.number()]),
  land_use: z.enum(['سكني', 'تجاري']),
  proximity: z.enum(['قريب', 'متوسط', 'بعيد']).optional(),
  min_price_per_sqm: z.coerce.number().min(0).optional(),
  max_price_per_sqm: z.coerce.number().min(0).optional(),
  area_sqm: z.coerce.number().positive().optional(),
  top_n: z.coerce.number().int().min(1).max(5).optional(),
})

const ML_API_URL = (process.env.ML_API_URL ?? '').trim()

/** مسافة هافرساين بالكم بين نقطتين (درجات) */
function haversineKm(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLon = ((lon2 - lon1) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

/** نطاق الإحداثيات تقريباً للشرقية (الدمام/الخبر/الظهران) */
const KSA_EAST_LAT_MIN = 26.2
const KSA_EAST_LAT_MAX = 26.6
const KSA_EAST_LNG_MIN = 49.9
const KSA_EAST_LNG_MAX = 50.2

/** تأكد أن bbox بالترتيب [minLng, minLat, maxLng, maxLat]. إن وُجد (lat,lng) نصححه. */
function normalizeBbox(bbox: [number, number, number, number]): [number, number, number, number] {
  const [a, b, c, d] = bbox
  const aIsLat = a >= KSA_EAST_LAT_MIN && a <= KSA_EAST_LAT_MAX
  const bIsLng = b >= KSA_EAST_LNG_MIN && b <= KSA_EAST_LNG_MAX
  if (aIsLat && bIsLng && c >= KSA_EAST_LAT_MIN && c <= KSA_EAST_LAT_MAX && d >= KSA_EAST_LNG_MIN && d <= KSA_EAST_LNG_MAX) {
    return [Math.min(b, d), Math.min(a, c), Math.max(b, d), Math.max(a, c)]
  }
  return bbox
}

/** تحويل bbox [minLng, minLat, maxLng, maxLat] إلى مركز ونصف قطر بالكم */
function bboxToCenterAndRadius(bbox: [number, number, number, number]): {
  center_lat: number
  center_lon: number
  radius_km: number
} {
  const [minLng, minLat, maxLng, maxLat] = normalizeBbox(bbox)
  const center_lat = (minLat + maxLat) / 2
  const center_lon = (minLng + maxLng) / 2
  const corners: [number, number][] = [
    [minLat, minLng],
    [minLat, maxLng],
    [maxLat, minLng],
    [maxLat, maxLng],
  ]
  let radius_km = 0
  for (const [lat, lon] of corners) {
    const d = haversineKm(center_lat, center_lon, lat, lon)
    if (d > radius_km) radius_km = d
  }
  const minRadiusKm = 5
  return { center_lat, center_lon, radius_km: Math.min(100, Math.max(radius_km, minRadiusKm)) }
}

function landUseToPropertyType(land_use: 'سكني' | 'تجاري'): string {
  return land_use === 'سكني' ? 'قطعة أرض-سكنى' : 'قطعة أرض-تجارى'
}

type RecommendResult = {
  city_ar: string
  district_ar: string
  lat: number
  lon: number
  predicted_median_price_per_sqm: number
  score: number
  confidence?: 'high' | 'medium' | 'low'
  confidence_reason?: { deals_count: number; volatility: number }
  services_level?: 'high' | 'medium' | 'low'
  growth_trend?: 'up' | 'flat' | 'down'
  components?: Record<string, number>
  growth_component?: { growth_pct: number; source: string; confidence: string }
  reasons_ar: string[]
}

type BestAreaItem = {
  city: string
  district: string
  latitude: number
  longitude: number
  price_per_sqm: number
  growth_rate_pct: number
  reasons: string[]
  score?: number
  confidence?: 'high' | 'medium' | 'low'
  confidence_reason?: { deals_count: number; volatility: number }
  services_level?: 'high' | 'medium' | 'low'
  growth_trend?: 'up' | 'flat' | 'down'
  growth_component?: { growth_pct: number; source: string; confidence: string }
}

export async function POST(req: Request) {
  try {
    const json = await req.json().catch(() => ({}))
    const parsed = BodySchema.safeParse(json)
    if (!parsed.success) {
      return NextResponse.json(
        { error: 'بيانات غير مكتملة', details: parsed.error.flatten() },
        { status: 400 }
      )
    }
    const {
      bbox,
      land_use,
      proximity = 'قريب',
      min_price_per_sqm,
      max_price_per_sqm,
      area_sqm = 400,
      top_n = 3,
    } = parsed.data

    if (!ML_API_URL) {
      return NextResponse.json(
        { error: 'خدمة التقدير غير متوفرة. تحققي من إعدادات الخادم.' },
        { status: 503 }
      )
    }

    const baseUrl = ML_API_URL.replace(/\/$/, '')

    // 1) استدعاء /recommend/districts (الباك يستخدم أحدث ربع تلقائياً)
    const normalizedBbox = normalizeBbox(bbox)
    const { center_lat, center_lon, radius_km } = bboxToCenterAndRadius(normalizedBbox)

    let res = await fetch(`${baseUrl}/recommend/districts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        center_lat,
        center_lon,
        radius_km,
        city_ar: null,
        property_type_ar: landUseToPropertyType(land_use),
        top_k: top_n,
        min_price_per_sqm: min_price_per_sqm ?? undefined,
        max_price_per_sqm: max_price_per_sqm ?? undefined,
        proximity,
      }),
    })

    let data = (await res.json().catch(() => ({}))) as {
      results?: RecommendResult[]
      best_areas?: BestAreaItem[]
      primary?: BestAreaItem
      count_in_radius?: number
      note?: string
      detail?: string | string[]
      proximity_applied?: string
      mode_used?: string
      latest_year?: number
      latest_quarter?: number
      used_weights?: Record<string, number>
      services_mult?: number
      tie?: boolean
    }

    // 2) إذا 404 = الباك قديم ولا يحتوي على /recommend/districts → استدعاء /predict/best-areas (bbox)
    if (res.status === 404 && (data.detail === 'Not Found' || (typeof data.detail === 'string' && data.detail.includes('Not Found')))) {
      res = await fetch(`${baseUrl}/predict/best-areas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bbox: normalizedBbox,
          land_use,
          proximity,
          area_sqm,
          top_n,
        }),
      })
      data = (await res.json().catch(() => ({}))) as { best_areas?: BestAreaItem[]; primary?: BestAreaItem; detail?: string }
    }

    if (!res.ok) {
      const rawDetail =
        typeof data.detail === 'string'
          ? data.detail
          : Array.isArray(data.detail) && data.detail[0]
            ? String(data.detail[0])
            : ''
      const message =
        res.status === 404 && (rawDetail === 'Not Found' || !rawDetail)
          ? 'خدمة التقدير غير متاحة (404). أعدي تشغيل الباك من مجلد backend: uvicorn api.main:app --reload --port 8000'
          : (rawDetail || data.note) ?? 'لم نتمكن من تحديد أحياء في النطاق. ارسمي المستطيل فوق المنطقة الشرقية (الدمام، الخبر، الظهران).'
      return NextResponse.json({ error: message }, { status: res.status })
    }

    // استجابة من /recommend/districts (جديد)
    const results = Array.isArray(data.results) ? data.results : []
    if (results.length === 0) {
      return NextResponse.json({
        best_areas: [],
        primary: null,
        note: data.note ?? (data.count_in_radius === 0 ? 'لا توجد أحياء ضمن النطاق' : 'لا توجد أحياء ضمن نطاق السعر المحدد'),
        tie: false,
        mode_used: data.mode_used,
        latest_year: data.latest_year,
        latest_quarter: data.latest_quarter,
      })
    }
    if (results.length > 0) {
      const mapResult = (r: RecommendResult): BestAreaItem => ({
        city: r.city_ar,
        district: r.district_ar,
        latitude: r.lat,
        longitude: r.lon,
        price_per_sqm: r.predicted_median_price_per_sqm,
        growth_rate_pct: r.growth_component?.growth_pct ?? 0,
        reasons: r.reasons_ar ?? [],
        score: r.score,
        confidence: r.confidence,
        confidence_reason: r.confidence_reason,
        services_level: r.services_level,
        growth_trend: r.growth_trend,
        growth_component: r.growth_component,
      })
      const best_areas = results.map(mapResult)
      const primary = mapResult(results[0])
      return NextResponse.json({
        best_areas,
        primary,
        tie: data.tie,
        note: data.note,
        proximity_applied: data.proximity_applied ?? proximity,
        mode_used: data.mode_used,
        latest_year: data.latest_year,
        latest_quarter: data.latest_quarter,
        used_weights: data.used_weights,
        services_mult: data.services_mult,
      })
    }

    // استجابة من /predict/best-areas (باك قديم)
    if (data.primary && Array.isArray(data.best_areas) && data.best_areas.length > 0) {
      return NextResponse.json({
        best_areas: data.best_areas,
        primary: data.primary,
      })
    }

    return NextResponse.json(
      { error: data.note ?? 'لا توجد أحياء في النطاق المحدد (الدمام، الخبر، الظهران فقط).' },
      { status: 404 }
    )
  } catch (err: unknown) {
    const error = err as Error
    const msg = error?.message ?? ''
    console.error('[/api/predict/best-areas]', error?.stack ?? error?.message)
    // اتصال مرفوض أو شبكة = الباكند غالباً غير شغال
    if (msg.includes('ECONNREFUSED') || msg.includes('fetch failed') || msg.includes('Failed to fetch')) {
      return NextResponse.json(
        { error: 'لا يمكن الاتصال بخادم التقدير. تأكدي أن الباكند يعمل: uvicorn api.main:app --reload --port 8000' },
        { status: 503 }
      )
    }
    return NextResponse.json(
      { error: 'حدث خطأ غير متوقع. جرّبي لاحقًا.' },
      { status: 500 }
    )
  }
}
