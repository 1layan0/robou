'use client';

import 'mapbox-gl/dist/mapbox-gl.css';
import 'maplibre-gl/dist/maplibre-gl.css';
import Map, { MapRef, Marker, Popup, Source, Layer } from 'react-map-gl';
import mapboxgl from 'mapbox-gl';
import * as maplibregl from 'maplibre-gl';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { LayerProps } from 'react-map-gl';
import { CITY_CENTER, CITY_BBOX, geocodeDistrictInCity, type CityKey } from '@/lib/geo';
import { useI18n, useT } from '@/i18n/useTranslations';
import SARIcon from '@/components/SARIcon';

const MB_TOKEN = (process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? '').trim();
const isValidMbToken = (tok: string) => tok.startsWith('pk.') && tok.length > 60;

export type Bbox = [number, number, number, number]; // [minLng, minLat, maxLng, maxLat]
export type Top3Area = { lat: number; lng: number; label: string };

type Props = {
  city?: CityKey;
  district?: string;
  coords?: { lat: number; lng: number } | null;
  result?: { pricePerSqm: number; total: number; range: [number, number]; verdict: string } | null;
  onSelect?: (c: { lat: number; lng: number }) => void;
  theme?: 'light' | 'dark';
  /** 'bbox' = draw rectangle (two clicks), then onBboxSelect; 'point' = single marker (default) */
  mode?: 'point' | 'bbox';
  onBboxSelect?: (bbox: Bbox) => void;
  selectedBbox?: Bbox | null;
  top3Areas?: Top3Area[] | null;
};

export default function MapView({
  city = 'الدمام',
  district,
  coords,
  result,
  onSelect,
  mode = 'point',
  onBboxSelect,
  selectedBbox,
  top3Areas,
}: Props) {
  const t = useT();
  const { locale } = useI18n();
  const isAr = locale === 'ar';
  const engine: 'mapbox' | 'maplibre' = isValidMbToken(MB_TOKEN) ? 'mapbox' : 'maplibre';
  const ref = useRef<MapRef>(null);
  const [marker, setMarker] = useState<{ lat: number; lng: number } | null>(coords ?? null);
  const [showPopup, setShowPopup] = useState(false);
  const [bboxCorner1, setBboxCorner1] = useState<[number, number] | null>(null);
  const [bboxCorner2, setBboxCorner2] = useState<[number, number] | null>(null);

  if (engine === 'mapbox') {
    mapboxgl.accessToken = MB_TOKEN;
  }

  // Geocode district when district/city changes and coords is null (point mode only)
  useEffect(() => {
    if (mode !== 'point' || !city || !district?.trim() || coords) return;

    const geocode = async () => {
      const geocoded = await geocodeDistrictInCity(city, district.trim());
      if (geocoded && typeof geocoded.lat === 'number' && typeof geocoded.lng === 'number' && !isNaN(geocoded.lat) && !isNaN(geocoded.lng)) {
        setMarker(geocoded);
        onSelect?.(geocoded);
        const map = ref.current?.getMap() as mapboxgl.Map | maplibregl.Map | null;
        if (map && 'flyTo' in map) {
          map.flyTo({ center: [geocoded.lng, geocoded.lat], zoom: 14, duration: 900 });
        }
      }
    };

    geocode();
  }, [mode, city, district, coords, onSelect]);

  useEffect(() => {
    if (mode !== 'point') return;
    if (coords && typeof coords.lat === 'number' && typeof coords.lng === 'number' && !isNaN(coords.lat) && !isNaN(coords.lng)) {
      setMarker(coords);
      const map = ref.current?.getMap() as mapboxgl.Map | maplibregl.Map | null;
      if (map && 'flyTo' in map) {
        map.flyTo({ center: [coords.lng, coords.lat], zoom: 15, duration: 1000 });
      }
    }
  }, [mode, coords]);

  useEffect(() => {
    if (mode !== 'point') return;
    if (result && marker && typeof marker.lat === 'number' && typeof marker.lng === 'number' && !isNaN(marker.lat) && !isNaN(marker.lng)) {
      setShowPopup(true);
      const map = ref.current?.getMap() as mapboxgl.Map | maplibregl.Map | null;
      if (map && 'flyTo' in map) {
        map.flyTo({ center: [marker.lng, marker.lat], zoom: 15.5, duration: 1000 });
      }
    }
  }, [result, marker]);

  useEffect(() => {
    if (mode !== 'point') return;
    const map = ref.current?.getMap() as mapboxgl.Map | maplibregl.Map | null;
    const c = CITY_CENTER[city];
    if (map && c && 'flyTo' in map && !coords) {
      map.flyTo({ center: [c[1], c[0]], zoom: 12, duration: 800 });
    }
  }, [mode, city, coords]);

  // Bbox: when both corners set, compute bbox and notify parent; then clear for next draw
  useEffect(() => {
    if (mode !== 'bbox' || !bboxCorner1 || !bboxCorner2 || !onBboxSelect) return;
    const [lng1, lat1] = bboxCorner1;
    const [lng2, lat2] = bboxCorner2;
    const minLng = Math.min(lng1, lng2);
    const maxLng = Math.max(lng1, lng2);
    const minLat = Math.min(lat1, lat2);
    const maxLat = Math.max(lat1, lat2);
    onBboxSelect([minLng, minLat, maxLng, maxLat]);
    setBboxCorner1(null);
    setBboxCorner2(null);
  }, [mode, bboxCorner1, bboxCorner2, onBboxSelect]);

  const geocoderRef = useRef<{ setBbox?: (bbox: [number, number, number, number]) => void } | null>(null);

  useEffect(() => {
    const map = ref.current?.getMap() as (mapboxgl.Map | maplibregl.Map) & { __raboo3_init?: boolean } | null;
    if (!map) return;
    if (map.__raboo3_init) return;
    map.__raboo3_init = true;

    const lib = engine === 'mapbox' ? mapboxgl : maplibregl;

    if ('addControl' in map) {
      map.addControl(new lib.NavigationControl({ visualizePitch: true }) as any, 'top-right');
      map.addControl(new lib.FullscreenControl() as any, 'top-right');

      if (engine === 'mapbox') {
        map.addControl(new lib.GeolocateControl({ trackUserLocation: true }) as any, 'top-right');

        try {
          import('@mapbox/mapbox-gl-geocoder').then(({ default: MapboxGeocoder }) => {
            const bbox = CITY_BBOX[city];
            const geocoder = new MapboxGeocoder({
              accessToken: MB_TOKEN,
              mapboxgl: mapboxgl as any,
              marker: false,
              language: 'ar',
              countries: 'sa',
              placeholder: 'ابحث عن حي/عنوان…',
              bbox: bbox ? [bbox[0], bbox[1], bbox[2], bbox[3]] : undefined,
            });

            geocoderRef.current = geocoder as { setBbox?: (bbox: [number, number, number, number]) => void };

            if ('addControl' in map) {
              map.addControl(geocoder as any, 'top-left');
            }

            geocoder.on('result', (e: { result: { center: [number, number] } }) => {
              const [lng, lat] = e.result.center;
              const next = { lat, lng };
              setMarker(next);
              onSelect?.(next);
              if ('flyTo' in map) {
                map.flyTo({ center: [lng, lat], zoom: 15, duration: 800 });
              }
            });
          }).catch(() => {
            // ignore
          });
        } catch {
          // ignore
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [engine, onSelect]);

  // Update geocoder bbox when city changes
  useEffect(() => {
    if (engine === 'mapbox' && geocoderRef.current && city) {
      const bbox = CITY_BBOX[city];
      if (bbox && typeof geocoderRef.current.setBbox === 'function') {
        try {
          geocoderRef.current.setBbox([bbox[0], bbox[1], bbox[2], bbox[3]]);
        } catch {
          // ignore
        }
      }
    }
  }, [city, engine]);

  const styleUrl: string | any =
    engine === 'mapbox'
      ? 'mapbox://styles/mapbox/satellite-streets-v12'
      : {
          version: 8,
          sources: {
            'osm-tiles': {
              type: 'raster',
              tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
              tileSize: 256,
              attribution: '© OpenStreetMap contributors',
            },
          },
          layers: [
            {
              id: 'osm-tiles-layer',
              type: 'raster',
              source: 'osm-tiles',
              minzoom: 0,
              maxzoom: 22,
            },
          ],
        };

  const commonProps = useMemo(
    () =>
      engine === 'mapbox'
        ? { mapboxAccessToken: MB_TOKEN, mapLib: mapboxgl as unknown }
        : { mapLib: maplibregl as unknown },
    [engine]
  );

  const accuracyCircle = useMemo(() => {
    if (!marker || typeof marker.lat !== 'number' || typeof marker.lng !== 'number' || isNaN(marker.lat) || isNaN(marker.lng)) {
      return null;
    }
    return {
      type: 'FeatureCollection' as const,
      features: [
        {
          type: 'Feature' as const,
          geometry: {
            type: 'Point' as const,
            coordinates: [marker.lng, marker.lat] as [number, number],
          },
          properties: {},
        },
      ],
    };
  }, [marker]);

  const circleLayer: LayerProps = {
    id: 'accuracy-circle',
    type: 'circle',
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 40, 15, 60, 18, 100],
      'circle-color': '#16a34a',
      'circle-opacity': 0.2,
      'circle-stroke-width': 3,
      'circle-stroke-color': '#16a34a',
      'circle-stroke-opacity': 0.6,
    },
  };

  const bboxPolygon = useMemo(() => {
    let minLng: number, minLat: number, maxLng: number, maxLat: number;
    if (selectedBbox && selectedBbox.length === 4) {
      [minLng, minLat, maxLng, maxLat] = selectedBbox;
    } else if (mode === 'bbox' && bboxCorner1 && bboxCorner2) {
      const [lng1, lat1] = bboxCorner1;
      const [lng2, lat2] = bboxCorner2;
      minLng = Math.min(lng1, lng2);
      maxLng = Math.max(lng1, lng2);
      minLat = Math.min(lat1, lat2);
      maxLat = Math.max(lat1, lat2);
    } else {
      return null;
    }
    return {
      type: 'Feature' as const,
      geometry: {
        type: 'Polygon' as const,
        coordinates: [[[minLng, minLat], [maxLng, minLat], [maxLng, maxLat], [minLng, maxLat], [minLng, minLat]]],
      },
      properties: {},
    };
  }, [mode, selectedBbox, bboxCorner1, bboxCorner2]);

  const bboxFillLayer: LayerProps = {
    id: 'bbox-fill',
    type: 'fill',
    paint: {
      'fill-color': '#2563eb',
      'fill-opacity': 0.25,
      'fill-outline-color': '#1d4ed8',
    } as Record<string, unknown>,
  };

  const handleMapClick = (e: { lngLat: { lat: number; lng: number } }) => {
    const lat = e.lngLat.lat;
    const lng = e.lngLat.lng;
    if (typeof lat !== 'number' || typeof lng !== 'number' || isNaN(lat) || isNaN(lng)) return;

    if (mode === 'bbox') {
      if (!bboxCorner1) {
        setBboxCorner1([lng, lat]);
      } else {
        setBboxCorner2([lng, lat]);
      }
      return;
    }

    const next = { lat, lng };
    setMarker(next);
    setShowPopup(false);
    onSelect?.(next);
  };

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        minHeight: 460,
        height: 'clamp(460px,62vh,700px)',
        borderRadius: 16,
        overflow: 'hidden',
      }}
      dir={isAr ? 'rtl' : 'ltr'}
    >
      <Map
        ref={ref}
        {...(commonProps as any)}
        mapStyle={styleUrl as any}
        initialViewState={{ latitude: 26.392, longitude: 50.196, zoom: 11 }}
        style={{ width: '100%', height: '100%' }}
        attributionControl
        cooperativeGestures
        onClick={handleMapClick}
      >
        {bboxPolygon && (
          <Source id="bbox-source" type="geojson" data={{ type: 'FeatureCollection', features: [bboxPolygon] }}>
            <Layer {...bboxFillLayer} />
          </Source>
        )}
        {accuracyCircle && mode === 'point' && (
          <Source id="accuracy-source" type="geojson" data={accuracyCircle}>
            <Layer {...circleLayer} />
          </Source>
        )}

        {top3Areas && top3Areas.length > 0 && top3Areas.map((area, i) => (
          <Marker key={i} longitude={area.lng} latitude={area.lat} anchor="bottom">
            <div
              style={{
                background: i === 0 ? '#16a34a' : i === 1 ? '#2563eb' : '#9333ea',
                color: 'white',
                fontWeight: 700,
                width: 32,
                height: 32,
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '3px solid white',
                boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
              }}
            >
              {i + 1}
            </div>
          </Marker>
        ))}
        {mode === 'point' && marker && typeof marker.lat === 'number' && typeof marker.lng === 'number' && !isNaN(marker.lat) && !isNaN(marker.lng) && (
          <>
            <Marker longitude={marker.lng} latitude={marker.lat} anchor="bottom">
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: '50% 50% 50% 0',
                  backgroundColor: '#16a34a',
                  border: '4px solid white',
                  boxShadow: '0 6px 20px rgba(0,0,0,0.5), 0 0 0 2px rgba(22,163,74,0.3)',
                  transform: 'rotate(-45deg)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  position: 'relative',
                }}
              >
                <div
                  style={{
                    transform: 'rotate(45deg)',
                    width: 14,
                    height: 14,
                    borderRadius: '50%',
                    backgroundColor: 'white',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                  }}
                />
                <div
                  style={{
                    position: 'absolute',
                    bottom: -8,
                    left: '50%',
                    transform: 'translateX(-50%) rotate(45deg)',
                    width: 0,
                    height: 0,
                    borderLeft: '6px solid transparent',
                    borderRight: '6px solid transparent',
                    borderTop: '8px solid #16a34a',
                  }}
                />
              </div>
            </Marker>
            {result && showPopup && (
              <Popup
                longitude={marker.lng}
                latitude={marker.lat}
                closeButton
                closeOnClick={false}
                onClose={() => setShowPopup(false)}
                anchor="bottom"
                offset={20}
              >
                <div className="text-sm leading-6 space-y-2 min-w-[200px]">
                  <div className="font-bold text-base text-raboo3-700 border-b border-slate-200 pb-2">
                    {t.predict.map.popup_title}
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-slate-600">{t.predict.result.price_psm}:</span>
                      <span className="font-semibold text-ink-900">
                        {result.pricePerSqm.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} <SARIcon />
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-600">{t.predict.result.total_price}:</span>
                      <span className="font-semibold text-ink-900">
                        {result.total.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} <SARIcon />
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-600">{t.predict.result.range}:</span>
                      <span className="font-semibold text-ink-900">
                        {result.range[0].toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')}–{result.range[1].toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} <SARIcon />
                      </span>
                    </div>
                  </div>
                  <div
                    className={`mt-2 px-3 py-1 rounded-full text-xs font-semibold text-center ${
                      result.verdict === 'فرصة' || result.verdict === 'Opportunity'
                        ? 'bg-amber-100 text-amber-700'
                        : result.verdict === 'عادل' || result.verdict === 'Fair'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                    }`}
                  >
                    {result.verdict}
                  </div>
                </div>
              </Popup>
            )}
          </>
        )}
      </Map>

      {mode === 'bbox' && !selectedBbox && (
        <div
          style={{ position: 'absolute', top: 12, left: 12, right: 12, zIndex: 10 }}
          className="px-4 py-3 rounded-xl bg-blue-600 text-white shadow-lg text-center text-sm font-medium"
        >
          {isAr ? 'انقر النقطة الأولى على الخريطة ثم النقطة الثانية لرسم مستطيل النطاق. سيتم تقدير أسعار الأراضي داخل هذا النطاق.' : 'Click the first point on the map, then the second point to draw the search area. Land prices will be estimated within this range.'}
        </div>
      )}
      {mode === 'bbox' && selectedBbox && (
        <div
          style={{ position: 'absolute', top: 12, left: 12, zIndex: 10 }}
          className="px-3 py-2 rounded-lg bg-green-700 text-white shadow text-xs font-medium"
        >
          {isAr ? '✓ تم تحديد النطاق. اضغطي «تنفيذ التقدير» في اللوحة.' : '✓ Range set. Click "Run valuation" in the panel.'}
        </div>
      )}
      {engine === 'maplibre' && (
        <div
          style={{ position: 'absolute', top: mode === 'bbox' ? 72 : 12, left: 12, fontSize: 11 }}
          className="px-3 py-2 rounded-lg bg-amber-100 border border-amber-300 text-amber-800 shadow-lg"
        >
          <div className="font-semibold mb-1">⚠️ {isAr ? 'للخريطة الاحترافية:' : 'For professional map:'}</div>
          <div className="text-xs">{isAr ? 'أضيفي مفتاح Mapbox صالح في .env.local' : 'Add a valid Mapbox token in .env.local'}</div>
        </div>
      )}
      <div
        style={{ position: 'absolute', bottom: 8, left: 12, fontSize: 12, opacity: 0.7 }}
        className="px-2 py-1 rounded bg-white/80 text-ink-900"
      >
        {engine === 'mapbox' ? t.predict.map.engine_mapbox : t.predict.map.engine_maplibre}
      </div>
    </div>
  );
}
