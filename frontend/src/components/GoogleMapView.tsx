'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  GoogleMap,
  useJsApiLoader,
  Marker,
  InfoWindow,
  Polygon,
} from '@react-google-maps/api'
import { useI18n, useT } from '@/i18n/useTranslations'
import { CITY_CENTER, type CityKey } from '@/lib/geo'
import SARIcon from '@/components/SARIcon'

export type Bbox = [number, number, number, number] // [minLng, minLat, maxLng, maxLat]
export type Top3Area = { lat: number; lng: number; label: string }

const DEFAULT_CENTER = { lat: 26.39, lng: 50.19 }
const DEFAULT_ZOOM = 11
const MAP_CONTAINER_STYLE = { width: '100%', height: '100%', minHeight: 460 }

type Props = {
  city?: CityKey
  district?: string
  coords?: { lat: number; lng: number } | null
  result?: { pricePerSqm: number; total: number; range: [number, number]; verdict: string } | null
  onSelect?: (c: { lat: number; lng: number }) => void
  mode?: 'point' | 'bbox'
  onBboxSelect?: (bbox: Bbox) => void
  selectedBbox?: Bbox | null
  top3Areas?: Top3Area[] | null
  /** إظهار أسماء الأحياء على الخريطة (بدل 1/2/3) */
  showDistrictNames?: boolean
  /** عند الضغط على marker من Top 3 (0, 1, 2) */
  onTop3MarkerClick?: (index: number) => void
}

export default function GoogleMapView({
  city = 'الدمام',
  coords,
  result,
  mode = 'point',
  onSelect,
  onBboxSelect,
  selectedBbox,
  top3Areas,
  showDistrictNames = false,
  onTop3MarkerClick,
}: Props) {
  const { locale } = useI18n()
  const t = useT()
  const isAr = locale === 'ar'
  const apiKey = (process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY ?? '').trim()
  const { isLoaded, loadError } = useJsApiLoader({
    googleMapsApiKey: apiKey,
  })
  const [bboxCorner1, setBboxCorner1] = useState<{ lat: number; lng: number } | null>(null)
  const [bboxCorner2, setBboxCorner2] = useState<{ lat: number; lng: number } | null>(null)
  const [map, setMap] = useState<google.maps.Map | null>(null)
  const [infoOpen, setInfoOpen] = useState(false)

  const center = useMemo(() => {
    if (coords?.lat != null && coords?.lng != null) return { lat: coords.lat, lng: coords.lng }
    const c = CITY_CENTER[city]
    if (c) return { lat: c[0], lng: c[1] }
    return DEFAULT_CENTER
  }, [coords, city])

  useEffect(() => {
    if (mode !== 'bbox' || !bboxCorner1 || !bboxCorner2 || !onBboxSelect) return
    const minLng = Math.min(bboxCorner1.lng, bboxCorner2.lng)
    const maxLng = Math.max(bboxCorner1.lng, bboxCorner2.lng)
    const minLat = Math.min(bboxCorner1.lat, bboxCorner2.lat)
    const maxLat = Math.max(bboxCorner1.lat, bboxCorner2.lat)
    onBboxSelect([minLng, minLat, maxLng, maxLat])
    setBboxCorner1(null)
    setBboxCorner2(null)
  }, [mode, bboxCorner1, bboxCorner2, onBboxSelect])

  useEffect(() => {
    if (result && coords && map) {
      setInfoOpen(true)
      map.panTo({ lat: coords.lat, lng: coords.lng })
      map.setZoom(15)
    }
  }, [result, coords, map])

  const onMapClick = useCallback(
    (e: google.maps.MapMouseEvent) => {
      const lat = e.latLng?.lat()
      const lng = e.latLng?.lng()
      if (lat == null || lng == null || isNaN(lat) || isNaN(lng)) return
      if (mode === 'bbox') {
        if (!bboxCorner1) setBboxCorner1({ lat, lng })
        else setBboxCorner2({ lat, lng })
        return
      }
      onSelect?.({ lat, lng })
    },
    [mode, bboxCorner1, onSelect]
  )

  const bboxPath = useMemo(() => {
    if (selectedBbox && selectedBbox.length === 4) {
      const [minLng, minLat, maxLng, maxLat] = selectedBbox
      return [
        { lat: minLat, lng: minLng },
        { lat: minLat, lng: maxLng },
        { lat: maxLat, lng: maxLng },
        { lat: maxLat, lng: minLng },
        { lat: minLat, lng: minLng },
      ]
    }
    if (bboxCorner1 && bboxCorner2) {
      const minLng = Math.min(bboxCorner1.lng, bboxCorner2.lng)
      const maxLng = Math.max(bboxCorner1.lng, bboxCorner2.lng)
      const minLat = Math.min(bboxCorner1.lat, bboxCorner2.lat)
      const maxLat = Math.max(bboxCorner1.lat, bboxCorner2.lat)
      return [
        { lat: minLat, lng: minLng },
        { lat: minLat, lng: maxLng },
        { lat: maxLat, lng: maxLng },
        { lat: maxLat, lng: minLng },
        { lat: minLat, lng: minLng },
      ]
    }
    return null
  }, [selectedBbox, bboxCorner1, bboxCorner2])

  if (loadError) {
    return (
      <div className="flex items-center justify-center bg-slate-100 dark:bg-ink-800 rounded-2xl min-h-[460px] p-8 text-center">
        <p className="text-red-600 dark:text-red-400">
          {isAr ? 'فشل تحميل خريطة Google.' : 'Failed to load Google Maps.'}
        </p>
      </div>
    )
  }

  if (!isLoaded || !apiKey) {
    return (
      <div className="flex items-center justify-center bg-slate-100 dark:bg-ink-800 rounded-2xl min-h-[460px] p-8">
        <p className="text-slate-600 dark:text-slate-400">
          {isAr ? 'جاري تحميل الخريطة...' : 'Loading map...'}
        </p>
      </div>
    )
  }

  return (
    <div
      className="relative rounded-2xl overflow-hidden"
      style={{ minHeight: 460, height: 'clamp(460px, 62vh, 700px)' }}
      dir={isAr ? 'rtl' : 'ltr'}
    >
      <GoogleMap
        mapContainerStyle={MAP_CONTAINER_STYLE}
        center={center}
        zoom={DEFAULT_ZOOM}
        onClick={onMapClick}
        onLoad={setMap}
        options={{
          zoomControl: true,
          mapTypeControl: true,
          fullscreenControl: true,
          streetViewControl: false,
        }}
      >
        {bboxPath && (
          <Polygon
            paths={bboxPath}
            options={{
              fillColor: '#2563eb',
              fillOpacity: 0.25,
              strokeColor: '#1d4ed8',
              strokeWeight: 3,
            }}
          />
        )}
        {top3Areas && top3Areas.length > 0 && mode === 'point' && top3Areas.map((area, i) => (
          <Marker
            key={`${area.lat}-${area.lng}-${i}`}
            position={{ lat: area.lat, lng: area.lng }}
            label={{
              text: showDistrictNames ? (area.label || String(i + 1)) : String(i + 1),
              color: 'white',
              fontWeight: '700',
            }}
            icon={{
              path: 0,
              scale: 16,
              fillColor: i === 0 ? '#16a34a' : i === 1 ? '#2563eb' : '#9333ea',
              fillOpacity: 1,
              strokeColor: 'white',
              strokeWeight: 3,
            }}
            onClick={() => onTop3MarkerClick?.(i)}
          />
        ))}
        {mode === 'point' && coords && !(top3Areas && top3Areas.length > 0) && (
          <>
            <Marker
              position={{ lat: coords.lat, lng: coords.lng }}
              onClick={() => setInfoOpen(true)}
            />
            {result && infoOpen && (
              <InfoWindow
                position={{ lat: coords.lat, lng: coords.lng }}
                onCloseClick={() => setInfoOpen(false)}
              >
                <div className="text-sm leading-6 space-y-2 min-w-[200px] p-1">
                  <div className="font-bold text-base text-raboo3-700 border-b border-slate-200 pb-2">
                    {t.predict.map.popup_title}
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between gap-4">
                      <span className="text-slate-600">{t.predict.result.price_psm}:</span>
                      <span className="font-semibold text-ink-900">
                        {result.pricePerSqm.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} <SARIcon />
                      </span>
                    </div>
                    <div className="flex justify-between gap-4">
                      <span className="text-slate-600">{t.predict.result.total_price}:</span>
                      <span className="font-semibold text-ink-900">
                        {result.total.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} <SARIcon />
                      </span>
                    </div>
                    <div className="flex justify-between gap-4">
                      <span className="text-slate-600">{t.predict.result.range}:</span>
                      <span className="font-semibold text-ink-900">
                        {result.range[0].toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')}–
                        {result.range[1].toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')} <SARIcon />
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
              </InfoWindow>
            )}
          </>
        )}
      </GoogleMap>

      {mode === 'bbox' && !selectedBbox && (
        <div
          className="absolute top-3 left-3 right-3 z-10 px-4 py-3 rounded-xl bg-blue-600 text-white shadow-lg text-center text-sm font-medium"
          style={{ position: 'absolute' }}
        >
          {isAr
            ? 'انقري النقطة الأولى على الخريطة ثم النقطة الثانية لرسم مستطيل النطاق. سيتم تقدير أسعار الأراضي داخل هذا النطاق.'
            : 'Click the first point on the map, then the second point to draw the search area. Land prices will be estimated within this range.'}
        </div>
      )}
      {mode === 'bbox' && selectedBbox && (
        <div
          className="absolute top-3 left-3 z-10 px-3 py-2 rounded-lg bg-green-700 text-white shadow text-xs font-medium"
          style={{ position: 'absolute' }}
        >
          {isAr
            ? '✓ تم تحديد النطاق. اضغطي «تنفيذ التقدير» في اللوحة.'
            : '✓ Range set. Click "Run valuation" in the panel.'}
        </div>
      )}
      <div
        className="absolute bottom-2 left-2 px-2 py-1 rounded bg-white/90 text-ink-900 text-xs"
        style={{ position: 'absolute', opacity: 0.8 }}
      >
        Google Maps
      </div>
    </div>
  )
}
