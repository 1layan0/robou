'use client';

import { useI18n, useT } from '@/i18n/useTranslations';

const SOURCES = [
  { name: 'وزارة العدل', nameEn: 'Ministry of Justice', logo: '/sources/moj.svg', href: 'https://www.moj.gov.sa' },
  { name: 'الهيئة العامة للعقار', nameEn: 'Real Estate General Authority', logo: '/sources/rega.svg', href: 'https://rega.gov.sa' },
  { name: 'منصة إيجار', nameEn: 'Ejar Platform', logo: '/sources/ejar.svg', href: 'https://ejar.sa' },
];

function SourceCard({
  name,
  nameEn,
  logo,
  href,
  isAr,
}: {
  name: string;
  nameEn: string;
  logo: string;
  href?: string;
  isAr: boolean;
}) {
  const img = (
    <img
      src={logo}
      alt={isAr ? name : nameEn}
      className="h-16 w-auto object-contain dark:brightness-110 dark:contrast-105"
    />
  );

  const card = (
    <div className="flex items-center justify-center rounded-2xl border border-slate-200 bg-white px-10 py-7 shadow-sm transition-shadow dark:border-slate-600 dark:bg-slate-700/90 hover:shadow-md">
      {img}
    </div>
  );

  if (href) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="block focus:outline-none focus-visible:ring-2 focus-visible:ring-raboo3-500 focus-visible:ring-offset-2 rounded-2xl"
        aria-label={isAr ? name : nameEn}
      >
        {card}
      </a>
    );
  }
  return card;
}

export default function DataSourcesStrip() {
  const t = useT();
  const { locale } = useI18n();
  const isAr = locale === 'ar';

  const renderCard = (s: (typeof SOURCES)[0], keySuffix?: string) => (
    <SourceCard
      key={keySuffix ? `${s.logo}-${keySuffix}` : s.logo}
      name={s.name}
      nameEn={s.nameEn}
      logo={s.logo}
      href={s.href}
      isAr={isAr}
    />
  );

  return (
    <section
      id="data-sources"
      className="container mt-16"
      dir={isAr ? 'rtl' : 'ltr'}
      aria-labelledby="data-sources-heading"
    >
      <div className="rounded-3xl border border-slate-200/80 bg-emerald-50/40 px-6 py-10 shadow-sm dark:border-slate-600/80 dark:bg-slate-800/70">
        <div className="mx-auto max-w-3xl text-center">
          <p id="data-sources-heading" className="text-sm font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            {t.home.data_sources_title}
          </p>
          <p className="mt-2 text-base text-slate-600 dark:text-slate-300">
            {t.home.data_sources_desc}
          </p>
        </div>

        {/* dir="ltr" ثابت حتى في الصفحة العربية: المساران يبقان [أول][ثاني] والحركة -50% تعطي حلقة متصلة من اليمين */}
        <div className="marquee mt-8" dir="ltr">
          <div className="marquee-inner">
            {/* وحدة = مسار + فجوة حتى المسافة موحدة والحلقة متصلة */}
            <div className="marquee-track">
              {SOURCES.map((s) => renderCard(s))}
            </div>
            <div className="marquee-gap" aria-hidden="true" />
            <div className="marquee-track" aria-hidden="true">
              {SOURCES.map((s) => renderCard(s, 'b'))}
            </div>
            <div className="marquee-gap" aria-hidden="true" />
          </div>
        </div>
      </div>
    </section>
  );
}
