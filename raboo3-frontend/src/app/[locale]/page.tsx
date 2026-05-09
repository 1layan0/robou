'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';
import { motion } from 'framer-motion';
import { useI18n, useT } from '@/i18n/useTranslations';
import Hero from '@/components/Hero';
import DataSourcesStrip from '@/components/DataSourcesStrip';
import FeatureCard from '@/components/FeatureCard';

const PriceIcon = () => (
  <svg
    aria-hidden="true"
    viewBox="0 0 24 24"
    className="h-7 w-7 text-raboo3-700 dark:text-raboo3-300"
  >
    <rect x="3" y="4" width="6" height="16" rx="1.5" className="fill-current opacity-30" />
    <rect x="10" y="8" width="5" height="12" rx="1.5" className="fill-current opacity-60" />
    <rect x="16" y="11" width="5" height="9" rx="1.5" className="fill-current" />
  </svg>
);

const MapAnalysisIcon = () => (
  <svg
    aria-hidden="true"
    viewBox="0 0 24 24"
    className="h-7 w-7 text-raboo3-700 dark:text-raboo3-300"
  >
    <path
      d="M4 5.5 9 4l6 1.5 5-1.5v14l-5 1.5L9 18 4 19.5V5.5Z"
      className="fill-none stroke-current"
      strokeWidth="1.5"
    />
    <circle cx="10" cy="11" r="1.4" className="fill-current" />
    <circle cx="15" cy="9" r="1.2" className="fill-current opacity-70" />
    <circle cx="16.5" cy="14" r="1" className="fill-current opacity-50" />
    <path
      d="M10 11 15 9l1.5 5"
      className="fill-none stroke-current"
      strokeWidth="1.5"
      strokeLinecap="round"
    />
  </svg>
);

export default function HomePage() {
  const { locale } = useI18n();
  const t = useT();
  const [city, setCity] = useState<'الدمام' | 'الظهران' | 'الخبر' | undefined>('الدمام');
  const isAr = locale === 'ar';

  const featureList = [
    {
      title: t.home.feature_title_1,
      description: t.home.feature_desc_1,
      icon: <PriceIcon />,
    },
    {
      title: t.home.feature_title_2,
      description: t.home.feature_desc_2,
      icon: <MapAnalysisIcon />,
    },
  ];

  return (
    <main className="space-y-20" dir={isAr ? 'rtl' : 'ltr'}>
      <Hero />

      <section id="features" className="section relative">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-slate-50/30 to-transparent dark:via-ink-900/20" />
        <div className="container relative space-y-12">
          <motion.div
            className="mx-auto max-w-3xl text-center"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl md:text-5xl">
              {t.home.why_raboo3.split(t.brand.name).map((part, i, arr) => (
                <span key={i}>
                  {part}
                  {i < arr.length - 1 && (
                    <span className="bg-gradient-to-r from-raboo3-600 to-raboo3-500 bg-clip-text text-transparent">
                      {t.brand.name}
                    </span>
                  )}
                </span>
              ))}
            </h2>
            <p className="mt-4 text-base leading-relaxed text-slate-600 dark:text-slate-300 sm:text-lg">
              {t.home.why_raboo3_subtitle}
            </p>
          </motion.div>
          <div className="grid gap-6 md:grid-cols-2">
            {featureList.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <FeatureCard icon={feature.icon} title={feature.title} description={feature.description} />
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section id="data-sources">
        <DataSourcesStrip />
      </section>
    </main>
  );
}

