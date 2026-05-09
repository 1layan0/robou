'use client';

import { useEffect } from 'react';

export default function DocumentDirLang({ lang, dir }: { lang: string; dir: string }) {
  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = dir;
  }, [lang, dir]);
  return null;
}
