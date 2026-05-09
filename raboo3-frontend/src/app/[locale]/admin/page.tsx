'use client';

import Link from 'next/link';
import { useNotifications } from '@/contexts/NotificationContext';
import { useI18n, useT } from '@/i18n/useTranslations';

export default function AdminPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const { addNotification, clearAll } = useNotifications();

  const handleSystemNotification = () => {
    addNotification({
      type: 'system',
      title: t.admin.system_notification,
      message: isAr ? 'تم تحديث قاعدة البيانات بنجاح. جميع البيانات محدثة.' : 'Database updated successfully. All data is up to date.',
      duration: 5000,
    });
  };

  const handleAdminNotification = () => {
    addNotification({
      type: 'admin',
      title: t.admin.admin_notification,
      message: isAr ? 'لديك 5 طلبات جديدة تحتاج إلى مراجعة.' : 'You have 5 new requests that need review.',
      duration: 6000,
    });
  };

  const handleSuccessNotification = () => {
    addNotification({
      type: 'success',
      title: t.admin.success_notification,
      message: isAr ? 'تم حفظ التغييرات بنجاح.' : 'Changes saved successfully.',
      duration: 3000,
    });
  };

  const handleErrorNotification = () => {
    addNotification({
      type: 'error',
      title: t.admin.error_notification,
      message: isAr ? 'حدث خطأ أثناء معالجة الطلب. يرجى المحاولة مرة أخرى.' : 'An error occurred while processing the request. Please try again.',
      duration: 5000,
    });
  };

  const handleWarningNotification = () => {
    addNotification({
      type: 'warning',
      title: t.admin.warning_notification,
      message: isAr ? 'هناك مشكلة محتملة تحتاج إلى انتباهك.' : 'There is a potential issue that needs your attention.',
      duration: 4000,
    });
  };

  return (
    <main className="section" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container max-w-6xl space-y-8">
        <header className="space-y-3">
          <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl">
            {t.admin.title}
          </h1>
          <p className="text-base leading-relaxed text-slate-600 dark:text-slate-300">
            {t.admin.subtitle}
          </p>
        </header>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Link href={`/${locale}/admin/users`} className="card p-6 hover:shadow-xl transition-shadow">
            <div className="space-y-3">
              <div className="w-12 h-12 rounded-xl bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                <span className="text-2xl">👥</span>
              </div>
              <h3 className="text-xl font-bold text-ink-900 dark:text-white">{t.admin.user_management}</h3>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {t.admin.user_management_desc}
              </p>
            </div>
          </Link>

          <Link href={`/${locale}/upload`} className="card p-6 hover:shadow-xl transition-shadow">
            <div className="space-y-3">
              <div className="w-12 h-12 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <span className="text-2xl">📤</span>
              </div>
              <h3 className="text-xl font-bold text-ink-900 dark:text-white">{t.admin.data_upload}</h3>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {t.admin.data_upload_desc}
              </p>
            </div>
          </Link>

          <Link href={`/${locale}/reports`} className="card p-6 hover:shadow-xl transition-shadow">
            <div className="space-y-3">
              <div className="w-12 h-12 rounded-xl bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                <span className="text-2xl">📊</span>
              </div>
              <h3 className="text-xl font-bold text-ink-900 dark:text-white">{t.admin.reports}</h3>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {t.admin.reports_desc}
              </p>
            </div>
          </Link>
        </div>

        <div className="card p-8 space-y-6">
          <header className="space-y-2">
            <h2 className="text-2xl font-bold text-ink-900 dark:text-white">
              {t.admin.test_notifications}
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              {t.admin.test_notifications_desc}
            </p>
          </header>

          <div className="grid gap-4 md:grid-cols-2">
            <button
              onClick={handleSystemNotification}
              className="btn border border-slate-200 bg-white hover:bg-slate-50 dark:border-slate-700 dark:bg-ink-900/50 dark:hover:bg-ink-900"
            >
              {t.admin.system_notification}
            </button>
            <button
              onClick={handleAdminNotification}
              className="btn border border-purple-200 bg-purple-50 hover:bg-purple-100 text-purple-700 dark:border-purple-800 dark:bg-purple-900/20 dark:text-purple-300"
            >
              {t.admin.admin_notification}
            </button>
            <button
              onClick={handleSuccessNotification}
              className="btn border border-green-200 bg-green-50 hover:bg-green-100 text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300"
            >
              {t.admin.success_notification}
            </button>
            <button
              onClick={handleErrorNotification}
              className="btn border border-red-200 bg-red-50 hover:bg-red-100 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300"
            >
              {t.admin.error_notification}
            </button>
            <button
              onClick={handleWarningNotification}
              className="btn border border-yellow-200 bg-yellow-50 hover:bg-yellow-100 text-yellow-700 dark:border-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300"
            >
              {t.admin.warning_notification}
            </button>
            <button
              onClick={clearAll}
              className="btn border border-slate-200 bg-slate-100 hover:bg-slate-200 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
            >
              {t.admin.clear_all}
            </button>
          </div>

          <div className="mt-8 p-4 bg-slate-50 dark:bg-ink-900/50 rounded-xl">
            <h2 className="font-semibold mb-2 text-ink-900 dark:text-white">{t.admin.info_title}</h2>
            <ul className="text-sm text-slate-600 dark:text-slate-300 space-y-1 list-disc list-inside">
              <li>{t.admin.info_item1}</li>
              <li>{t.admin.info_item2}</li>
              <li>{t.admin.info_item3}</li>
              <li>{t.admin.info_item4}</li>
            </ul>
          </div>
        </div>
      </div>
    </main>
  );
}

