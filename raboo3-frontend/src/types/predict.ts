/** عنصر من استجابة أفضل أحياء (مقارنة 2–3 أحياء) */
export type BestAreaItem = {
  city: string
  district: string
  district_id?: number
  property_type_ar?: string
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

export type PredictionResult = {
  pricePerSqm: number
  total: number
  range: [number, number]
  verdict: 'مبالغ' | 'عادل' | 'فرصة'
  city?: string
  growthRatePct?: number
  recommendation?: string
  score?: number
}

/** Payload من best-areas أو التقدير الكلاسيكي — مستخدم في ValuationReport وصفحة التوقع */
export type PredictionPayload = PredictionResult & {
  city: string
  /** نوع العقار العربي (مفضلة Supabase) */
  propertyTypeAr?: string
  coords: [number, number] | null
  area?: number
  district?: string
  bestAreas?: BestAreaItem[]
  proximityApplied?: string
  tie?: boolean
  note?: string
  latestYear?: number
  latestQuarter?: number
}
