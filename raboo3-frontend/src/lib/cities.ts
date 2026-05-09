export const CITIES = ["الدمام", "الظهران", "الخبر"] as const;

export type City = (typeof CITIES)[number];

export const CITY_COORDS: Record<City, [number, number]> = {
  "الدمام": [26.43, 50.1],
  "الظهران": [26.3, 50.15],
  "الخبر": [26.29, 50.21],
};
