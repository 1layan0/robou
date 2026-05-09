'use client';

import { useI18n } from '@/i18n/useTranslations';

export default function SiteFooter() {
  const { locale } = useI18n();
  const isAr = locale === 'ar';

  return (
    <footer className="w-full border-t border-slate-200 bg-white/70 dark:bg-ink-900/80 dark:border-slate-700 backdrop-blur px-6 py-4">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 text-xs sm:text-sm text-slate-600 dark:text-slate-300">
        <p className="whitespace-pre-wrap">
          {isAr ? '© 2026 ربوع. جميع الحقوق محفوظة.' : '© 2026 Robou. All rights reserved.'}
        </p>
        <div className="flex items-center gap-3">
          <div className="relative group">
            <button
              type="button"
              aria-label="حساب ربوع على إكس"
              className="cursor-default rounded-full p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              <svg
                viewBox="0 0 24 24"
                aria-hidden="true"
                className="h-5 w-5 text-slate-400 hover:text-slate-600 dark:text-slate-400 dark:hover:text-slate-100 transition"
              >
                <path
                  fill="currentColor"
                  d="M17.53 4H20l-5.09 5.82L20.5 20h-4.03l-3.11-4.63L9.7 20H7.24l5.45-6.24L7 4h4.11l2.8 4.17L17.53 4Z"
                />
              </svg>
            </button>
            <span className="pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 rounded bg-black/80 px-2 py-1 text-xs text-white opacity-0 group-hover:opacity-100 transition">
              قريبًا
            </span>
          </div>

          <div className="relative group">
            <button
              type="button"
              aria-label="حساب ربوع على إنستغرام"
              className="cursor-default rounded-full p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              <svg
                viewBox="0 0 24 24"
                aria-hidden="true"
                className="h-5 w-5 text-slate-400 hover:text-slate-600 dark:text-slate-400 dark:hover:text-slate-100 transition"
              >
                <rect x="3" y="3" width="18" height="18" rx="5" ry="5" fill="none" stroke="currentColor" strokeWidth="1.6" />
                <circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" strokeWidth="1.6" />
                <circle cx="17" cy="7" r="1.1" fill="currentColor" />
              </svg>
            </button>
            <span className="pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 rounded bg-black/80 px-2 py-1 text-xs text-white opacity-0 group-hover:opacity-100 transition">
              قريبًا
            </span>
          </div>

          <div className="relative group">
            <button
              type="button"
              aria-label="واتساب ربوع"
              className="cursor-default rounded-full p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              <svg
                viewBox="0 0 24 24"
                aria-hidden="true"
                className="h-5 w-5 text-slate-400 hover:text-slate-600 dark:text-slate-400 dark:hover:text-slate-100 transition"
              >
                <path
                  fill="currentColor"
                  d="M20.5 11.74C20.5 7.39 16.9 4 12.37 4 7.39 4 3.5 7.97 3.5 12.32c0 1.34.35 2.6.96 3.72L3 20.5l4.59-1.2c1.08.59 2.31.92 3.65.92 4.98 0 8.26-3.86 8.26-8.48Zm-8.14 6.56c-1.2 0-2.32-.32-3.29-.88l-.24-.14-2.72.72.73-2.64-.16-.27a6.38 6.38 0 0 1-.97-3.37c0-3.58 2.74-6.33 6.58-6.33 3.5 0 6.37 2.93 6.37 6.52 0 3.73-2.98 6.49-6.3 6.49Zm3.47-4.72c-.19-.1-1.12-.55-1.29-.61-.17-.06-.3-.1-.43.1-.13.19-.49.61-.6.73-.11.13-.22.14-.41.05-.19-.1-.8-.3-1.52-.96-.56-.5-.94-1.12-1.06-1.31-.11-.19-.01-.29.08-.38.08-.08.19-.22.28-.33.09-.11.12-.19.18-.32.06-.13.03-.24-.02-.34-.05-.1-.43-1.02-.59-1.39-.15-.36-.3-.31-.43-.32h-.37c-.13 0-.34.05-.52.24-.17.19-.68.66-.68 1.6 0 .94.7 1.84.8 1.97.1.13 1.38 2.18 3.36 3.05.47.2.84.33 1.13.42.48.15.91.13 1.26.08.39-.06 1.12-.46 1.28-.9.16-.44.16-.82.11-.9-.05-.08-.17-.13-.36-.22Z"
                />
              </svg>
            </button>
            <span className="pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 rounded bg-black/80 px-2 py-1 text-xs text-white opacity-0 group-hover:opacity-100 transition">
              قريبًا
            </span>
          </div>

          <div className="relative group">
            <button
              type="button"
              aria-label="البريد الإلكتروني لربوع"
              className="cursor-default rounded-full p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              <svg
                viewBox="0 0 24 24"
                aria-hidden="true"
                className="h-5 w-5 text-slate-400 hover:text-slate-600 dark:text-slate-400 dark:hover:text-slate-100 transition"
              >
                <rect
                  x="3"
                  y="5"
                  width="18"
                  height="14"
                  rx="2"
                  ry="2"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.6"
                />
                <path
                  d="M4 7.5 11.35 12c.4.26.9.26 1.3 0L20 7.5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
            <span className="pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 rounded bg-black/80 px-2 py-1 text-xs text-white opacity-0 group-hover:opacity-100 transition">
              قريبًا
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}

