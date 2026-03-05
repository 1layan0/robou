'use client';

import { createContext, useContext } from 'react';
import type { Messages } from './dictionaries';

type TContext = {
  locale: 'ar' | 'en';
  messages: Messages;
};

export const I18nContext = createContext<TContext | null>(null);

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('I18nContext is not provided');
  return ctx;
}

export function useT() {
  const { messages } = useI18n();
  return messages;
}

