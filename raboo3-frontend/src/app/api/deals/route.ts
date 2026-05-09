import { NextResponse } from 'next/server'
import { getSupabaseAdmin } from '@/lib/supabase/server'
import { fetchDealsFromSupabase } from '@/lib/supabase/analytics-from-db'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const ML_API_URL = (process.env.ML_API_URL ?? '').trim()

type DealRow = {
  city_ar: string
  district_ar: string
  year: number
  quarter: number
  property_type_ar: string
  price_per_sqm: number
  price_total: number | null
  area_sqm: number | null
}

function getLatestYear(rows: DealRow[] | null | undefined): number {
  if (!rows?.length) return 0
  return rows.reduce((max, row) => {
    const year = Number(row?.year) || 0
    return year > max ? year : max
  }, 0)
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const limitRaw = searchParams.get('limit')
  const limit = limitRaw != null ? Number.parseInt(limitRaw, 10) : 500
  const lim = Number.isFinite(limit) ? limit : 500
  const mlLimit = Math.min(lim, 1000)

  let fromDb: DealRow[] | null = null
  const admin = getSupabaseAdmin()
  if (admin) {
    fromDb = await fetchDealsFromSupabase(admin, lim)
  }

  if (!ML_API_URL) {
    return NextResponse.json({ transactions: fromDb ?? [] }, { status: 200 })
  }

  const baseUrl = ML_API_URL.replace(/\/$/, '')
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 12000)

  try {
    const res = await fetch(`${baseUrl}/deals?limit=${mlLimit}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: controller.signal,
      next: { revalidate: 0 },
    })
    clearTimeout(timeout)
    if (!res.ok) {
      return NextResponse.json({ transactions: fromDb ?? [] }, { status: 200 })
    }
    const data = (await res.json()) as { transactions?: DealRow[] }
    const fromMl = Array.isArray(data.transactions) ? data.transactions : []

    if (!fromDb?.length) {
      return NextResponse.json({ transactions: fromMl }, { status: 200 })
    }

    const dbLatestYear = getLatestYear(fromDb)
    const mlLatestYear = getLatestYear(fromMl)
    const preferred = mlLatestYear > dbLatestYear ? fromMl : fromDb
    return NextResponse.json({ transactions: preferred }, { status: 200 })
  } catch {
    clearTimeout(timeout)
    return NextResponse.json({ transactions: fromDb ?? [] }, { status: 200 })
  }
}
