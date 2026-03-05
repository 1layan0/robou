'use client'

import { useEffect, useMemo, useState } from 'react'
import { animate, motion } from 'framer-motion'
import type { City } from '@/lib/cities'
import { useI18n, useT } from '@/i18n/useTranslations'
import SARIcon from '@/components/SARIcon'

export type PredictionResult = {
  pricePerSqm: number
  total: number
  range: [number, number]
  verdict: 'مبالغ' | 'عادل' | 'فرصة'
  city?: City
  /** من ML: نمو سنوي متوقع % */
  growthRatePct?: number
  /** من ML: strong_buy | buy | hold | avoid */
  recommendation?: string
  /** من ML: درجة استثمار 0–100 */
  score?: number
}

interface PriceCardProps {
  data?: PredictionResult | null
}

const verdictStyles: Record<PredictionResult['verdict'], string> = {
  مبالغ: 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300',
  عادل: 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300',
  فرصة: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-200',
}

type ConfettiPiece = { top: number; left: number; color: string }

export default function PriceCard({ data }: PriceCardProps) {
  const t = useT();
  const { locale } = useI18n();
  const isAr = locale === 'ar';
  const [confettiActive, setConfettiActive] = useState(false)
  const [confettiPieces, setConfettiPieces] = useState<ConfettiPiece[]>([])
  const verdict = data?.verdict
  const verdictDescription = verdict === 'مبالغ' ? t.predict.result.verdict_high : verdict === 'عادل' ? t.predict.result.verdict_fair : verdict === 'فرصة' ? t.predict.result.verdict_opportunity : ''

  useEffect(() => {
    let frame: number | null = null
    let timer: ReturnType<typeof setTimeout> | null = null

    frame = requestAnimationFrame(() => {
      if (verdict === 'فرصة') {
        const pieces = Array.from({ length: 24 }).map((_, index) => ({
          top: Math.random() * 100,
          left: Math.random() * 100,
          color: ['#16a34a', '#4fbe8f', '#B8860B'][index % 3],
        }))
        setConfettiPieces(pieces)
        setConfettiActive(true)
        timer = setTimeout(() => setConfettiActive(false), 1800)
      } else {
        setConfettiPieces([])
        setConfettiActive(false)
      }
    })

    return () => {
      if (frame) cancelAnimationFrame(frame)
      if (timer) clearTimeout(timer)
    }
  }, [verdict])

  if (!data) {
    return (
      <section className="card flex min-h-[260px] flex-col items-center justify-center text-center p-8 space-y-3" dir={isAr ? 'rtl' : 'ltr'}>
        <h3 className="text-lg font-semibold text-ink-800 dark:text-slate-200">{t.predict.result.empty_title}</h3>
        <p className="text-slate-500 dark:text-slate-400 text-sm max-w-xs leading-relaxed">{t.predict.result.empty_hint}</p>
      </section>
    )
  }

  const { pricePerSqm, total, range, city } = data

  return (
    <section className="relative card space-y-6 p-6" dir={isAr ? 'rtl' : 'ltr'}>
      {confettiActive && <Confetti pieces={confettiPieces} />}
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <h3 className="text-lg font-semibold text-ink-900 dark:text-white">{t.predict.result.heading}</h3>
          {city && <p className="text-xs text-slate-500 dark:text-slate-300">{isAr ? 'المدينة:' : 'City:'} {city}</p>}
        </div>
        <span className={`rounded-full px-4 py-1 text-xs font-semibold ${verdictStyles[data.verdict]}`} title={verdictDescription}>{data.verdict}</span>
      </header>
      {verdictDescription && (
        <p className="text-xs text-slate-500 dark:text-slate-400 -mt-2">{verdictDescription}</p>
      )}
      <dl className="space-y-4 text-sm">
        <Row label={t.predict.result.price_psm}>
          <AnimatedNumber value={pricePerSqm} locale={locale} /> <SARIcon />
        </Row>
        <Row label={t.predict.result.total_price}>
          <AnimatedNumber value={total} locale={locale} /> <SARIcon />
        </Row>
        <Row label={t.predict.result.range}>
          <AnimatedNumber value={range[0]} locale={locale} /> – <AnimatedNumber value={range[1]} locale={locale} /> <SARIcon />
        </Row>
      </dl>
      <div className="space-y-3 text-xs text-slate-500 dark:text-slate-300">
        <p>{t.predict.result.note}</p>
      </div>
    </section>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-6">
      <dt className="text-slate-500 dark:text-slate-300">{label}</dt>
      <dd className="text-base font-semibold text-ink-900 dark:text-white">{children}</dd>
    </div>
  )
}

function AnimatedNumber({ value, locale = 'ar' }: { value: number; locale?: string }) {
  const [displayValue, setDisplayValue] = useState(value)

  useEffect(() => {
    const controls = animate(0, value, {
      duration: 0.8,
      ease: 'easeOut',
      onUpdate: (latest) => setDisplayValue(latest),
    })
    return () => controls.stop()
  }, [value])

  const formatted = useMemo(
    () => Math.round(displayValue).toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US'),
    [displayValue, locale]
  )
  return <motion.span layout>{formatted}</motion.span>
}

function Confetti({ pieces }: { pieces: ConfettiPiece[] }) {
  return (
    <motion.div
      className="pointer-events-none absolute inset-0 overflow-hidden"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      {pieces.map((piece, index) => (
        <motion.span
          key={index}
          className="absolute h-2 w-2 rounded-full"
          style={{ top: `${piece.top}%`, left: `${piece.left}%`, backgroundColor: piece.color }}
          initial={{ scale: 0, y: -20 }}
          animate={{ scale: [1, 0.6, 1], y: 20, opacity: [1, 0.7, 0] }}
          transition={{ duration: 1.2, delay: index * 0.02 }}
        />
      ))}
    </motion.div>
  )
}
