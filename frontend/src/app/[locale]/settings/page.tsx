'use client';

import { useState } from 'react';
import { useNotifications } from '@/contexts/NotificationContext';
import { useI18n, useT } from '@/i18n/useTranslations';

export default function SettingsPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const { addNotification } = useNotifications();
  const [formData, setFormData] = useState({
    name: 'أحمد محمد',
    email: 'ahmed@example.com',
    phone: '+966501234567',
    language: locale,
    notifications: true,
    emailUpdates: true,
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    // Mock save - replace with actual API call
    setTimeout(() => {
      addNotification({
        type: 'success',
        title: isAr ? 'تم حفظ الإعدادات' : 'Settings Saved',
        message: isAr ? 'تم تحديث إعداداتك بنجاح' : 'Your settings have been updated',
        duration: 3000,
      });
      setLoading(false);
    }, 1000);
  };

  return (
    <main className="section" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container max-w-4xl space-y-8">
        <header className="space-y-2">
          <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl">
            {t.settings.title}
          </h1>
          <p className="text-base leading-relaxed text-slate-600 dark:text-slate-300">
            {t.settings.subtitle}
          </p>
        </header>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="card p-6 space-y-4">
            <h2 className="text-xl font-bold text-ink-900 dark:text-white">{t.settings.profile}</h2>
            
            <div>
              <label className="block text-sm font-medium text-ink-900 dark:text-white mb-2">
                {t.settings.name}
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-ink-900 dark:text-white mb-2">
                {t.settings.email}
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-ink-900 dark:text-white mb-2">
                {t.settings.phone}
              </label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
              />
            </div>
          </div>

          <div className="card p-6 space-y-4">
            <h2 className="text-xl font-bold text-ink-900 dark:text-white">{t.settings.preferences}</h2>
            
            <div>
              <label className="block text-sm font-medium text-ink-900 dark:text-white mb-2">
                {t.settings.language}
              </label>
              <select
                value={formData.language}
                onChange={(e) => setFormData({ ...formData, language: e.target.value as 'ar' | 'en' })}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
              >
                <option value="ar">{t.common.language_ar}</option>
                <option value="en">{t.common.language_en}</option>
              </select>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="block text-sm font-medium text-ink-900 dark:text-white">
                  {t.settings.notifications}
                </label>
                <p className="text-xs text-slate-500 dark:text-slate-400">{t.settings.notifications_desc}</p>
              </div>
              <input
                type="checkbox"
                checked={formData.notifications}
                onChange={(e) => setFormData({ ...formData, notifications: e.target.checked })}
                className="h-5 w-5 rounded border-slate-300 text-raboo3-600 focus:ring-raboo3-500"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="block text-sm font-medium text-ink-900 dark:text-white">
                  {t.settings.email_updates}
                </label>
                <p className="text-xs text-slate-500 dark:text-slate-400">{t.settings.email_updates_desc}</p>
              </div>
              <input
                type="checkbox"
                checked={formData.emailUpdates}
                onChange={(e) => setFormData({ ...formData, emailUpdates: e.target.checked })}
                className="h-5 w-5 rounded border-slate-300 text-raboo3-600 focus:ring-raboo3-500"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3">
            <button
              type="button"
              className="px-6 py-2 rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-ink-900 dark:text-slate-300 dark:hover:bg-ink-800"
            >
              {t.settings.cancel}
            </button>
            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary px-6 py-2"
            >
              {loading ? t.common.loading : t.settings.save}
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}

