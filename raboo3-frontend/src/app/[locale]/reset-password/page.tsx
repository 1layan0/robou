'use client';

import { useState, useEffect, useRef, Suspense } from 'react';
import type { Session } from '@supabase/supabase-js';
import { useRouter, useSearchParams } from 'next/navigation';
import { useNotifications } from '@/contexts/NotificationContext';
import Link from 'next/link';
import { useI18n, useT } from '@/i18n/useTranslations';
import { getSupabaseBrowser } from '@/lib/supabase/client';

function isStrongPassword(password: string) {
  return /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$/.test(password);
}

function ResetPasswordContent() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const router = useRouter();
  const searchParams = useSearchParams();
  const { addNotification } = useNotifications();
  const authErrorReported = useRef(false);
  const [formData, setFormData] = useState({
    password: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [recoveryReady, setRecoveryReady] = useState(false);
  const [checking, setChecking] = useState(true);
  const [passwordResetComplete, setPasswordResetComplete] = useState(false);

  const authError = searchParams.get('auth_error');
  const authErrorDesc = searchParams.get('auth_error_description');

  useEffect(() => {
    if (authErrorReported.current || !authError) return;
    authErrorReported.current = true;
    addNotification({
      type: 'error',
      title: t.common.error_generic,
      message: authErrorDesc || authError,
      duration: 10000,
    });
    router.replace(`/${locale}/reset-password`, { scroll: false });
  }, [authError, authErrorDesc, addNotification, router, locale, t.common.error_generic]);

  useEffect(() => {
    let cancelled = false;
    const supabase = getSupabaseBrowser();
    let subscription: { unsubscribe: () => void } | null = null;
    const timers: number[] = [];

    if (!supabase) {
      setChecking(false);
      setRecoveryReady(false);
      return;
    }

    const applySession = (session: Session | null) => {
      if (cancelled || !session) return;
      setRecoveryReady(true);
      setChecking(false);
    };

    const refreshSession = async () => {
      if (cancelled || typeof window === 'undefined') return;
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!cancelled) applySession(session);
    };

    void (async () => {
      if (typeof window === 'undefined') return;

      const code = new URLSearchParams(window.location.search).get('code');
      if (code) {
        const { error } = await supabase.auth.exchangeCodeForSession(code);
        if (error && process.env.NODE_ENV !== 'production') {
          console.warn('[reset-password] exchangeCodeForSession:', error.message);
        }
      }

      if (cancelled) return;
      await refreshSession();

      const { data } = supabase.auth.onAuthStateChange((event, nextSession) => {
        if (cancelled) return;
        if (event === 'PASSWORD_RECOVERY' || event === 'SIGNED_IN') {
          applySession(nextSession);
        }
      });
      subscription = data.subscription;

      [250, 900, 2200].forEach((ms) => {
        timers.push(window.setTimeout(() => void refreshSession(), ms));
      });

      timers.push(
        window.setTimeout(() => {
          if (!cancelled) setChecking(false);
        }, 4500)
      );
    })();

    return () => {
      cancelled = true;
      subscription?.unsubscribe();
      timers.forEach((id) => window.clearTimeout(id));
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const supabase = getSupabaseBrowser();
    if (!supabase) return;
    setLoading(true);

    if (!isStrongPassword(formData.password)) {
      addNotification({
        type: 'error',
        title: t.common.error_generic,
        message: isAr
          ? 'كلمة المرور ضعيفة: ٨ أحرف على الأقل، حرف كبير وصغير، رقم، ورمز.'
          : 'Weak password: at least 8 chars, upper & lower case, digit, and symbol.',
        duration: 4000,
      });
      setLoading(false);
      return;
    }

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

    try {
      const { error } = await supabase.auth.updateUser({ password: formData.password });
      if (error) {
        addNotification({
          type: 'error',
          title: t.common.error_generic,
          message: error.message ?? (isAr ? 'فشل التحديث' : 'Update failed'),
          duration: 6000,
        });
        setLoading(false);
        return;
      }
      await supabase.auth.signOut();
      if (typeof window !== 'undefined' && window.location.hash) {
        window.history.replaceState(null, '', window.location.pathname + window.location.search);
      }
      setPasswordResetComplete(true);
      setLoading(false);
      addNotification({
        type: 'success',
        title: t.reset_password.success_title,
        message: t.reset_password.success_message,
        duration: 6000,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      addNotification({
        type: 'error',
        title: t.common.error_generic,
        message: msg,
        duration: 5000,
      });
      setLoading(false);
    }
  };

  if (checking) {
    return (
      <main className="section min-h-screen flex items-center justify-center" dir={isAr ? 'rtl' : 'ltr'}>
        <div className="text-slate-500 dark:text-slate-400 text-sm">
          {isAr ? 'جاري التحقق من الرابط…' : 'Verifying link…'}
        </div>
      </main>
    );
  }

  if (passwordResetComplete) {
    return (
      <main className="section min-h-screen flex items-center justify-center" dir={isAr ? 'rtl' : 'ltr'}>
        <div className="container max-w-md">
          <div className="card p-8 space-y-6 text-center">
            <div
              className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 text-2xl"
              aria-hidden
            >
              ✓
            </div>
            <h1 className="text-2xl font-bold text-ink-900 dark:text-white">{t.reset_password.success_title}</h1>
            <p className="text-slate-600 dark:text-slate-400 text-sm leading-relaxed">
              {t.reset_password.success_message}
            </p>
            <div className="flex flex-col gap-3 pt-2">
              <Link href={`/${locale}`} className="btn btn-primary py-3 text-base font-semibold">
                {t.reset_password.go_home}
              </Link>
              <Link
                href={`/${locale}/login`}
                className="btn py-3 text-base font-semibold border border-slate-200 bg-white text-ink-900 hover:bg-slate-50 dark:border-white/15 dark:bg-ink-900/50 dark:text-white dark:hover:bg-white/10"
              >
                {t.reset_password.back_to_login}
              </Link>
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (!recoveryReady) {
    return (
      <main className="section min-h-screen flex items-center justify-center" dir={isAr ? 'rtl' : 'ltr'}>
        <div className="container max-w-md">
          <div className="card p-8 space-y-4 text-center">
            <h1 className="text-xl font-bold text-ink-900 dark:text-white">
              {isAr ? 'رابط غير صالح أو منتهي' : 'Invalid or expired link'}
            </h1>
            <p className="text-slate-600 dark:text-slate-400 text-sm">
              {isAr
                ? 'اطلبي رابطًا جديدًا من صفحة نسيت كلمة المرور، وتأكدي أن Supabase يسمح بـ /auth/callback و مسارات إعادة التعيين ضمن Redirect URLs.'
                : 'Request a new link from Forgot password, and ensure /auth/callback and reset URLs are in Supabase Redirect URLs.'}
            </p>
            <Link href={`/${locale}/forgot-password`} className="btn btn-primary inline-block">
              {t.forgot_password.title}
            </Link>
            <div>
              <Link href={`/${locale}/login`} className="text-sm text-raboo3-600 dark:text-raboo3-400">
                {t.reset_password.back_to_login}
              </Link>
            </div>
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
            <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white">{t.reset_password.title}</h1>
            <p className="text-slate-600 dark:text-slate-400">{t.reset_password.subtitle}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
              {isAr
                ? 'إن وُجد حساب، الرابط من الإيميل يثبت هويتك في Supabase.'
                : 'If an account exists, the link from your email proves your identity to Supabase.'}
            </p>
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
                minLength={8}
                autoComplete="new-password"
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
                minLength={8}
                autoComplete="new-password"
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

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <main className="section min-h-screen flex items-center justify-center">
          <div className="animate-pulse text-slate-500">…</div>
        </main>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}
