'use client';

import { useEffect } from 'react';

export default function LocaleError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="min-h-screen flex items-center justify-center p-4" dir="rtl">
      <div className="text-center max-w-md">
        <h1 className="text-xl font-bold text-ink-900 dark:text-white mb-2">حدث خطأ</h1>
        <p className="text-slate-600 dark:text-slate-400 mb-4">{error?.message || 'خطأ غير متوقع'}</p>
        <button
          type="button"
          onClick={() => reset()}
          className="px-4 py-2 rounded-xl bg-raboo3-600 text-white font-medium hover:bg-raboo3-700"
        >
          إعادة المحاولة
        </button>
      </div>
    </main>
  );
}
