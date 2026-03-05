import './globals.css';
import { defaultLocale } from '@/i18n/config';
import type { ReactNode } from 'react';

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang={defaultLocale} dir="rtl" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
