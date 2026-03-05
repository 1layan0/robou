'use client';

import { useState } from 'react';
import { useNotifications } from '@/contexts/NotificationContext';
import { useI18n, useT } from '@/i18n/useTranslations';

export default function SystemSettingsPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const { addNotification } = useNotifications();
  const [settings, setSettings] = useState({
    maintenanceMode: false,
    allowRegistrations: true,
    requireEmailVerification: true,
    maxUploadSize: '10',
    sessionTimeout: '30',
    enableAnalytics: true,
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    setTimeout(() => {
      addNotification({
        type: 'success',
        title: isAr ? 'تم حفظ الإعدادات' : 'Settings Saved',
        message: isAr ? 'تم تحديث إعدادات النظام بنجاح' : 'System settings updated successfully',
        duration: 3000,
      });
      setLoading(false);
    }, 1000);
  };

  return (
    <main className="section" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container max-w-4xl space-y-8">
        <header className="space-y-3">
          <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl">
            {t.admin_settings.title}
          </h1>
          <p className="text-base leading-relaxed text-slate-600 dark:text-slate-300">
            {t.admin_settings.subtitle}
          </p>
        </header>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="card p-6 space-y-4">
            <h2 className="text-xl font-bold text-ink-900 dark:text-white">{t.admin_settings.general}</h2>
            
            <div className="flex items-center justify-between">
              <div>
                <label className="block text-sm font-medium text-ink-900 dark:text-white">
                  {t.admin_settings.maintenance_mode}
                </label>
                <p className="text-xs text-slate-500 dark:text-slate-400">{t.admin_settings.maintenance_mode_desc}</p>
              </div>
              <input
                type="checkbox"
                checked={settings.maintenanceMode}
                onChange={(e) => setSettings({ ...settings, maintenanceMode: e.target.checked })}
                className="h-5 w-5 rounded border-slate-300 text-raboo3-600 focus:ring-raboo3-500"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="block text-sm font-medium text-ink-900 dark:text-white">
                  {t.admin_settings.allow_registrations}
                </label>
                <p className="text-xs text-slate-500 dark:text-slate-400">{t.admin_settings.allow_registrations_desc}</p>
              </div>
              <input
                type="checkbox"
                checked={settings.allowRegistrations}
                onChange={(e) => setSettings({ ...settings, allowRegistrations: e.target.checked })}
                className="h-5 w-5 rounded border-slate-300 text-raboo3-600 focus:ring-raboo3-500"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="block text-sm font-medium text-ink-900 dark:text-white">
                  {t.admin_settings.require_email_verification}
                </label>
                <p className="text-xs text-slate-500 dark:text-slate-400">{t.admin_settings.require_email_verification_desc}</p>
              </div>
              <input
                type="checkbox"
                checked={settings.requireEmailVerification}
                onChange={(e) => setSettings({ ...settings, requireEmailVerification: e.target.checked })}
                className="h-5 w-5 rounded border-slate-300 text-raboo3-600 focus:ring-raboo3-500"
              />
            </div>
          </div>

          <div className="card p-6 space-y-4">
            <h2 className="text-xl font-bold text-ink-900 dark:text-white">{t.admin_settings.upload}</h2>
            
            <div>
              <label className="block text-sm font-medium text-ink-900 dark:text-white mb-2">
                {t.admin_settings.max_upload_size} (MB)
              </label>
              <input
                type="number"
                value={settings.maxUploadSize}
                onChange={(e) => setSettings({ ...settings, maxUploadSize: e.target.value })}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
              />
            </div>
          </div>

          <div className="card p-6 space-y-4">
            <h2 className="text-xl font-bold text-ink-900 dark:text-white">{t.admin_settings.security}</h2>
            
            <div>
              <label className="block text-sm font-medium text-ink-900 dark:text-white mb-2">
                {t.admin_settings.session_timeout} (minutes)
              </label>
              <input
                type="number"
                value={settings.sessionTimeout}
                onChange={(e) => setSettings({ ...settings, sessionTimeout: e.target.value })}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3">
            <button
              type="button"
              className="px-6 py-2 rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-ink-900 dark:text-slate-300 dark:hover:bg-ink-800"
            >
              {t.admin_settings.cancel}
            </button>
            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary px-6 py-2"
            >
              {loading ? t.common.loading : t.admin_settings.save}
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}

