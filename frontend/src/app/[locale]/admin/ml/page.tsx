'use client';

import { useI18n, useT } from '@/i18n/useTranslations';

export default function MLMonitoringPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';

  const modelMetrics = {
    accuracy: 94.5,
    precision: 92.3,
    recall: 91.8,
    f1Score: 92.0,
    lastTraining: '2024-01-10',
    trainingSamples: 15420,
    predictionsToday: 342,
    avgResponseTime: '45ms',
  };

  return (
    <main className="section" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container space-y-8">
        <header className="space-y-3">
          <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl">
            {t.admin_ml.title}
          </h1>
          <p className="text-base leading-relaxed text-slate-600 dark:text-slate-300">
            {t.admin_ml.subtitle}
          </p>
        </header>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <div className="card p-6">
            <div className="text-sm text-slate-600 dark:text-slate-400 mb-2">{t.admin_ml.accuracy}</div>
            <div className="text-3xl font-bold text-ink-900 dark:text-white">{modelMetrics.accuracy}%</div>
          </div>
          <div className="card p-6">
            <div className="text-sm text-slate-600 dark:text-slate-400 mb-2">{t.admin_ml.precision}</div>
            <div className="text-3xl font-bold text-ink-900 dark:text-white">{modelMetrics.precision}%</div>
          </div>
          <div className="card p-6">
            <div className="text-sm text-slate-600 dark:text-slate-400 mb-2">{t.admin_ml.recall}</div>
            <div className="text-3xl font-bold text-ink-900 dark:text-white">{modelMetrics.recall}%</div>
          </div>
          <div className="card p-6">
            <div className="text-sm text-slate-600 dark:text-slate-400 mb-2">{t.admin_ml.f1_score}</div>
            <div className="text-3xl font-bold text-ink-900 dark:text-white">{modelMetrics.f1Score}%</div>
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <div className="card p-6 space-y-4">
            <h2 className="text-xl font-bold text-ink-900 dark:text-white">{t.admin_ml.training_info}</h2>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-slate-600 dark:text-slate-400">{t.admin_ml.last_training}:</span>
                <span className="font-semibold text-ink-900 dark:text-white">{modelMetrics.lastTraining}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600 dark:text-slate-400">{t.admin_ml.training_samples}:</span>
                <span className="font-semibold text-ink-900 dark:text-white">
                  {modelMetrics.trainingSamples.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')}
                </span>
              </div>
            </div>
            <button className="w-full btn btn-primary mt-4">
              {t.admin_ml.retrain_model}
            </button>
          </div>

          <div className="card p-6 space-y-4">
            <h2 className="text-xl font-bold text-ink-900 dark:text-white">{t.admin_ml.performance}</h2>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-slate-600 dark:text-slate-400">{t.admin_ml.predictions_today}:</span>
                <span className="font-semibold text-ink-900 dark:text-white">{modelMetrics.predictionsToday}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600 dark:text-slate-400">{t.admin_ml.avg_response_time}:</span>
                <span className="font-semibold text-ink-900 dark:text-white">{modelMetrics.avgResponseTime}</span>
              </div>
            </div>
            <button className="w-full btn border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-ink-900 dark:text-slate-300 mt-4">
              {t.admin_ml.view_logs}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}

