'use client';

import { useState } from 'react';
import { useI18n, useT } from '@/i18n/useTranslations';

export default function DataValidationPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';

  const [validationStatus, setValidationStatus] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all');

  const mockData = [
    { id: 1, type: 'transaction', status: 'pending', submittedBy: 'أحمد محمد', date: '2024-01-15', errors: 2 },
    { id: 2, type: 'facility', status: 'approved', submittedBy: 'فاطمة علي', date: '2024-01-14', errors: 0 },
    { id: 3, type: 'transaction', status: 'rejected', submittedBy: 'محمد خالد', date: '2024-01-13', errors: 5 },
    { id: 4, type: 'district', status: 'pending', submittedBy: 'سارة أحمد', date: '2024-01-12', errors: 1 },
  ];

  const filteredData = validationStatus === 'all' 
    ? mockData 
    : mockData.filter(item => item.status === validationStatus);

  return (
    <main className="section" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container space-y-8">
        <header className="space-y-3">
          <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl">
            {t.admin_validation.title}
          </h1>
          <p className="text-base leading-relaxed text-slate-600 dark:text-slate-300">
            {t.admin_validation.subtitle}
          </p>
        </header>

        <div className="card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-ink-900 dark:text-white">{t.admin_validation.filter}</h2>
            <select
              value={validationStatus}
              onChange={(e) => setValidationStatus(e.target.value as any)}
              className="px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
            >
              <option value="all">{t.admin_validation.all}</option>
              <option value="pending">{t.admin_validation.pending}</option>
              <option value="approved">{t.admin_validation.approved}</option>
              <option value="rejected">{t.admin_validation.rejected}</option>
            </select>
          </div>

          <div className="space-y-3">
            {filteredData.map((item) => (
              <div
                key={item.id}
                className="p-4 border border-slate-200 dark:border-slate-800 rounded-xl hover:bg-slate-50 dark:hover:bg-ink-900/50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-3">
                      <span className="font-semibold text-ink-900 dark:text-white">
                        {t.admin_validation.data_type}: {item.type}
                      </span>
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-semibold ${
                          item.status === 'approved'
                            ? 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300'
                            : item.status === 'rejected'
                            ? 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300'
                            : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-500/20 dark:text-yellow-300'
                        }`}
                      >
                        {item.status === 'approved'
                          ? t.admin_validation.approved
                          : item.status === 'rejected'
                          ? t.admin_validation.rejected
                          : t.admin_validation.pending}
                      </span>
                    </div>
                    <div className="text-sm text-slate-600 dark:text-slate-400">
                      {t.admin_validation.submitted_by}: {item.submittedBy} | {t.admin_validation.date}: {item.date}
                    </div>
                    {item.errors > 0 && (
                      <div className="text-sm text-red-600 dark:text-red-400">
                        {t.admin_validation.errors_found}: {item.errors}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button className="px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 text-sm font-semibold">
                      {t.admin_validation.approve}
                    </button>
                    <button className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 text-sm font-semibold">
                      {t.admin_validation.reject}
                    </button>
                    <button className="px-4 py-2 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-ink-900 dark:text-slate-300 text-sm font-semibold">
                      {t.admin_validation.view}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}

