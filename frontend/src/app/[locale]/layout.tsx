import '../globals.css';
import type { ReactNode } from 'react';
import { Cairo } from 'next/font/google';
import { getMessages } from '@/i18n/dictionaries';
import { isLocale, type Locale, defaultLocale } from '@/i18n/config';
import { ThemeProvider } from 'next-themes';
import { NotificationProvider } from '@/contexts/NotificationContext';
import { AuthProvider } from '@/contexts/AuthContext';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import I18nProvider from '@/components/I18nProvider';

const cairo = Cairo({ subsets: ['arabic'], weight: ['300', '400', '600', '700'], display: 'swap' });

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> | { locale: string } }) {
  const paramsObj = await Promise.resolve(params);
  const { locale: localeParam } = paramsObj;
  const locale: Locale = isLocale(localeParam) ? localeParam : defaultLocale;
  const messages = await getMessages(locale);

  return {
    title: `${messages.brand.name} — ${messages.brand.tagline}`,
    description: messages.home.hero_subtitle,
    icons: {
      icon: '/favicon.svg',
      shortcut: '/favicon.svg',
      apple: '/favicon.svg',
    },
    openGraph: {
      title: messages.brand.name,
      description: messages.brand.tagline,
      locale: locale === 'ar' ? 'ar_SA' : 'en_US',
      type: 'website',
    },
  };
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }> | { locale: string };
}) {
  const paramsObj = await Promise.resolve(params);
  const { locale: localeParam } = paramsObj;
  const locale: Locale = isLocale(localeParam) ? localeParam : defaultLocale;
  const messages = await getMessages(locale);

  const dir = locale === 'ar' ? 'rtl' : 'ltr';

  return (
    <html lang={locale} dir={dir} suppressHydrationWarning>
      <body suppressHydrationWarning>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <NotificationProvider>
            <I18nProvider locale={locale} messages={messages}>
              <AuthProvider>
                <div
                  dir={dir}
                  className={`min-h-screen bg-white text-ink-900 dark:bg-ink-900 dark:text-white antialiased ${locale === 'ar' ? cairo.className : 'font-sans'}`}
                >
                  <Navbar />
                  {children}
                  <Footer />
                </div>
              </AuthProvider>
            </I18nProvider>
          </NotificationProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
