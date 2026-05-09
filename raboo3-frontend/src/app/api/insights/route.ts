import { NextResponse } from 'next/server'
import { getSupabaseAdmin } from '@/lib/supabase/server'
import { fetchInsightsFromSupabase } from '@/lib/supabase/analytics-from-db'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const ML_API_URL = (process.env.ML_API_URL ?? '').trim()

async function fetchFromMl(propertyType: string | null): Promise<Response> {
  const baseUrl = ML_API_URL.replace(/\/$/, '')
  const q = propertyType
    ? `?property_type=${encodeURIComponent(propertyType)}`
    : ''
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 15000)
  try {
    const res = await fetch(`${baseUrl}/insights${q}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: controller.signal,
      next: { revalidate: 0 },
    })
    clearTimeout(timeout)
    return res
  } finally {
    clearTimeout(timeout)
  }
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const propertyType = searchParams.get('property_type')

  const admin = getSupabaseAdmin()
  if (admin) {
    const fromDb = await fetchInsightsFromSupabase(admin, propertyType)
    if (fromDb !== null) {
      return NextResponse.json(fromDb)
    }
  }

  if (!ML_API_URL) {
    return NextResponse.json(
      {
        error:
          'لا توجد بيانات تحليلات من قاعدة Supabase أو خدمة ML. تأكدي من رفع التجميع وضبط NEXT_PUBLIC_SUPABASE_URL وSUPABASE_SERVICE_ROLE_KEY، أو شغّلي الباك اند وضبطي ML_API_URL.',
      },
      { status: 503 },
    )
  }

  try {
    const res = await fetchFromMl(propertyType)
    if (!res.ok) {
      const text = await res.text()
      return NextResponse.json(
        { error: text || `الباك اند أرجع ${res.status}` },
        { status: res.status },
      )
    }
    const data = await res.json()
    return NextResponse.json(data)
  } catch (e) {
    const isAbort = e instanceof Error && e.name === 'AbortError'
    const isConnRefused =
      e instanceof Error &&
      ('code' in e ? (e as NodeJS.ErrnoException).code === 'ECONNREFUSED' : false)
    const message =
      isAbort
        ? 'انتهت مهلة الاتصال بالباك اند. تأكدي أنه يعمل (مثلاً: uvicorn api.main:app --port 8000).'
        : isConnRefused
          ? 'لا يمكن الاتصال بالباك اند. شغّليه من مجلد raboo3-ml: uvicorn api.main:app --reload --port 8000'
          : e instanceof Error
            ? e.message
            : 'فشل الاتصال بالباك اند'
    return NextResponse.json({ error: message }, { status: 502 })
  }
}
