import { NextResponse } from "next/server";
import { z } from "zod";
import { resolveCityFromCoords } from "@/lib/geo";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BodySchema = z.object({
  city: z.enum(["الدمام","الخبر","الظهران"]).optional(),
  district: z.string().optional(),
  bbox: z.tuple([z.number(), z.number(), z.number(), z.number()]).optional(), // [minLng, minLat, maxLng, maxLat]
  land_area_m2: z.coerce.number().positive("المساحة غير صحيحة"),
  land_use: z.enum(["سكني","تجاري"]),
  street_width_m: z.coerce.number().int().positive().optional(),
  num_streets: z.coerce.number().int().min(1).max(4),
  proximity: z.enum(["قريب","متوسط","بعيد"]).optional(),
  lat: z.coerce.number().optional(),
  lng: z.coerce.number().optional(),
});

const CITY_BASE: Record<string, number> = { "الدمام": 1750, "الخبر": 1850, "الظهران": 2100 };

const ML_API_URL = (process.env.ML_API_URL ?? "").trim();

function mlPayload(d: z.infer<typeof BodySchema>) {
  return {
    city: d.city,
    district: d.district,
    area_sqm: d.land_area_m2,
    land_use: d.land_use,
    street_count: d.num_streets,
    ...(d.proximity ? { proximity: d.proximity } : {}),
    ...(d.lat != null && d.lng != null && !isNaN(d.lat) && !isNaN(d.lng) ? { lat: d.lat, lng: d.lng } : {}),
  };
}

function mlRecommendationToVerdict(rec: string): "مبالغ" | "عادل" | "فرصة" {
  if (rec === "strong_buy" || rec === "buy") return "فرصة";
  if (rec === "hold") return "عادل";
  return "مبالغ";
}

async function fetchFromML<T>(path: string, body: object): Promise<T | null> {
  if (!ML_API_URL) return null;
  const url = `${ML_API_URL.replace(/\/$/, "")}${path}`;
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

type CentroidsResponse = { centroids: Array<{ city: string; district: string; latitude: number; longitude: number }> };

async function fetchDistrictsCoordinates(): Promise<CentroidsResponse["centroids"]> {
  if (!ML_API_URL) return [];
  const url = `${ML_API_URL.replace(/\/$/, "")}/districts/coordinates`;
  try {
    const res = await fetch(url);
    if (!res.ok) return [];
    const data = (await res.json()) as CentroidsResponse;
    return data.centroids ?? [];
  } catch {
    return [];
  }
}

/** اختيار أفضل حي داخل النطاق: الذي يقع مركزه داخل الـ bbox، أو الأقرب لمركز النطاق */
function pickBestDistrictInBbox(
  bbox: [number, number, number, number],
  centroids: Array<{ city: string; district: string; latitude: number; longitude: number }>
): { city: string; district: string; lat: number; lng: number } | null {
  const [minLng, minLat, maxLng, maxLat] = bbox;
  const centerLat = (minLat + maxLat) / 2;
  const centerLng = (minLng + maxLng) / 2;
  const allowedCities = ["الدمام", "الخبر", "الظهران"];

  const inside = centroids.filter(
    (c) =>
      allowedCities.includes(c.city) &&
      c.latitude >= minLat &&
      c.latitude <= maxLat &&
      c.longitude >= minLng &&
      c.longitude <= maxLng
  );
  const candidates = inside.length > 0 ? inside : centroids.filter((c) => allowedCities.includes(c.city));
  if (candidates.length === 0) return null;

  let best = candidates[0];
  let bestDistSq =
    (best.latitude - centerLat) ** 2 + (best.longitude - centerLng) ** 2;
  for (let i = 1; i < candidates.length; i++) {
    const c = candidates[i];
    const d = (c.latitude - centerLat) ** 2 + (c.longitude - centerLng) ** 2;
    if (d < bestDistSq) {
      bestDistSq = d;
      best = c;
    }
  }
  return {
    city: best.city,
    district: best.district,
    lat: best.latitude,
    lng: best.longitude,
  };
}

export async function POST(req: Request) {
  try {
    const json = await req.json().catch(() => ({}));
    const parsed = BodySchema.safeParse(json);
    if (!parsed.success) {
      return NextResponse.json(
        { error: "بيانات غير مكتملة", details: parsed.error.flatten() },
        { status: 400 }
      );
    }

    let d = parsed.data;

    if (d.bbox != null && d.bbox.length === 4) {
      const centroids = await fetchDistrictsCoordinates();
      const best = pickBestDistrictInBbox(d.bbox, centroids);
      if (!best) {
        return NextResponse.json(
          { error: "لم نتمكن من تحديد حي داخل النطاق المحدد. جرّبي توسيع النطاق أو اختيار منطقة أخرى." },
          { status: 400 }
        );
      }
      d = {
        ...d,
        city: best.city as "الدمام" | "الخبر" | "الظهران",
        district: best.district,
        lat: best.lat,
        lng: best.lng,
      };
    } else if (!d.city || !d.district) {
      return NextResponse.json(
        { error: "المدينة والحي مطلوبان، أو حدّدي نطاقًا على الخريطة." },
        { status: 400 }
      );
    }

    if (process.env.NODE_ENV === "development") {
      console.info("[/api/predict] payload", d);
    }

    if (d.lat != null && d.lng != null && typeof d.lat === 'number' && typeof d.lng === 'number' && !isNaN(d.lat) && !isNaN(d.lng)) {
      const detectedCity = await resolveCityFromCoords(d.lat, d.lng);
      if (detectedCity && detectedCity !== d.city && process.env.NODE_ENV === "development") {
        console.warn("[/api/predict] city/location mismatch", {
          selectedCity: d.city,
          detectedCity,
          lat: d.lat,
          lng: d.lng,
        });
      }
    }

    const payload = mlPayload(d);
    let pricePerSqm: number;
    let total: number;
    let verdict: "مبالغ" | "عادل" | "فرصة";
    let growthRatePct: number | undefined;
    let recommendation: string | undefined;
    let score: number | undefined;

    const predictRes = await fetchFromML<{ price_per_sqm: number; total_price?: number }>("/predict", payload);
    if (predictRes && typeof predictRes.price_per_sqm === "number" && predictRes.price_per_sqm > 0) {
      pricePerSqm = Math.round(predictRes.price_per_sqm);
      const area = Math.max(80, d.land_area_m2);
      total = predictRes.total_price != null ? Math.round(predictRes.total_price) : Math.round(pricePerSqm * area);
      const invRes = await fetchFromML<{ recommendation: string; score: number }>("/predict/investment", payload);
      if (invRes?.recommendation != null) {
        verdict = mlRecommendationToVerdict(invRes.recommendation);
        recommendation = invRes.recommendation;
        score = typeof invRes.score === "number" ? invRes.score : undefined;
      } else {
        verdict = pricePerSqm * area > total * 1.08 ? "مبالغ" : total < pricePerSqm * area * 0.95 ? "فرصة" : "عادل";
      }
      const growthRes = await fetchFromML<{ growth_rate_pct: number }>("/predict/growth", payload);
      if (growthRes != null && typeof growthRes.growth_rate_pct === "number") {
        growthRatePct = growthRes.growth_rate_pct;
      }
    } else {
      const base = (d.city != null && d.city in CITY_BASE ? CITY_BASE[d.city as keyof typeof CITY_BASE] : null) ?? 1800;
      const streetWidth = d.street_width_m ?? 15;
      const w = streetWidth >= 20 ? 1.06 : 1.0;
      const streets = d.num_streets >= 2 ? 1.08 : 1.0;
      const use = d.land_use === "تجاري" ? 1.12 : 1.0;
      const adj = w * streets * use;
      pricePerSqm = Math.round(base * adj);
      const area = Math.max(80, d.land_area_m2);
      total = Math.round(pricePerSqm * area);
      verdict = total > pricePerSqm * area * 1.08 ? "مبالغ" : total < pricePerSqm * area * 0.95 ? "فرصة" : "عادل";
    }

    const range: [number, number] = [Math.round(pricePerSqm * 0.9), Math.round(pricePerSqm * 1.1)];
    const safeCoords =
      d.lat != null && d.lng != null &&
      typeof d.lat === 'number' && typeof d.lng === 'number' &&
      !isNaN(d.lat) && !isNaN(d.lng) &&
      d.lat >= -90 && d.lat <= 90 && d.lng >= -180 && d.lng <= 180
        ? { lat: d.lat, lng: d.lng }
        : null;

    const response: Record<string, unknown> = {
      pricePerSqm,
      total,
      range,
      verdict,
      city: d.city,
      district: d.district,
      coords: safeCoords,
    };
    if (growthRatePct != null) response.growthRatePct = growthRatePct;
    if (recommendation != null) response.recommendation = recommendation;
    if (score != null) response.score = score;

    return NextResponse.json(response);
  } catch (err: unknown) {
    const error = err as Error;
    console.error("[/api/predict] Internal error:", error?.stack || (typeof err === 'string' ? err : error.message));
    return NextResponse.json(
      { error: "حدث خطأ غير متوقع في الخادم. جرّبي لاحقًا." },
      { status: 500 }
    );
  }
}
