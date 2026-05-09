'use client';

import Raboo3Logo from '@/components/Raboo3Logo';
import { useI18n, useT } from '@/i18n/useTranslations';
import Link from 'next/link';

export default function AboutPage() {
  const t = useT();
  const { locale } = useI18n();
  const isAr = locale === 'ar';

  return (
    <main className="min-h-screen" dir={isAr ? 'rtl' : 'ltr'}>
      {/* Hero */}
      <section className="relative overflow-hidden pt-16 pb-24 px-4">
        <div className="absolute inset-0 bg-grid-pattern opacity-40 dark:opacity-20" />
        <div className="container relative mx-auto max-w-4xl text-center">
          <div className="inline-flex items-center justify-center w-28 h-28 mb-6">
            <Raboo3Logo size={72} />
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-ink-900 dark:text-white tracking-tight mb-3">
            {t.about.title}
          </h1>
          <p className="text-slate-600 dark:text-slate-300 text-lg max-w-2xl mx-auto">
            {isAr ? 'منصة تُحوّل البيانات إلى قرار — تقدير ذكي لأسعار الأراضي' : 'Where data becomes decision — smart land valuation'}
          </p>
        </div>
      </section>

      {/* Content blocks */}
      <section className="container max-w-4xl mx-auto px-4 pb-20 space-y-8">
        <article className="group relative rounded-2xl border border-slate-200/60 dark:border-slate-700/60 p-8 sm:p-10 ps-14 sm:ps-16 shadow-sm hover:shadow-md hover:border-slate-300/70 dark:hover:border-slate-600/70 transition-all duration-300">
          <span className="absolute top-10 start-4 w-10 h-10 rounded-xl bg-raboo3-100 dark:bg-raboo3-900/40 flex items-center justify-center text-raboo3-600 dark:text-raboo3-400 text-lg font-bold">
            1
          </span>
          <p className="text-lg text-ink-800 dark:text-slate-200 leading-relaxed">
            {t.about.p1}
          </p>
        </article>

        <article className="group relative rounded-2xl border border-slate-200/60 dark:border-slate-700/60 p-8 sm:p-10 ps-14 sm:ps-16 shadow-sm hover:shadow-md hover:border-slate-300/70 dark:hover:border-slate-600/70 transition-all duration-300">
          <span className="absolute top-10 start-4 w-10 h-10 rounded-xl bg-raboo3-100 dark:bg-raboo3-900/40 flex items-center justify-center text-raboo3-600 dark:text-raboo3-400 text-lg font-bold">
            2
          </span>
          <p className="text-lg text-ink-800 dark:text-slate-200 leading-relaxed">
            {t.about.p2}
          </p>
        </article>

        <article className="group relative rounded-2xl border border-slate-200/60 dark:border-slate-700/60 p-8 sm:p-10 ps-14 sm:ps-16 shadow-sm hover:shadow-md hover:border-slate-300/70 dark:hover:border-slate-600/70 transition-all duration-300">
          <span className="absolute top-10 start-4 w-10 h-10 rounded-xl bg-raboo3-100 dark:bg-raboo3-900/40 flex items-center justify-center text-raboo3-600 dark:text-raboo3-400 text-lg font-bold">
            3
          </span>
          <p className="text-lg text-ink-800 dark:text-slate-200 leading-relaxed">
            {t.about.p3}
          </p>
        </article>

        {/* CTA */}
        <div className="text-center pt-8">
          <Link
            href={`/${locale}/predict`}
            className="inline-flex items-center gap-2 rounded-xl bg-raboo3-600 hover:bg-raboo3-700 dark:bg-raboo3-500 dark:hover:bg-raboo3-600 text-white font-semibold px-6 py-3 transition-colors"
          >
            {isAr ? 'ابدأ التقدير' : 'Start valuation'}
            <span className="text-lg" aria-hidden>{isAr ? '←' : '→'}</span>
          </Link>
        </div>
      </section>
    </main>
  );
}
