'use client';

import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import clsx from 'classnames';
import { useTheme } from 'next-themes';
import Raboo3Logo from '@/components/Raboo3Logo';
import { useI18n, useT } from '@/i18n/useTranslations';
import { useAuth } from '@/contexts/AuthContext';

export default function Navbar() {
  const t = useT();
  const { locale } = useI18n();
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const [adminMenuOpen, setAdminMenuOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const { user } = useAuth();
  const { resolvedTheme, setTheme } = useTheme();

  const segments = pathname.split('/').filter(Boolean);
  const currentLocale = segments[0] === 'ar' || segments[0] === 'en' ? segments[0] : 'ar';
  const rest = segments.slice(1).join('/');

  function switchLocale(nextLocale: 'ar' | 'en') {
    if (nextLocale === currentLocale) return;
    const targetBase = '/' + [nextLocale, rest].filter(Boolean).join('/');
    const qs = searchParams.toString();
    router.push(qs ? `${targetBase}?${qs}` : targetBase);
  }

  const isAr = locale === 'ar';

  const firstInitial = user?.firstName?.trim()?.[0] ?? '';
  const lastInitial = user?.lastName?.trim()?.[0] ?? '';
  const initials =
    (firstInitial + lastInitial || '')
      .trim()
      .toUpperCase() || (isAr ? 'حس' : 'AC');

  const links = [
    { href: `/${locale}`, label: t.nav.home },
    { href: `/${locale}/predict`, label: t.nav.predict },
    { href: `/${locale}/insights`, label: t.nav.insights },
    { href: `/${locale}/transactions`, label: t.nav.transactions },
    { href: `/${locale}/about`, label: t.nav.about },
  ];

  // روابط لوحة التحكم تم إخفاؤها من الواجهة العامة
  const adminLinks: { href: string; label: string }[] = [];

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 24);
    };
    onScroll();
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    if (open && pathname) {
      setOpen(false);
    }
  }, [pathname]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (adminMenuOpen && !target.closest('.admin-menu-container')) {
        setAdminMenuOpen(false);
      }
    };
    if (adminMenuOpen) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [adminMenuOpen]);

  return (
    <header
      className={clsx(
        'sticky top-0 z-50 transition-all duration-300',
        scrolled
          ? 'bg-white/95 dark:bg-ink-900/95 backdrop-blur-md shadow-lg border-b border-slate-200/50 dark:border-slate-800/50'
          : 'bg-transparent'
      )}
      dir={isAr ? 'rtl' : 'ltr'}
    >
      <div className="mx-auto w-full max-w-7xl px-6 flex items-center justify-between py-4">
        <Link href={`/${locale}`} className="flex items-center gap-3 text-lg font-bold">
          <Raboo3Logo size={42} />
          <div className="leading-tight">
            <div className="text-2xl font-extrabold tracking-tight text-ink-900 dark:text-white">
              {t.brand.name}
            </div>
            <div className="text-sm text-slate-500 mt-1">{t.brand.tagline}</div>
          </div>
        </Link>
        <nav className="hidden items-center gap-1 text-sm font-semibold md:flex">
          {links.map((link) => {
            const active = pathname === link.href || (link.href === `/${locale}` && pathname === `/${locale}`);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={clsx(
                  'relative rounded-lg px-4 py-2 transition-all duration-200',
                  active
                    ? 'text-raboo3-700 dark:text-raboo3-400'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-ink-900 dark:text-slate-300 dark:hover:bg-slate-800'
                )}
              >
                {link.label}
                {active && (
                  <motion.span
                    layoutId="nav-underline"
                    className="absolute inset-x-2 bottom-0 h-0.5 rounded-full bg-raboo3-500"
                  />
                )}
              </Link>
            );
          })}
        </nav>
        <div className="flex items-center gap-3">
          {adminLinks.length > 0 && (
            <div className="hidden md:block relative admin-menu-container">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setAdminMenuOpen(!adminMenuOpen);
                }}
                className="text-sm font-semibold text-slate-600 hover:text-ink-900 dark:text-slate-300 dark:hover:text-white flex items-center gap-1"
              >
                {isAr ? 'لوحة التحكم' : 'Admin'}
                <span className="text-xs">▼</span>
              </button>
              {adminMenuOpen && (
                <div className="absolute top-full mt-2 right-0 w-56 bg-white dark:bg-ink-900 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 py-2 z-50">
                  {adminLinks.map((link) => (
                    <Link
                      key={link.href}
                      href={link.href}
                      onClick={() => setAdminMenuOpen(false)}
                      className="block px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 hover:text-ink-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white"
                    >
                      {link.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )}
          {!user && (
            <>
              <Link
                href={`/${locale}/signup`}
                className="hidden text-sm font-semibold text-slate-600 hover:text-ink-900 dark:text-slate-300 dark:hover:text-white md:block"
              >
                {t.nav.signup}
              </Link>
              <Link
                href={`/${locale}/login`}
                className="hidden text-sm font-semibold text-slate-600 hover:text-ink-900 dark:text-slate-300 dark:hover:text-white md:block"
              >
                {t.nav.login}
              </Link>
            </>
          )}
          <div className="flex items-center gap-3 h-9">
            {/* تبديل اللغة */}
            <div
              role="group"
              aria-label={isAr ? 'اللغة' : 'Language'}
              className="inline-flex h-9 rounded-lg bg-slate-100/90 dark:bg-slate-800/90 p-1 text-xs font-medium"
            >
              <button
                type="button"
                onClick={() => switchLocale('ar')}
                className={clsx(
                  'rounded-md px-3 h-full min-w-[3rem] transition-colors duration-200 flex items-center justify-center',
                  locale === 'ar'
                    ? 'bg-white dark:bg-ink-700 text-ink-900 dark:text-white shadow-sm'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
                )}
              >
                {t.common.language_ar}
              </button>
              <button
                type="button"
                onClick={() => switchLocale('en')}
                className={clsx(
                  'rounded-md px-3 h-full min-w-[3rem] transition-colors duration-200 flex items-center justify-center',
                  locale === 'en'
                    ? 'bg-white dark:bg-ink-700 text-ink-900 dark:text-white shadow-sm'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
                )}
              >
                {t.common.language_en}
              </button>
            </div>

            {/* مبدّل الثيم — ثابت الاتجاه ليمين/يسار */}
            {mounted && (
              <button
                type="button"
                dir="ltr"
                onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
                aria-label={
                  isAr
                    ? resolvedTheme === 'dark'
                      ? 'تفعيل الوضع الفاتح'
                      : 'تفعيل الوضع الليلي'
                    : resolvedTheme === 'dark'
                      ? 'Enable light mode'
                      : 'Enable dark mode'
                }
                className="relative inline-flex h-9 w-14 shrink-0 items-center rounded-full bg-slate-200 dark:bg-slate-700 transition-colors duration-200 hover:bg-slate-300 dark:hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-raboo3-400 focus:ring-offset-2 dark:focus:ring-offset-ink-900"
              >
                <span
                  className="absolute top-1/2 -translate-y-1/2 inline-flex h-7 w-7 items-center justify-center rounded-full bg-white dark:bg-ink-800 shadow-sm transition-all duration-200 ease-out"
                  style={{
                    left: resolvedTheme === 'dark' ? 'calc(100% - 1.75rem - 4px)' : '4px',
                  }}
                >
                  {resolvedTheme === 'dark' ? (
                    <svg className="h-4 w-4 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" />
                    </svg>
                  ) : (
                    <svg className="h-4 w-4 text-slate-600 dark:text-slate-300" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                    </svg>
                  )}
                </span>
              </button>
            )}
          </div>
          {user && (
            <Link
              href={`/${locale}/account`}
              className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-raboo3-600 text-white text-sm font-semibold shadow-sm hover:bg-raboo3-700 transition-colors"
              aria-label={isAr ? 'حسابي' : 'My account'}
            >
              {initials}
            </Link>
          )}
          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white/80 text-sm shadow-sm backdrop-blur-sm transition-all hover:scale-110 hover:border-raboo3-300 dark:border-slate-700 dark:bg-ink-900/80 md:hidden"
            onClick={() => setOpen((prev) => !prev)}
            aria-label={isAr ? 'فتح القائمة' : 'Open menu'}
            aria-expanded={open}
          >
            <span className="flex flex-col gap-1.5 text-ink-900 dark:text-white">
              <span className={clsx('block h-0.5 w-6 rounded-full bg-current transition-all', open && 'rotate-45 translate-y-2')} />
              <span className={clsx('block h-0.5 w-6 rounded-full bg-current transition-all', open && 'opacity-0')} />
              <span className={clsx('block h-0.5 w-6 rounded-full bg-current transition-all', open && '-rotate-45 -translate-y-2')} />
            </span>
          </button>
        </div>
      </div>
      <AnimatePresence>
        {open && (
          <motion.nav
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="border-t border-slate-200/50 bg-white/98 backdrop-blur-md dark:border-slate-800/50 dark:bg-ink-900/98 md:hidden"
          >
            <div className="mx-auto w-full max-w-7xl px-6 flex flex-col gap-1 py-4 text-sm font-semibold">
              {links.map((link) => {
                const active = pathname === link.href || (link.href === `/${locale}` && pathname === `/${locale}`);
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setOpen(false)}
                    className={clsx(
                      'rounded-xl px-4 py-3 transition-all',
                      active
                        ? 'bg-raboo3-50 text-raboo3-700 dark:bg-raboo3-900/30 dark:text-raboo3-400'
                        : 'text-slate-600 hover:bg-slate-100 hover:text-ink-900 dark:text-slate-300 dark:hover:bg-slate-800'
                    )}
                  >
                    {link.label}
                  </Link>
                );
              })}
              {adminLinks.length > 0 && (
                <>
                  <div className="border-t border-slate-200 dark:border-slate-700 my-2" />
                  <div className="px-4 py-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                    {isAr ? 'لوحة التحكم' : 'Admin'}
                  </div>
                  {adminLinks.map((link) => (
                    <Link
                      key={link.href}
                      href={link.href}
                      onClick={() => setOpen(false)}
                      className="rounded-xl px-4 py-3 text-slate-600 hover:bg-slate-100 hover:text-ink-900 dark:text-slate-300 dark:hover:bg-slate-800"
                    >
                      {link.label}
                    </Link>
                  ))}
                  <div className="border-t border-slate-200 dark:border-slate-700 my-2" />
                </>
              )}
              <Link
                href={`/${locale}/login`}
                onClick={() => setOpen(false)}
                className="rounded-xl px-4 py-3 text-slate-600 hover:bg-slate-100 hover:text-ink-900 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                {t.nav.login}
              </Link>
            </div>
          </motion.nav>
        )}
      </AnimatePresence>
    </header>
  );
}
