'use client';

import Link from 'next/link';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
import { useEffect } from 'react';
import { useI18n, useT } from '@/i18n/useTranslations';

export default function Hero() {
  const t = useT();
  const { locale } = useI18n();
  const isAr = locale === 'ar';
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const dampedX = useSpring(x, { stiffness: 80, damping: 20 });
  const dampedY = useSpring(y, { stiffness: 80, damping: 20 });
  const blobX = useTransform(dampedX, (value) => value * -0.02);
  const blobY = useTransform(dampedY, (value) => value * -0.02);

  useEffect(() => {
    const handleMove = (event: MouseEvent) => {
      const centerX = window.innerWidth / 2;
      const centerY = window.innerHeight / 2;
      x.set(event.clientX - centerX);
      y.set(event.clientY - centerY);
    };
    window.addEventListener('mousemove', handleMove);
    return () => window.removeEventListener('mousemove', handleMove);
  }, [x, y]);

  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-slate-50 via-white to-raboo3-50/30 dark:from-ink-900 dark:via-ink-900 dark:to-ink-900/95" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="absolute inset-0 bg-grid-pattern opacity-[0.02] dark:opacity-[0.05]" />
      <div className="section relative">
        <div className="container">
          <div className="mx-auto max-w-5xl">
            <div className="relative rounded-3xl border border-slate-200/60 bg-gradient-to-br from-white/80 via-white/60 to-raboo3-50/20 p-8 shadow-2xl backdrop-blur-xl dark:border-slate-800/60 dark:from-ink-900/80 dark:via-ink-900/60 dark:to-raboo3-900/20 sm:p-12 md:p-16">
              <div className="hero-blobs pointer-events-none absolute inset-0 overflow-hidden rounded-3xl">
                <motion.div
                  className="absolute -top-32 right-0 h-96 w-96 rounded-full bg-gradient-to-br from-raboo3-500/20 via-raboo3-500/10 to-transparent blur-3xl"
                  style={{ x: blobX, y: blobY }}
                  aria-hidden
                />
                <motion.div
                  className="absolute bottom-0 left-0 h-[500px] w-[500px] rounded-full bg-gradient-to-tr from-raboo3-500/20 via-raboo3-400/10 to-transparent blur-3xl"
                  style={{ x: blobY, y: blobX }}
                  aria-hidden
                />
              </div>

              <div className="relative z-10 mx-auto flex max-w-4xl flex-col items-center gap-8 text-center">
                {t.home.hero_tagline ? (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    className="inline-flex items-center gap-2 rounded-full border border-raboo3-200/50 bg-raboo3-50/80 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-raboo3-700 backdrop-blur-sm dark:border-raboo3-800/50 dark:bg-raboo3-900/30 dark:text-raboo3-300"
                  >
                    <span className="h-2 w-2 animate-pulse rounded-full bg-raboo3-500" />
                    {t.home.hero_tagline}
                  </motion.div>
                ) : null}

                <motion.h1
                  className="text-4xl font-extrabold leading-tight text-ink-900 dark:text-white sm:text-5xl md:text-6xl lg:text-7xl"
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.7, delay: 0.1 }}
                >
                  <span className="bg-gradient-to-r from-ink-900 via-raboo3-700 to-ink-900 bg-clip-text text-transparent dark:from-white dark:via-raboo3-300 dark:to-white">
                    {t.brand.name}
                  </span>
                  <br />
                  <span className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl">{t.home.hero_title_main}</span>
                  {t.home.hero_title_sub ? (
                    <>
                      <br />
                      <span className="text-2xl font-bold text-raboo3-600 dark:text-raboo3-400 sm:text-3xl md:text-4xl">
                        {t.home.hero_title_sub}
                      </span>
                    </>
                  ) : null}
                </motion.h1>

                <motion.p
                  className="max-w-2xl text-base leading-relaxed text-slate-600 dark:text-slate-300 sm:text-lg"
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.7, delay: 0.2 }}
                >
                  {t.home.hero_subtitle}
                </motion.p>

                <motion.div
                  className="flex flex-wrap items-center justify-center gap-4"
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.7, delay: 0.3 }}
                  style={{ flexDirection: isAr ? 'row-reverse' : 'row' }}
                >
                  <Link
                    href={`/${locale}/predict`}
                    className="group relative overflow-hidden rounded-xl bg-gradient-to-r from-raboo3-600 to-raboo3-700 px-8 py-4 text-base font-semibold text-white shadow-lg shadow-raboo3-500/25 transition-all duration-300 hover:scale-105 hover:shadow-xl hover:shadow-raboo3-500/30 dark:from-raboo3-500 dark:to-raboo3-600"
                  >
                    <span className="relative z-10">{t.home.hero_cta_primary}</span>
                    <div className="absolute inset-0 bg-gradient-to-r from-raboo3-700 to-raboo3-800 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
                  </Link>
                  <Link
                    href={`/${locale}/about`}
                    className="rounded-xl border-2 border-slate-300 bg-white/80 px-8 py-4 text-base font-semibold text-ink-900 backdrop-blur-sm transition-all duration-300 hover:border-raboo3-400 hover:bg-raboo3-50 hover:text-raboo3-700 dark:border-slate-700 dark:bg-ink-900/60 dark:text-white dark:hover:border-raboo3-500 dark:hover:bg-raboo3-900/30"
                  >
                    {t.home.hero_cta_secondary}
                  </Link>
                </motion.div>

                <motion.div
                  className="mt-4 flex items-center gap-6 text-xs text-slate-500 dark:text-slate-400"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.7, delay: 0.5 }}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-raboo3-500">✓</span>
                    <span>{t.home.hero_feature_accuracy}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-raboo3-500">✓</span>
                    <span>{t.home.hero_feature_instant}</span>
                  </div>
                </motion.div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
