'use client';

import { useLayoutEffect } from 'react';
import { defaultLocale } from '@/i18n/config';

function recoveryTargetPath(hash: string): string | null {
  const h = hash.startsWith('#') ? hash.slice(1) : hash;
  const hashParams = new URLSearchParams(h);
  if (hashParams.get('type') === 'recovery') {
    return `/${defaultLocale}/reset-password`;
  }
  return null;
}

/**
 * إعادة توجيه / من المتصفح (وليس redirect() من السيرفر) حتى لا يُفقد fragment (#access_token… من روابط Supabase).
 */
export default function IndexRedirect() {
  useLayoutEffect(() => {
    const { search, hash } = window.location;
    const recovery = recoveryTargetPath(hash);
    const path = recovery ?? `/${defaultLocale}`;
    window.location.replace(`${path}${search}${hash}`);
  }, []);

  return (
    <main className="min-h-screen flex items-center justify-center bg-white dark:bg-ink-900 text-slate-500 text-sm">
      …
    </main>
  );
}
