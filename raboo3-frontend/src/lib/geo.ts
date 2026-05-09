export type CityKey = "الدمام" | "الخبر" | "الظهران";

export const CITY_CENTER: Record<CityKey, [number, number]> = {
  "الدمام": [26.43, 50.10],
  "الخبر": [26.29, 50.21],
  "الظهران": [26.30, 50.15],
};

// Bounding boxes [minLng, minLat, maxLng, maxLat] to scope geocoding per city
export const CITY_BBOX: Record<CityKey, [number, number, number, number]> = {
  "الدمام": [49.95, 26.30, 50.25, 26.55],
  "الخبر": [50.14, 26.24, 50.30, 26.36],
  "الظهران": [50.08, 26.25, 50.22, 26.37],
};

// Reverse-geocode a lat/lng → city name (Mapbox first, MapLibre/Nominatim fallback)
export async function resolveCityFromCoords(lat: number, lng: number): Promise<CityKey | null> {
  const token = (process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "").trim();

  // 1) Mapbox reverse
  try {
    if (token.startsWith("pk.")) {
      const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${lng},${lat}.json?access_token=${token}&language=ar&types=place,locality,neighborhood,address,poi&country=sa`;
      const r = await fetch(url);
      const j = await r.json();
      const txt = JSON.stringify(j);
      if (txt.includes("الدمام")) return "الدمام";
      if (txt.includes("الخبر")) return "الخبر";
      if (txt.includes("الظهران")) return "الظهران";
    }
  } catch {}

  // 2) Fallback: Nominatim
  try {
    const u = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&accept-language=ar`;
    const r2 = await fetch(u, { headers: { "User-Agent": "raboo3-graduation" } });
    const j2 = await r2.json();
    const name = (j2?.address?.city || j2?.address?.town || j2?.address?.suburb || j2?.display_name || "") as string;
    if (name.includes("الدمام")) return "الدمام";
    if (name.includes("الخبر")) return "الخبر";
    if (name.includes("الظهران")) return "الظهران";
  } catch {}

  return null;
}

// Forward geocode district within a city bbox (Mapbox first, fallback to city center)
export async function geocodeDistrictInCity(city: CityKey, district: string): Promise<{lat:number; lng:number} | null> {
  const token = (process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "").trim();

  if (token.startsWith("pk.")) {
    const bbox = CITY_BBOX[city];
    const q = encodeURIComponent(`${district}, ${city}, المنطقة الشرقية, السعودية`);
    const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${q}.json?access_token=${token}&language=ar&bbox=${bbox.join(",")}&types=place,neighborhood,address,poi&country=sa&limit=1`;

    try {
      const r = await fetch(url);
      const j = await r.json();
      const c = j?.features?.[0]?.center;
      if (Array.isArray(c) && c.length >= 2) {
        const [lng, lat] = c;
        if (typeof lat === 'number' && typeof lng === 'number' && !isNaN(lat) && !isNaN(lng)) {
          return { lat, lng };
        }
      }
    } catch {}
  }

  // fallback: city center
  const [lat, lng] = CITY_CENTER[city];
  return { lat, lng };
}

// Legacy export for backward compatibility
export const CITY_COORDS = CITY_CENTER;
export const DISTRICT_HINTS: Record<string, [number, number]> = {
  "الدمام|الحسام": [26.453, 50.087],
  "الظهران|الحزام الذهبي": [26.306, 50.149],
  "الخبر|العقربية": [26.297, 50.211],
};
