'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { useI18n } from '@/i18n/useTranslations';
import type { LandCardData } from './LandCard';

const MapView = dynamic(() => import('@/components/MapView'), {
  ssr: false,
  loading: () => <div className="card h-full min-h-[600px] animate-pulse flex items-center justify-center" aria-busy="true" />,
});

interface SearchMapProps {
  results: LandCardData[];
  selectedId?: string;
  onMarkerClick?: (id: string) => void;
  highlightedId?: string;
}

export default function SearchMap({ results, selectedId, onMarkerClick, highlightedId }: SearchMapProps) {
  const { locale } = useI18n();
  const isAr = locale === 'ar';
  const [mapReady, setMapReady] = useState(false);

  // Calculate center from results or default to Eastern Province center
  const centerCoords = results.length > 0
    ? {
        lat: results.reduce((sum, r) => sum + r.coordinates.lat, 0) / results.length,
        lng: results.reduce((sum, r) => sum + r.coordinates.lng, 0) / results.length,
      }
    : { lat: 26.392, lng: 50.196 };

  const selectedCoords = selectedId
    ? results.find(r => r.id === selectedId)?.coordinates || centerCoords
    : centerCoords;

  useEffect(() => {
    setMapReady(true);
  }, []);

  return (
    <div className="relative h-full min-h-[600px] rounded-xl overflow-hidden" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="h-full w-full">
        <MapView
          city={results[0]?.city || 'الدمام'}
          coords={selectedCoords}
        />
      </div>
      {results.length > 0 && (
        <div className="absolute bottom-4 left-4 right-4 z-10 pointer-events-none">
          <div className="bg-white/95 dark:bg-ink-900/95 backdrop-blur-md rounded-xl p-3 shadow-lg border border-slate-200 dark:border-slate-700">
            <div className="text-xs text-slate-600 dark:text-slate-400">
              {isAr ? `عرض ${results.length} نتيجة على الخريطة` : `Showing ${results.length} results on map`}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

