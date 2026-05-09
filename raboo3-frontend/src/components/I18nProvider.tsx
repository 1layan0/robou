'use client';

import type { ReactNode } from 'react';
import { I18nContext } from '@/i18n/useTranslations';
import type { Locale } from '@/i18n/config';
import type { Messages } from '@/i18n/dictionaries';

interface I18nProviderProps {
  locale: Locale;
  messages: Messages;
  children: ReactNode;
}

export default function I18nProvider({ locale, messages, children }: I18nProviderProps) {
  return <I18nContext.Provider value={{ locale, messages }}>{children}</I18nContext.Provider>;
}

