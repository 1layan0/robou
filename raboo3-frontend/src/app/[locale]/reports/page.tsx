'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import { useNotifications } from '@/contexts/NotificationContext';
import { CITIES } from '@/lib/cities';
import { useI18n, useT } from '@/i18n/useTranslations';
import { translateCity } from '@/lib/translateLocations';

const InsightsChart = dynamic(() => import('@/components/InsightsChart'), { ssr: false });

interface Report {
  id: string;
  title: string;
  type: 'price' | 'demand' | 'trend' | 'comparison';
  city?: string;
  period: string;
  generatedAt: string;
  data: Record<string, unknown>;
}

export default function ReportsPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const { addNotification } = useNotifications();
  const [selectedCity, setSelectedCity] = useState<string>('');
  const [selectedPeriod, setSelectedPeriod] = useState<'week' | 'month' | 'quarter' | 'year'>('month');
  const [reportType, setReportType] = useState<'price' | 'demand' | 'trend' | 'comparison'>('price');
  const [generating, setGenerating] = useState(false);

  const mockReports: Report[] = [
    {
      id: '1',
      title: 'تقرير أسعار الدمام - الشهر الماضي',
      type: 'price',
      city: 'الدمام',
      period: 'month',
      generatedAt: new Date().toISOString(),
      data: { average: 1850, trend: 'up', change: 5.2 },
    },
    {
      id: '2',
      title: 'مقارنة الطلب بين المدن',
      type: 'comparison',
      period: 'quarter',
      generatedAt: new Date().toISOString(),
      data: { cities: ['الدمام', 'الظهران', 'الخبر'], values: [85, 92, 78] },
    },
  ];

  const handleGenerateReport = () => {
    setGenerating(true);
    setTimeout(() => {
      addNotification({
        type: 'success',
        title: isAr ? 'تم إنشاء التقرير' : 'Report Generated',
        message: isAr ? 'تم إنشاء التقرير بنجاح وجاهز للتحميل' : 'Report generated successfully and ready for download',
        duration: 3000,
      });
      setGenerating(false);
    }, 2000);
  };

  const handleDownload = () => {
      addNotification({
        type: 'info',
        title: isAr ? 'جاري التحميل' : 'Downloading',
        message: isAr ? 'سيتم تحميل التقرير قريباً' : 'Report will be downloaded shortly',
        duration: 2000,
      });
  };

  return (
    <main className="section" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container space-y-8">
        <header className="space-y-3">
          <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl">
            {t.reports.title}
          </h1>
          <p className="text-base leading-relaxed text-slate-600 dark:text-slate-300">
            {t.reports.subtitle}
          </p>
        </header>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <div className="card p-6 space-y-4">
              <h2 className="text-xl font-bold text-ink-900 dark:text-white">{t.reports.create_new}</h2>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-ink-900 dark:text-white">
                    {t.reports.report_type}
                  </label>
                  <select
                    value={reportType}
                    onChange={(e) => setReportType(e.target.value as 'price' | 'demand' | 'trend' | 'comparison')}
                    className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
                  >
                    <option value="price">{t.reports.report_type_price}</option>
                    <option value="demand">{t.reports.report_type_demand}</option>
                    <option value="trend">{t.reports.report_type_trend}</option>
                    <option value="comparison">{t.reports.report_type_comparison}</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="block text-sm font-medium text-ink-900 dark:text-white">
                    {t.reports.period}
                  </label>
                  <select
                    value={selectedPeriod}
                    onChange={(e) => setSelectedPeriod(e.target.value as 'week' | 'month' | 'quarter' | 'year')}
                    className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
                  >
                    <option value="week">{t.reports.period_week}</option>
                    <option value="month">{t.reports.period_month}</option>
                    <option value="quarter">{t.reports.period_quarter}</option>
                    <option value="year">{t.reports.period_year}</option>
                  </select>
                </div>

                {reportType !== 'comparison' && (
                  <div className="space-y-2 md:col-span-2">
                    <label className="block text-sm font-medium text-ink-900 dark:text-white">
                      {t.reports.city}
                    </label>
                    <select
                      value={selectedCity}
                      onChange={(e) => setSelectedCity(e.target.value)}
                      className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
                    >
                      <option value="">{t.reports.all_cities}</option>
                      {CITIES.map((city) => (
                        <option key={city} value={city}>
                          {translateCity(city, locale)}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="md:col-span-2">
                  <button
                    onClick={handleGenerateReport}
                    disabled={generating}
                    className="btn btn-primary w-full"
                    aria-busy={generating}
                  >
                    {generating ? t.reports.generating : t.reports.generate}
                  </button>
                </div>
              </div>
            </div>

            <div className="card p-6 space-y-4">
              <h2 className="text-xl font-bold text-ink-900 dark:text-white">{t.reports.previous_reports}</h2>
              <div className="space-y-3">
                {mockReports.map((report) => (
                  <motion.div
                    key={report.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center justify-between p-4 rounded-xl bg-slate-50 dark:bg-ink-900/50"
                  >
                    <div className="flex-1">
                      <div className="font-semibold text-ink-900 dark:text-white">{report.title}</div>
                      <div className="text-sm text-slate-600 dark:text-slate-400">
                        {new Date(report.generatedAt).toLocaleDateString(locale === 'ar' ? 'ar-SA' : 'en-US')}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                    <button
                      onClick={handleDownload}
                      className="btn border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 text-sm px-4 py-2 dark:border-slate-700 dark:bg-ink-900/50 dark:text-slate-300"
                    >
                      {t.reports.download}
                    </button>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>

          <div className="lg:col-span-1">
            <div className="card p-6 space-y-4 sticky top-24">
              <h3 className="text-lg font-bold text-ink-900 dark:text-white">{t.reports.quick_stats}</h3>
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-raboo3-50 dark:bg-raboo3-900/20">
                  <div className="text-sm text-slate-600 dark:text-slate-400">{t.reports.total_reports}</div>
                  <div className="text-2xl font-bold text-raboo3-600 dark:text-raboo3-400">
                    {mockReports.length}
                  </div>
                </div>
                <div className="p-4 rounded-xl bg-blue-50 dark:bg-blue-900/20">
                  <div className="text-sm text-slate-600 dark:text-slate-400">{t.reports.last_report}</div>
                  <div className="text-sm font-semibold text-blue-600 dark:text-blue-400">
                    {mockReports[0]?.generatedAt
                      ? new Date(mockReports[0].generatedAt).toLocaleDateString(locale === 'ar' ? 'ar-SA' : 'en-US')
                      : t.reports.none}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <h3 className="text-xl font-bold text-ink-900 dark:text-white mb-4">{t.reports.visual_analytics}</h3>
          <InsightsChart />
        </div>
      </div>
    </main>
  );
}

