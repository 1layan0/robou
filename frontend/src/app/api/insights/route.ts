import { NextResponse } from 'next/server'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const ML_API_URL = (process.env.ML_API_URL ?? '').trim()

export async function GET() {
  if (!ML_API_URL) {
    return NextResponse.json(
      { error: 'خدمة التحليلات غير متاحة. تأكدي من تشغيل الباك اند وضبط ML_API_URL.' },
      { status: 503 }
    )
  }
  const baseUrl = ML_API_URL.replace(/\/$/, '')
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 15000)

  try {
    const res = await fetch(`${baseUrl}/insights`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: controller.signal,
      next: { revalidate: 0 },
    })
    clearTimeout(timeout)
    if (!res.ok) {
      const text = await res.text()
      return NextResponse.json(
        { error: text || `الباك اند أرجع ${res.status}` },
        { status: res.status }
      )
    }
    const data = await res.json()
    return NextResponse.json(data)
  } catch (e) {
    clearTimeout(timeout)
    const isAbort = e instanceof Error && e.name === 'AbortError'
    const isConnRefused =
      e instanceof Error &&
      ('code' in e ? (e as NodeJS.ErrnoException).code === 'ECONNREFUSED' : false)
    const message =
      isAbort
        ? 'انتهت مهلة الاتصال بالباك اند. تأكدي أنه يعمل (مثلاً: uvicorn api.main:app --port 8000).'
        : isConnRefused
          ? 'لا يمكن الاتصال بالباك اند. شغّليه من مجلد backend: uvicorn api.main:app --reload --port 8000'
          : e instanceof Error
            ? e.message
            : 'فشل الاتصال بالباك اند'
    return NextResponse.json({ error: message }, { status: 502 })
  }
}
