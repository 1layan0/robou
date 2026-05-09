import { type Locale } from '../config';
import ar from './ar';
import en from './en';

export async function getMessages(locale: Locale) {
  switch (locale) {
    case 'ar':
      return ar;
    case 'en':
      return en;
    default:
      return ar;
  }
}

export type { Messages } from './types';

