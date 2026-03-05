'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useNotifications } from '@/contexts/NotificationContext';
import Link from 'next/link';
import { useI18n, useT } from '@/i18n/useTranslations';
import { useAuth, getStoredUser } from '@/contexts/AuthContext';

export default function LoginPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const router = useRouter();
  const { addNotification } = useNotifications();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    // Mock login - replace with actual API call
    setTimeout(() => {
      if (email && password) {
        const emailTrimmed = email.trim();
        const stored = getStoredUser();
        if (stored && stored.email === emailTrimmed) {
          login(stored);
        } else {
          const nameFromEmail = emailTrimmed.split('@')[0] || '';
          const parts = nameFromEmail.split(/[.\s_-]+/).filter(Boolean);
          const firstName = parts[0] || (isAr ? 'مستخدم' : 'User');
          const lastName = parts[1] || '';
          login({
            firstName,
            lastName,
            email: emailTrimmed,
            phone: '',
          });
        }
        addNotification({
          type: 'success',
          title: isAr ? 'تم تسجيل الدخول بنجاح' : 'Login Successful',
          message: isAr ? 'مرحباً بك في منصة ربوع' : 'Welcome to Robou',
          duration: 3000,
        });
        router.push(`/${locale}`);
      } else {
        addNotification({
          type: 'error',
          title: isAr ? 'خطأ في تسجيل الدخول' : 'Login Error',
          message: isAr ? 'يرجى التحقق من البريد الإلكتروني وكلمة المرور' : 'Please check your email and password',
          duration: 4000,
        });
      }
      setLoading(false);
    }, 1000);
  };

  return (
    <main className="section min-h-screen flex items-center justify-center" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container max-w-md">
        <div className="card p-8 space-y-6">
          <header className="text-center space-y-2">
            <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white">
              {t.login.title}
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              {isAr ? 'أدخل بياناتك للوصول إلى حسابك' : 'Enter your credentials to access your account'}
            </p>
          </header>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label htmlFor="email" className="block text-sm font-medium text-ink-900 dark:text-white">
                {t.login.email}
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                placeholder="example@email.com"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="password" className="block text-sm font-medium text-ink-900 dark:text-white">
                {t.login.password}
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                placeholder="••••••••"
              />
            </div>

            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="sr-only"
                />
                <span
                  className={`inline-flex h-5 w-5 items-center justify-center rounded border transition-colors ${
                    rememberMe
                      ? 'border-green-600 bg-green-600'
                      : 'border-slate-300 bg-white dark:bg-ink-900'
                  }`}
                >
                  {rememberMe && (
                    <span className="text-[12px] font-semibold text-white leading-none">
                      ✓
                    </span>
                  )}
                </span>
                <span className="text-slate-600 dark:text-slate-300">تذكرني</span>
              </label>
              <Link
                href={`/${locale}/forgot-password`}
                className="text-raboo3-600 hover:text-raboo3-700 dark:text-raboo3-400"
              >
                {t.login.forgot_password}
              </Link>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn btn-primary py-3 text-base font-semibold"
              aria-busy={loading}
            >
              {loading ? (isAr ? 'جاري تسجيل الدخول...' : 'Logging in...') : t.login.submit}
            </button>
          </form>

          <div className="text-center text-sm text-slate-600 dark:text-slate-300">
            {isAr ? 'ليس لديك حساب؟' : "Don't have an account?"}{' '}
            <Link
              href={`/${locale}/signup`}
              className="text-raboo3-600 hover:text-raboo3-700 dark:text-raboo3-400 font-semibold"
            >
              {t.login.signup}
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}

