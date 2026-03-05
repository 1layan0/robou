'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useNotifications } from '@/contexts/NotificationContext';
import Link from 'next/link';
import { useI18n, useT } from '@/i18n/useTranslations';

export default function ResetPasswordPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const router = useRouter();
  const searchParams = useSearchParams();
  const { addNotification } = useNotifications();
  const [formData, setFormData] = useState({
    password: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const tokenParam = searchParams.get('token');
    if (!tokenParam) {
      addNotification({
        type: 'error',
        title: t.common.error_generic,
        message: isAr ? 'رابط غير صالح' : 'Invalid link',
        duration: 3000,
      });
      router.push(`/${locale}/forgot-password`);
    } else {
      setToken(tokenParam);
    }
  }, [searchParams, router, locale, addNotification, t.common.error_generic, isAr]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    if (formData.password !== formData.confirmPassword) {
      addNotification({
        type: 'error',
        title: t.common.error_generic,
        message: isAr ? 'كلمات المرور غير متطابقة' : 'Passwords do not match',
        duration: 3000,
      });
      setLoading(false);
      return;
    }

    // Mock password reset - replace with actual API call
    setTimeout(() => {
      addNotification({
        type: 'success',
        title: isAr ? 'تم تغيير كلمة المرور بنجاح' : 'Password Changed',
        message: isAr ? 'يمكنك الآن تسجيل الدخول' : 'You can now login',
        duration: 3000,
      });
      router.push(`/${locale}/login`);
      setLoading(false);
    }, 1500);
  };

  if (!token) {
    return null;
  }

  return (
    <main className="section min-h-screen flex items-center justify-center" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container max-w-md">
        <div className="card p-8 space-y-6">
          <header className="text-center space-y-2">
            <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white">{t.reset_password.title}</h1>
            <p className="text-slate-600 dark:text-slate-400">{t.reset_password.subtitle}</p>
          </header>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-ink-900 dark:text-white mb-2">
                {t.reset_password.new_password}
              </label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                placeholder={t.reset_password.new_password_placeholder}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-ink-900 dark:text-white mb-2">
                {t.reset_password.confirm_password}
              </label>
              <input
                type="password"
                value={formData.confirmPassword}
                onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                required
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                placeholder={t.reset_password.confirm_password_placeholder}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn btn-primary py-3 text-base font-semibold"
            >
              {loading ? t.common.loading : t.reset_password.submit}
            </button>
          </form>

          <div className="text-center text-sm text-slate-600 dark:text-slate-400">
            <Link href={`/${locale}/login`} className="text-raboo3-600 hover:text-raboo3-700 dark:text-raboo3-400 font-semibold">
              {t.reset_password.back_to_login}
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}

