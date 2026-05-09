'use client';

import { useI18n, useT } from '@/i18n/useTranslations';

export default function Footer() {
  const t = useT();
  const { locale } = useI18n();

  return (
    <footer className="mt-16 border-t border-black/5 py-8" dir={locale === 'ar' ? 'rtl' : 'ltr'}>
      <div className="mx-auto w-full max-w-7xl px-6 text-sm text-slate-500">
        {t.brand.name} — {t.brand.tagline}
      </div>
    </footer>
  );
}
