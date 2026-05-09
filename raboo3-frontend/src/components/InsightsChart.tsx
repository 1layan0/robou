'use client'

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { motion } from 'framer-motion'
import { useI18n, useT } from '@/i18n/useTranslations'

export interface CityInsight {
  city: string
  avgPrice: number
  demand: number
}

interface InsightsChartProps {
  /** بيانات حقيقية من API التحليلات؛ إن كانت فارغة يُعرض رسالة عدم توفر بيانات */
  data?: CityInsight[] | null
}

export default function InsightsChart({ data }: InsightsChartProps) {
  const { locale } = useI18n()
  const t = useT()
  const isAr = locale === 'ar'
  const numberLocale = isAr ? 'ar-SA' : 'en-US'
  const axisNumberLocale = 'en-US'

  if (data == null || data.length === 0) {
    return (
      <div className="card h-72 p-6 flex items-center justify-center text-slate-500 dark:text-slate-400 text-sm">
        {t.insights.empty}
      </div>
    )
  }

  return (
    <motion.div
      className="card h-72 p-6"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
    >
      <h3 className="mb-4 text-base font-semibold text-ink-900 dark:text-white">
        {isAr ? 'متوسط سعر المتر ونسبة الطلب' : 'Average Price per Sqm and Demand Ratio'}
      </h3>
      <div className="h-[calc(100%-2rem)]" dir="ltr">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          barSize={32}
          margin={{ top: 8, right: 28, left: 28, bottom: 18 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.4} />
          <XAxis
            dataKey="city"
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
            tickMargin={10}
            minTickGap={24}
          />
          <YAxis
            yAxisId="left"
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
            width={72}
            tickMargin={8}
            allowDecimals={false}
            tickFormatter={(val) => Number(val).toLocaleString(axisNumberLocale)}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
            width={52}
            tickMargin={8}
            allowDecimals={false}
            tickFormatter={(val) => `${Math.round(Number(val)).toLocaleString(axisNumberLocale)}%`}
          />
          <Tooltip
            formatter={(value: number, name: string) => {
              const isPrice = name === (isAr ? 'متوسط السعر' : 'Avg Price')
              return isPrice
                ? `${value.toLocaleString(numberLocale)} ${t.predict.result.currency}`
                : `${Math.round(Number(value)).toLocaleString(numberLocale)}%`
            }}
            labelFormatter={(label) => `${isAr ? 'المدينة' : 'City'}: ${label}`}
          />
          <Bar dataKey="avgPrice" name={isAr ? 'متوسط السعر' : 'Avg Price'} yAxisId="left" radius={[12, 12, 12, 12]} fill="#16a34a" />
          <Bar dataKey="demand" name={isAr ? 'نسبة الطلب' : 'Demand'} yAxisId="right" radius={[12, 12, 12, 12]} fill="#4fbe8f" />
        </BarChart>
      </ResponsiveContainer>
      </div>
    </motion.div>
  )
}
