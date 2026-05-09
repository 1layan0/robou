'use client'

import { useI18n, useT } from '@/i18n/useTranslations'
import type { PredictionPayload } from '@/types/predict'
import SARIcon from '@/components/SARIcon'
import { translateCity, translateDistrict, translateReason } from '@/lib/translateLocations'
import FavoriteStarButton from '@/components/FavoriteStarButton'

type ConfidenceLevel = 'high' | 'medium' | 'low'
type Recommendation = 'buy' | 'wait' | 'unsuitable'
type GrowthTrend = 'up' | 'stable' | 'down'

function useReportDerived(data: PredictionPayload) {
  const { verdict, growthRatePct, recommendation: mlRec, score: mlScore } = data
  const rec: Recommendation =
    mlRec === 'strong_buy' || mlRec === 'buy' ? 'buy'
    : mlRec === 'hold' ? 'wait'
    : mlRec === 'avoid' ? 'unsuitable'
    : verdict === 'فرصة' ? 'buy'
    : verdict === 'عادل' ? 'wait'
    : 'unsuitable'
  const confidence: ConfidenceLevel =
    typeof mlScore === 'number'
      ? mlScore >= 70 ? 'high'
      : mlScore >= 40 ? 'medium'
      : 'low'
    : rec === 'buy' ? 'high'
    : rec === 'wait' ? 'medium'
    : 'low'
  return { rec, confidence }
}

function growthToTrend(pct: number | undefined): GrowthTrend {
  if (pct == null) return 'stable'
  if (pct > 5) return 'up'
  if (pct < -5) return 'down'
  return 'stable'
}

function trendFromBackend(area: { growth_trend?: 'up' | 'flat' | 'down'; growth_rate_pct?: number }): GrowthTrend {
  if (area.growth_trend === 'up') return 'up'
  if (area.growth_trend === 'down') return 'down'
  if (area.growth_trend === 'flat') return 'stable'
  return growthToTrend(area.growth_rate_pct)
}

function sanitizeDisplayedGrowthReason(reason: string): string {
  return reason.replace(/\(([+-]?\d+(?:\.\d+)?)%\)/g, (_match, value: string) => {
    const num = Number.parseFloat(value)
    const safe = Number.isFinite(num) ? Math.min(100, Math.max(0, num)) : 0
    return `(${safe.toFixed(1)}%)`
  })
}

function servicesLevelLabel(s: 'high' | 'medium' | 'low', isAr: boolean): string {
  if (s === 'high') return isAr ? 'عالي' : 'High'
  if (s === 'medium') return isAr ? 'متوسط' : 'Medium'
  return isAr ? 'منخفض' : 'Low'
}

export default function ValuationReport({
  data,
  onTop3CardFocus,
  focusedTop3Index,
}: {
  data: PredictionPayload
  onTop3CardFocus?: (index: number) => void
  focusedTop3Index?: number | null
}) {
  const t = useT()
  const { locale } = useI18n()
  const isAr = locale === 'ar'
  const { rec, confidence } = useReportDerived(data)
  const bestDistrictRaw = data.district || data.city
  const bestCityRaw = data.city
  const bestDistrict = data.district ? translateDistrict(bestDistrictRaw, locale) : translateCity(bestDistrictRaw, locale)
  const bestCity = translateCity(bestCityRaw, locale)

  return (
    <article className="space-y-6" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="space-y-6">
          {/* 1) Decision Card — قرار سريع */}
          <section className="card p-6 border-2 border-raboo3-200/80 dark:border-raboo3-700/50 bg-gradient-to-br from-raboo3-50/50 to-white dark:from-raboo3-900/10 dark:to-ink-900">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm text-slate-500 dark:text-slate-400 mb-0.5">
                  {isAr ? 'أفضل حي في نطاقك' : 'Best district in your range'}
                </p>
                <h2 className="text-2xl font-bold text-ink-900 dark:text-white">
                  {bestDistrict}
                  {bestDistrictRaw !== bestCityRaw && (
                    <span className="text-lg font-medium text-slate-600 dark:text-slate-300">{isAr ? '، ' : ', '}{bestCity}</span>
                  )}
                </h2>
                <p className="text-2xl font-extrabold text-raboo3-600 dark:text-raboo3-400 mt-2">
                  {data.pricePerSqm.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} <SARIcon />/{isAr ? 'م²' : 'm²'}
                </p>
              </div>
              <div className="text-left">
                <p className="text-lg font-bold">
                  {rec === 'buy' && <span className="text-green-600 dark:text-green-400">{t.predict.report.rec_buy}</span>}
                  {rec === 'unsuitable' && <span className="text-red-600 dark:text-red-400">{t.predict.report.rec_unsuitable}</span>}
                </p>
              </div>
            </div>
          </section>

          {/* 2) Top 3 — مختصر: سعر، Score، اتجاه نمو، خدمات، ثقة، سببين + تفاصيل (confidence_reason) */}
          {data.bestAreas && data.bestAreas.length >= 1 && (
            <section className="card p-6">
              <h3 className="text-base font-bold text-slate-600 dark:text-slate-300 uppercase tracking-wide mb-4">
                {isAr ? 'مقارنة أفضل 3 أحياء' : 'Top 3 comparison'}
              </h3>
              {data.tie && (
                <p className="text-sm text-amber-600 dark:text-amber-400 mb-3">{isAr ? 'الأحياء متقاربة' : 'Areas are close'}</p>
              )}
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {data.bestAreas.map((area, i) => {
                  const trend = trendFromBackend(area)
                  const reasons = area.reasons?.slice(0, 2) ?? []
                  const reason1Raw = sanitizeDisplayedGrowthReason(reasons[0] ?? (isAr ? 'مناسب حسب المعايير' : 'Suitable by criteria'))
                  const reason2Raw = reasons[1] ? sanitizeDisplayedGrowthReason(reasons[1]) : undefined
                  const reason1 = translateReason(reason1Raw, locale)
                  const reason2 = reason2Raw ? translateReason(reason2Raw, locale) : ''
                  const isFocused = focusedTop3Index === i
                  const servicesLevel = area.services_level ?? 'medium'
                  const areaCityLabel = translateCity(area.city, locale)
                  const areaDistrictLabel = (area.district ? translateDistrict(area.district, locale) : areaCityLabel)
                  return (
                    <div
                      key={`${area.city}-${area.district}-${i}`}
                      className={`relative rounded-xl border-2 p-4 text-sm transition-shadow ${
                        i === 0
                          ? 'border-raboo3-400 bg-raboo3-50/50 dark:border-raboo3-500 dark:bg-raboo3-900/20'
                          : 'border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-800/30'
                      } ${isFocused ? 'ring-2 ring-raboo3-500' : ''}`}
                    >
                      <div className={`absolute top-4 z-10 ${isAr ? 'left-4' : 'right-4'}`}>
                        <FavoriteStarButton
                          city_ar={area.city}
                          district_ar={area.district || area.city}
                          district_id={area.district_id}
                          property_type_ar={area.property_type_ar ?? data.propertyTypeAr ?? ''}
                          predictedPricePerSqm={area.price_per_sqm}
                        />
                      </div>
                      <div className="flex items-center gap-2 mb-3">
                        <button
                          type="button"
                          aria-label={isAr ? `الحي ${i + 1}` : `Area ${i + 1}`}
                          onClick={() => onTop3CardFocus?.(i)}
                          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full font-bold text-white text-xs"
                          style={{
                            background: i === 0 ? '#16a34a' : i === 1 ? '#2563eb' : '#9333ea',
                          }}
                        >
                          {i + 1}
                        </button>
                        <div className="min-w-0 flex-1">
                          <p className="font-bold text-ink-900 dark:text-white truncate">{areaDistrictLabel || areaCityLabel}</p>
                          <p className="text-slate-500 dark:text-slate-400 text-xs">{areaCityLabel}</p>
                        </div>
                      </div>
                      <dl className="space-y-1.5 text-slate-600 dark:text-slate-300">
                        <div className="flex justify-between gap-2">
                          <span>{t.predict.report.price_per_sqm}</span>
                          <span className="font-semibold text-ink-900 dark:text-white">
                            {area.price_per_sqm.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} <SARIcon />/{isAr ? 'م²' : 'm²'}
                          </span>
                        </div>
                        <div className="flex justify-between gap-2 items-center">
                          <span>{isAr ? 'اتجاه النمو' : 'Growth trend'}</span>
                          <span className="font-medium">
                            {trend === 'up' && <span className="text-green-600 dark:text-green-400">{isAr ? 'جيد ↑' : 'Up ↑'}</span>}
                            {trend === 'stable' && <span className="text-slate-600 dark:text-slate-400">{isAr ? 'مستقر →' : 'Stable →'}</span>}
                            {trend === 'down' && <span className="text-amber-600 dark:text-amber-400">{isAr ? 'تراجع ↓' : 'Down ↓'}</span>}
                          </span>
                        </div>
                        <div className="flex justify-between gap-2 items-center">
                          <span>{isAr ? 'الخدمات' : 'Services'}</span>
                          <span className="font-medium text-ink-800 dark:text-slate-200">
                            {servicesLevelLabel(servicesLevel, isAr)}
                          </span>
                        </div>
                        <div>
                          <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">{reason1}</p>
                          {reason2 && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{reason2}</p>}
                        </div>
                      </dl>
                    </div>
                  )
                })}
              </div>
            </section>
          )}
        </div>
    </article>
  )
}
