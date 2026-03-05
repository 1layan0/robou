import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const AQARSAS_DEALS_URL = 'https://api.aqarsas.sa/deals/';
const API_KEY = process.env.AQARSAS_API_KEY ?? '';

/** Build request body for Aqarsas /deals. state 4 = Al Sharqiah (Eastern Province). */
function buildBody(body: Record<string, unknown>): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    key: API_KEY,
    calendar: body.calendar ?? 'gregorian',
    state: body.state ?? 4, // Al Sharqiah
    ...(body.start_date && { start_date: body.start_date }),
    ...(body.end_date && { end_date: body.end_date }),
    ...(body.city && { city: body.city }),
    ...(body.category && { category: body.category }),
    ...(body.dtype && { dtype: body.dtype }),
    ...(body.min_meter_price != null && { min_meter_price: Number(body.min_meter_price) }),
    ...(body.max_meter_price != null && { max_meter_price: Number(body.max_meter_price) }),
    ...(body.min_deal_price != null && { min_deal_price: Number(body.min_deal_price) }),
    ...(body.max_deal_price != null && { max_deal_price: Number(body.max_deal_price) }),
    ...(body.min_area != null && { min_area: Number(body.min_area) }),
    ...(body.max_area != null && { max_area: Number(body.max_area) }),
    ...(body.hai && { hai: body.hai, hai_exact_match: body.hai_exact_match ?? 0 }),
  };
  return payload;
}

export async function POST(request: NextRequest) {
  if (!API_KEY) {
    return NextResponse.json({
      Error_code: 1,
      Error_msg: 'Missing API key',
      no_api_key: true,
      Deals_list: [],
    });
  }

  let body: Record<string, unknown> = {};
  try {
    body = await request.json();
  } catch {
    body = {};
  }

  const payload = buildBody(body);

  try {
    const res = await fetch(AQARSAS_DEALS_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      return NextResponse.json(
        { Error_code: 1, Error_msg: data?.Error_msg ?? 'Aqarsas request failed', Deals_list: [] },
        { status: res.status }
      );
    }

    return NextResponse.json(data);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Network error';
    return NextResponse.json(
      { Error_code: 1, Error_msg: message, Deals_list: [] },
      { status: 502 }
    );
  }
}
