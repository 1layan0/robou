const STORAGE_KEY = 'robou_favorites';

export type FavoriteItem = {
  city_ar: string;
  district_ar: string;
};

export function getFavorites(): FavoriteItem[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (x: unknown) =>
        x != null &&
        typeof x === 'object' &&
        typeof (x as FavoriteItem).city_ar === 'string' &&
        typeof (x as FavoriteItem).district_ar === 'string'
    );
  } catch {
    return [];
  }
}

export function addFavorite(city_ar: string, district_ar: string): void {
  const list = getFavorites();
  if (list.some((f) => f.city_ar === city_ar && f.district_ar === district_ar)) return;
  list.push({ city_ar, district_ar });
  if (typeof window !== 'undefined') window.localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
}

export function removeFavorite(city_ar: string, district_ar: string): void {
  const list = getFavorites().filter((f) => !(f.city_ar === city_ar && f.district_ar === district_ar));
  if (typeof window !== 'undefined') window.localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
}

export function isFavorite(city_ar: string, district_ar: string): boolean {
  return getFavorites().some((f) => f.city_ar === city_ar && f.district_ar === district_ar);
}
