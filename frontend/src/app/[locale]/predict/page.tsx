'use client'

import dynamic from 'next/dynamic'
import Link from 'next/link'
import { useRef, useState, useCallback } from 'react'
import ValuationReport from '@/components/ValuationReport'
import type { PredictionPayload } from '@/components/PredictForm'
import { useAuth } from '@/contexts/AuthContext'
import { useNotifications } from '@/contexts/NotificationContext'
import { useI18n, useT } from '@/i18n/useTranslations'
import type { Bbox } from '@/components/GoogleMapView'
import SARIcon from '@/components/SARIcon'

const GoogleMapView = dynamic(() => import('@/components/GoogleMapView'), { ssr: false })

const DEFAULT_AREA_M2 = 400
const BUDGET_MIN_DEFAULT = 500
const BUDGET_MAX_DEFAULT = 8000

export default function PredictPage() {
  const { locale } = useI18n()
  const t = useT()
  const isAr = locale === 'ar'
  const { user } = useAuth()
  const { addNotification } = useNotifications()
  const [showLoginRequired, setShowLoginRequired] = useState(false)
  const [selectedBbox, setSelectedBbox] = useState<Bbox | null>(null)
  const [usage, setUsage] = useState<'سكني' | 'تجاري'>('سكني')
  const [proximity, setProximity] = useState<'قريب' | 'متوسط' | 'بعيد'>('قريب')
  const [minPrice, setMinPrice] = useState(BUDGET_MIN_DEFAULT)
  const [maxPrice, setMaxPrice] = useState(BUDGET_MAX_DEFAULT)
  const [result, setResult] = useState<PredictionPayload | null>(null)
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [focusedTop3Index, setFocusedTop3Index] = useState<number | null>(null)
  const [showDistrictNames, setShowDistrictNames] = useState(false)
  const reportRef = useRef<HTMLDivElement>(null)

  const handleBboxSelect = useCallback((bbox: Bbox) => {
    setSelectedBbox(bbox)
  }, [])

  const handleGetBestArea = useCallback(async () => {
    if (!user) {
      setShowLoginRequired(true)
      return
    }
    if (!selectedBbox) {
      addNotification({
        type: 'warning',
        title: isAr ? 'حدد المنطقة أولاً' : 'Select area first',
        message: t.recommend_areas.draw_hint,
        duration: 5000,
      })
      return
    }
    setError(null)
    setLoading(true)
    try {
      // استدعاء أفضل أحياء في النطاق (1–3 حسب ما يضمّه المستطيل)
      const res = await fetch('/api/predict/best-areas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bbox: selectedBbox,
          land_use: usage,
          proximity,
          min_price_per_sqm: minPrice,
          max_price_per_sqm: maxPrice,
          area_sqm: DEFAULT_AREA_M2,
          top_n: 3,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        const errMsg =
          typeof data?.error === 'string'
            ? data.error
            : data?.error && typeof data.error === 'object' && 'message' in data.error
              ? String((data.error as { message?: string }).message)
              : data?.note ?? (isAr ? 'فشل التقدير' : 'Valuation failed')
        setError(errMsg)
        return
      }
      const primary = data.primary
      const bestAreas = Array.isArray(data.best_areas) ? data.best_areas : []
      if (bestAreas.length === 0) {
        setError(typeof data.note === 'string' ? data.note : (isAr ? 'لا توجد أحياء ضمن النطاق' : 'No districts in range'))
        return
      }
      const coordPair: [number, number] = [
        primary?.latitude ?? (selectedBbox[1] + selectedBbox[3]) / 2,
        primary?.longitude ?? (selectedBbox[0] + selectedBbox[2]) / 2,
      ]
      const pricePerSqm = typeof primary?.price_per_sqm === 'number' ? primary.price_per_sqm : 0
      const total = Math.round(pricePerSqm * DEFAULT_AREA_M2)
      const range: [number, number] = [
        Math.round(pricePerSqm * 0.9),
        Math.round(pricePerSqm * 1.1),
      ]
      const payload: PredictionPayload = {
        pricePerSqm,
        total,
        range,
        verdict: 'عادل',
        city: (primary?.city ?? 'الدمام') as PredictionPayload['city'],
        district: primary?.district ?? '',
        coords: coordPair,
        area: DEFAULT_AREA_M2,
        growthRatePct: typeof primary?.growth_rate_pct === 'number' ? primary.growth_rate_pct : undefined,
        bestAreas: bestAreas.length > 0 ? bestAreas : undefined,
        proximityApplied: data.proximity_applied ?? proximity,
        tie: data.tie,
        note: data.note,
        latestYear: typeof data.latest_year === 'number' ? data.latest_year : undefined,
        latestQuarter: typeof data.latest_quarter === 'number' ? data.latest_quarter : undefined,
      }
      setResult(payload)
      setCoords({ lat: coordPair[0], lng: coordPair[1] })
      setTimeout(() => reportRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300)
    } finally {
      setLoading(false)
    }
  }, [user, selectedBbox, usage, proximity, minPrice, maxPrice, addNotification, isAr, t.recommend_areas.draw_hint])

  const handleReset = useCallback(() => {
    setResult(null)
    setCoords(null)
    setSelectedBbox(null)
    setError(null)
  }, [])

  return (
    <main
      className="section relative overflow-hidden bg-gradient-to-br from-slate-50 via-white to-raboo3-50/10 dark:from-ink-900 dark:via-ink-900 dark:to-raboo3-900/5"
      dir={isAr ? 'rtl' : 'ltr'}
    >
      <div className="container grid gap-8 lg:grid-cols-12">
        <div className="lg:col-span-5">
          <div className="card p-8 space-y-6">
            <header className="space-y-3">
              <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl">
                {t.recommend_areas.title}
              </h1>
              <p className="text-slate-600 dark:text-slate-300 text-sm leading-relaxed max-w-lg">
                {t.recommend_areas.intro}
              </p>
            </header>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-ink-700 dark:text-slate-300 mb-1.5">
                  {t.recommend_areas.select_usage}
                </label>
                <select
                  value={usage}
                  onChange={(e) => setUsage(e.target.value as 'سكني' | 'تجاري')}
                  className="input w-full"
                >
                  <option value="سكني">{t.recommend_areas.usage_res}</option>
                  <option value="تجاري">{t.recommend_areas.usage_com}</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-ink-700 dark:text-slate-300 mb-1.5">
                  {t.recommend_areas.select_proximity}
                </label>
                <select
                  value={proximity}
                  onChange={(e) => setProximity(e.target.value as 'قريب' | 'متوسط' | 'بعيد')}
                  className="input w-full"
                >
                  <option value="قريب">{t.recommend_areas.proximity_near}</option>
                  <option value="متوسط">{t.recommend_areas.proximity_medium}</option>
                  <option value="بعيد">{t.recommend_areas.proximity_far}</option>
                </select>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">{t.recommend_areas.draw_hint}</p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleGetBestArea}
                  disabled={loading}
                  className="btn btn-primary flex-1"
                >
                  {loading ? (isAr ? 'جاري التقدير...' : 'Loading...') : t.recommend_areas.predict_btn}
                </button>
                {result && (
                  <button type="button" onClick={handleReset} className="btn border border-slate-300 dark:border-ink-600">
                    {isAr ? 'جديد' : 'New'}
                  </button>
                )}
              </div>
            </div>

            {error && (
              <div className="card border border-red-300 bg-red-50 text-red-700 dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-200 p-4">
                {typeof error === 'string' ? error : String(error)}
              </div>
            )}

            {result && (
              <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
                <p className="text-sm font-medium text-ink-900 dark:text-white">
                  {isAr ? 'أفضل حي مقترح في نطاقك: ' : 'Top district in your range: '}
                  {result.district && result.district !== result.city ? result.district : result.city}
                  {result.district && result.district !== result.city ? `، ${result.city}` : ''}
                  {result.bestAreas && result.bestAreas.length > 1 && (
                    <span className="text-slate-500 dark:text-slate-400 font-normal">
                      {' '}({isAr ? 'مقارنة بين ' : 'compare '}{result.bestAreas.length} {isAr ? 'أحياء' : 'areas'})
                    </span>
                  )}
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="lg:col-span-7 space-y-6">
          <div className="card p-0 overflow-hidden relative">
            {result?.bestAreas && result.bestAreas.length > 0 && (
              <div className="absolute top-3 right-3 z-10 flex items-center gap-2 px-3 py-2 rounded-lg bg-white/95 dark:bg-ink-800 shadow border border-slate-200 dark:border-slate-600">
                <label className="text-sm font-medium text-ink-700 dark:text-slate-200 cursor-pointer flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={showDistrictNames}
                    onChange={(e) => setShowDistrictNames(e.target.checked)}
                    className="rounded border-slate-300 text-raboo3-600 focus:ring-raboo3-500"
                  />
                  {isAr ? 'إظهار أسماء الأحياء' : 'Show district names'}
                </label>
              </div>
            )}
            <GoogleMapView
              city={result?.city ?? 'الدمام'}
              district={result?.district}
              coords={coords}
              result={result ?? null}
              mode={result ? 'point' : 'bbox'}
              onBboxSelect={result ? undefined : handleBboxSelect}
              selectedBbox={selectedBbox}
              top3Areas={result?.bestAreas?.map((a) => ({ lat: a.latitude, lng: a.longitude, label: a.district || a.city })) ?? null}
              showDistrictNames={showDistrictNames}
              onTop3MarkerClick={result?.bestAreas ? (index) => {
                setFocusedTop3Index(index)
                reportRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              } : undefined}
            />
          </div>
        </div>
      </div>

      {result && (
        <div ref={reportRef} className="container mt-10 pt-8 border-t border-slate-200 dark:border-slate-800">
          <ValuationReport
            data={result}
            focusedTop3Index={focusedTop3Index}
            onTop3CardFocus={(index) => {
              setFocusedTop3Index(index)
              reportRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }}
          />
        </div>
      )}

      {showLoginRequired && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="login-required-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
          onClick={() => setShowLoginRequired(false)}
        >
          <div
            className="rounded-2xl shadow-xl bg-white dark:bg-ink-800 border border-slate-200 dark:border-slate-600 p-6 max-w-sm w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="login-required-title" className="text-lg font-bold text-ink-900 dark:text-white mb-2">
              {isAr ? 'تسجيل الدخول مطلوب' : 'Sign in required'}
            </h2>
            <p className="text-slate-600 dark:text-slate-300 text-sm mb-6">
              {t.recommend_areas.login_required_message}
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setShowLoginRequired(false)}
                className="flex-1 py-2.5 px-4 rounded-xl border border-slate-300 dark:border-slate-500 text-ink-700 dark:text-slate-200 font-medium text-sm hover:bg-slate-50 dark:hover:bg-ink-700 transition-colors"
              >
                {isAr ? 'إغلاق' : 'Close'}
              </button>
              <Link
                href={`/${locale}/login`}
                className="flex-1 py-2.5 px-4 rounded-xl bg-raboo3-600 hover:bg-raboo3-700 text-white font-semibold text-sm text-center transition-colors"
              >
                {isAr ? 'تسجيل الدخول' : 'Sign in'}
              </Link>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
