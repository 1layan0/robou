'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { useI18n, useT } from '@/i18n/useTranslations';

const MapView = dynamic(() => import('@/components/MapView'), { ssr: false });

export default function GISLayersPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';

  const [layers, setLayers] = useState([
    { id: 1, name: 'District Boundaries', enabled: true, opacity: 100 },
    { id: 2, name: 'Price Heatmap', enabled: true, opacity: 75 },
    { id: 3, name: 'Facilities', enabled: false, opacity: 100 },
    { id: 4, name: 'Road Network', enabled: true, opacity: 50 },
  ]);

  const toggleLayer = (id: number) => {
    setLayers(layers.map(layer => 
      layer.id === id ? { ...layer, enabled: !layer.enabled } : layer
    ));
  };

  const updateOpacity = (id: number, opacity: number) => {
    setLayers(layers.map(layer => 
      layer.id === id ? { ...layer, opacity } : layer
    ));
  };

  return (
    <main className="section" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container space-y-8">
        <header className="space-y-3">
          <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl">
            {t.admin_gis.title}
          </h1>
          <p className="text-base leading-relaxed text-slate-600 dark:text-slate-300">
            {t.admin_gis.subtitle}
          </p>
        </header>

        <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
          <div className="card p-6 space-y-4">
            <h2 className="text-xl font-bold text-ink-900 dark:text-white">{t.admin_gis.layers}</h2>
            
            <div className="space-y-3">
              {layers.map((layer) => (
                <div key={layer.id} className="p-4 border border-slate-200 dark:border-slate-800 rounded-xl">
                  <div className="flex items-center justify-between mb-3">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={layer.enabled}
                        onChange={() => toggleLayer(layer.id)}
                        className="h-4 w-4 rounded border-slate-300 text-raboo3-600 focus:ring-raboo3-500"
                      />
                      <span className="font-semibold text-ink-900 dark:text-white">{layer.name}</span>
                    </label>
                  </div>
                  {layer.enabled && (
                    <div className="space-y-2">
                      <label className="block text-sm text-slate-600 dark:text-slate-400">
                        {t.admin_gis.opacity}: {layer.opacity}%
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={layer.opacity}
                        onChange={(e) => updateOpacity(layer.id, Number(e.target.value))}
                        className="w-full"
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>

            <button className="w-full btn btn-primary mt-4">
              {t.admin_gis.save_changes}
            </button>
          </div>

          <div className="card p-0 overflow-hidden" style={{ height: '600px' }}>
            <MapView city="الدمام" />
          </div>
        </div>
      </div>
    </main>
  );
}

