'use client';

import { useState } from 'react';
import { useNotifications } from '@/contexts/NotificationContext';
import Link from 'next/link';
import { useI18n, useT } from '@/i18n/useTranslations';

export default function ForgotPasswordPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const { addNotification } = useNotifications();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    // Mock password reset - replace with actual API call
    setTimeout(() => {
      setSent(true);
      addNotification({
        type: 'success',
        title: isAr ? 'تم إرسال رابط إعادة تعيين كلمة المرور' : 'Reset Link Sent',
        message: isAr ? 'تحقق من بريدك الإلكتروني' : 'Check your email',
        duration: 5000,
      });
      setLoading(false);
    }, 1500);
  };

  if (sent) {
    return (
      <main className="section min-h-screen flex items-center justify-center" dir={isAr ? 'rtl' : 'ltr'}>
        <div className="container max-w-md">
          <div className="card p-8 space-y-6 text-center">
            <div className="text-6xl mb-4">📧</div>
            <h1 className="text-2xl font-bold text-ink-900 dark:text-white">{t.forgot_password.check_email}</h1>
            <p className="text-slate-600 dark:text-slate-400">{t.forgot_password.check_email_message}</p>
            <Link href={`/${locale}/login`} className="btn btn-primary">
              {t.forgot_password.back_to_login}
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="section min-h-screen flex items-center justify-center" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container max-w-md">
        <div className="card p-8 space-y-6">
          <header className="text-center space-y-2">
            <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white">{t.forgot_password.title}</h1>
            <p className="text-slate-600 dark:text-slate-400">{t.forgot_password.subtitle}</p>
          </header>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-ink-900 dark:text-white mb-2">
                {t.forgot_password.email}
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                placeholder={t.forgot_password.email_placeholder}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn btn-primary py-3 text-base font-semibold"
            >
              {loading ? t.common.loading : t.forgot_password.submit}
            </button>
          </form>

          <div className="text-center text-sm text-slate-600 dark:text-slate-400">
            <Link href={`/${locale}/login`} className="text-raboo3-600 hover:text-raboo3-700 dark:text-raboo3-400 font-semibold">
              {t.forgot_password.back_to_login}
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}

