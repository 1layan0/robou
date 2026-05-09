'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useNotifications } from '@/contexts/NotificationContext';
import Link from 'next/link';
import { useI18n, useT } from '@/i18n/useTranslations';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/lib/supabase/client';

export default function LoginPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const router = useRouter();
  const { addNotification } = useNotifications();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setLoading(true);
    const emailTrimmed = email.trim();
    if (!supabase) {
      setErrorMsg(isAr ? 'اتصال Supabase غير متوفر. تأكدي من .env.local (NEXT_PUBLIC_SUPABASE_URL و ANON_KEY) ثم أعدي تشغيل السيرفر.' : 'Supabase not configured. Check .env.local (NEXT_PUBLIC_SUPABASE_URL, ANON_KEY) and restart.');
      setLoading(false);
      return;
    }
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email: emailTrimmed,
        password,
      });

      if (error) {
        console.error('Supabase login error:', error);
        const rawMsg = error.message;
        const isKeyError =
          /invalid api key|jwt|anon key|project_ref/i.test(rawMsg) || rawMsg.includes('Invalid API key');
        const message = isKeyError
          ? (isAr
              ? 'مفتاح Supabase غلط. من لوحة Supabase: Project Settings → API انسخي مفتاح "anon" "public" (الطويل اللي يبدأ بـ eyJ) وضعيه في .env.local ثم أعدي تشغيل السيرفر.'
              : 'Wrong Supabase key. In Dashboard: Project Settings → API copy the anon key into .env.local then restart.')
          : rawMsg;
        setErrorMsg(message);
        addNotification({
          type: 'error',
          title: isAr ? 'خطأ في تسجيل الدخول' : 'Login Error',
          message,
          duration: 6000,
        });
        setLoading(false);
        return;
      }

      if (!data.session) {
        const msg = isAr ? 'لم تُرجَع جلسة. تأكدي من تفعيل تسجيل الدخول بالإيميل في Supabase.' : 'No session returned. Ensure Email sign-in is enabled in Supabase.';
        console.error('Supabase login: no session after success', data);
        setErrorMsg(msg);
        addNotification({ type: 'error', title: isAr ? 'خطأ في تسجيل الدخول' : 'Login Error', message: msg, duration: 5000 });
        setLoading(false);
        return;
      }

      const u = data.session.user;
      login({
        id: u.id,
        firstName: (u.user_metadata?.first_name as string | undefined) || (isAr ? 'مستخدم' : 'User'),
        lastName: (u.user_metadata?.last_name as string | undefined) || '',
        email: u.email ?? emailTrimmed,
        phone: (u.phone as string | null) ?? null,
      });
      addNotification({
        type: 'success',
        title: isAr ? 'تم تسجيل الدخول بنجاح' : 'Login Successful',
        message: isAr ? 'مرحباً بك في منصة ربوع' : 'Welcome to Robou',
        duration: 3000,
      });
      router.replace(`/${locale}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error('Login exception:', err);
      setErrorMsg(msg);
      addNotification({
        type: 'error',
        title: isAr ? 'خطأ في تسجيل الدخول' : 'Login Error',
        message: msg,
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
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
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className={`w-full rounded-xl border border-slate-200 bg-white py-2 text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400 ${isAr ? 'pr-4 pl-11' : 'pl-4 pr-11'}`}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? (isAr ? 'إخفاء كلمة المرور' : 'Hide password') : (isAr ? 'إظهار كلمة المرور' : 'Show password')}
                  className={`absolute inset-y-0 flex items-center text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 ${isAr ? 'left-3' : 'right-3'}`}
                >
                  {showPassword ? (
                    <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 3l18 18M10.58 10.58A2 2 0 0012 14a2 2 0 001.42-.58M9.88 4.24A10.94 10.94 0 0112 4c5.05 0 9.27 3.11 10 8-.2 1.34-.76 2.58-1.57 3.64M6.1 6.1C4.27 7.46 2.97 9.53 2 12c.73 4.89 4.95 8 10 8 1.76 0 3.41-.38 4.89-1.05" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M2 12s3.5-8 10-8 10 8 10 8-3.5 8-10 8-10-8-10-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
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
                <span className="text-slate-600 dark:text-slate-300">{isAr ? 'تذكرني' : 'Remember me'}</span>
              </label>
              <Link
                href={`/${locale}/forgot-password`}
                className="text-raboo3-600 hover:text-raboo3-700 dark:text-raboo3-400"
              >
                {t.login.forgot_password}
              </Link>
            </div>

            {errorMsg && (
              <div className="rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
                {errorMsg}
              </div>
            )}

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

