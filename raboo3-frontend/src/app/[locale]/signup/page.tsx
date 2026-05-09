'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useNotifications } from '@/contexts/NotificationContext';
import Link from 'next/link';
import { useI18n, useT } from '@/i18n/useTranslations';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/lib/supabase/client';

function isLettersOnly(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return false;
  // Letters (Arabic/English/other locales) and spaces only
  return /^[\p{L}\s]+$/u.test(trimmed);
}

function isStrongPassword(password: string) {
  // At least 8 characters, one uppercase, one lowercase, one digit, and one special character
  return /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$/.test(password);
}

export default function SignupPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const router = useRouter();
  const { addNotification } = useNotifications();
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [firstNameError, setFirstNameError] = useState<string | null>(null);
  const [lastNameError, setLastNameError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFirstNameError(null);
    setLastNameError(null);
    setPasswordError(null);
    setSubmitError(null);
    setLoading(true);

    if (!supabase) {
      const msg = isAr ? 'اتصال Supabase غير متوفر. تأكدي من .env.local (NEXT_PUBLIC_SUPABASE_URL و NEXT_PUBLIC_SUPABASE_ANON_KEY) ثم أعدي تشغيل السيرفر.' : 'Supabase not configured. Add NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY to .env.local and restart.';
      setSubmitError(msg);
      setLoading(false);
      return;
    }

    const invalidFirst = !isLettersOnly(formData.firstName);
    const invalidLast = !isLettersOnly(formData.lastName);

    if (invalidFirst || invalidLast) {
      const baseMessageAr = 'الرجاء إدخال الاسم باستخدام حروف فقط بدون أرقام أو رموز.';
      const baseMessageEn = 'Please use letters only (no numbers or symbols).';

      if (invalidFirst) {
        setFirstNameError(isAr ? baseMessageAr : baseMessageEn);
      }
      if (invalidLast) {
        setLastNameError(isAr ? baseMessageAr : baseMessageEn);
      }

      addNotification({
        type: 'error',
        title: t.common.error_generic,
        message: isAr
          ? 'تأكد من أن الاسم الأول والاسم الثاني يحتويان على حروف فقط.'
          : 'Please make sure first and last name contain letters only.',
        duration: 4000,
      });
      setLoading(false);
      return;
    }

    if (!isStrongPassword(formData.password)) {
      addNotification({
        type: 'error',
        title: t.common.error_generic,
        message: isAr
          ? 'كلمة المرور ضعيفة. يجب أن تحتوي على ٨ أحرف على الأقل، وحرف كبير، وحرف صغير، ورقم، ورمز.'
          : 'Password is too weak. It must be at least 8 characters and include uppercase, lowercase, a number, and a symbol.',
        duration: 4000,
      });
      setPasswordError(
        isAr
          ? 'كلمة المرور ضعيفة. يجب أن تحتوي على ٨ أحرف على الأقل، وحرف كبير، وحرف صغير، ورقم، ورمز.'
          : 'Password is too weak. It must be at least 8 characters and include uppercase, lowercase, a number, and a symbol.'
      );
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
      setPasswordError(isAr ? 'كلمات المرور غير متطابقة' : 'Passwords do not match');
      setLoading(false);
      return;
    }

    try {
      const emailTrimmed = formData.email.trim();
      const { data, error } = await supabase.auth.signUp({
        email: emailTrimmed,
        password: formData.password,
        options: {
          data: {
            first_name: formData.firstName.trim(),
            last_name: formData.lastName.trim(),
          },
        },
      });
      if (process.env.NODE_ENV !== 'production') {
        console.log('[Signup] Supabase response:', { data, error });
      }
      if (error) {
        const isKeyError =
          /invalid api key|jwt|anon key|project_ref|unauthorized/i.test(error.message) ||
          error.message.includes('Invalid API key');
        const message = isKeyError
          ? (isAr
              ? 'مفتاح Supabase غير مقبول. من لوحة Supabase: Project Settings → API Keys انسخي مفتاح Publishable (أو Legacy anon اللي يبدأ بـ eyJ) وضعيه في .env.local ثم أعدي تشغيل السيرفر.'
              : 'Supabase key not accepted. In Dashboard: Project Settings → API Keys copy the Publishable key (or Legacy anon starting with eyJ) into .env.local then restart dev server.')
          : error.message;
        setSubmitError(message);
        addNotification({
          type: 'error',
          title: t.common.error_generic,
          message,
          duration: 6000,
        });
        setLoading(false);
        return;
      }
      if (data.session?.user) {
        const u = data.session.user;
        login({
          id: u.id,
          firstName: formData.firstName.trim() || (isAr ? 'مستخدم' : 'User'),
          lastName: formData.lastName.trim() || '',
          email: u.email ?? emailTrimmed,
          phone: (u.phone as string | null) ?? null,
        });
        addNotification({
          type: 'success',
          title: isAr ? 'تم إنشاء الحساب بنجاح' : 'Account Created',
          message: isAr ? 'مرحباً بك في منصة ربوع' : 'Welcome to Robou',
          duration: 3000,
        });
        router.push(`/${locale}`);
      } else if (data.user) {
        addNotification({
          type: 'success',
          title: isAr ? 'تم إنشاء الحساب' : 'Account Created',
          message: isAr ? 'سجّلي الدخول من صفحة تسجيل الدخول.' : 'Log in from the login page.',
          duration: 4000,
        });
        router.push(`/${locale}/login`);
      } else {
        const msg = isAr
          ? 'لم يرجع Supabase مستخدم. تأكدي من: Authentication → Providers → Email مفعّل. افتحي Console (F12) وابحثي عن [Signup] وشاركيني الرسالة.'
          : 'Supabase did not return a user. Ensure Authentication → Providers → Email is enabled. Open Console (F12), look for [Signup] and share that message.';
        setSubmitError(msg);
        addNotification({
          type: 'warning',
          title: isAr ? 'لم يكتمل التسجيل' : 'Signup incomplete',
          message: msg,
          duration: 6000,
        });
      }
      setLoading(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      if (process.env.NODE_ENV !== 'production') console.error('[Signup] Exception:', err);
      setSubmitError(msg);
      addNotification({
        type: 'error',
        title: t.common.error_generic,
        message: msg,
        duration: 5000,
      });
      setLoading(false);
    }
  };

  return (
    <main className="section min-h-screen flex items-center justify-center" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container max-w-md">
        <div className="card p-8 space-y-6">
          <header className="text-center space-y-2">
            <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white">{t.signup.title}</h1>
            <p className="text-slate-600 dark:text-slate-400">{t.signup.subtitle}</p>
          </header>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-ink-900 dark:text-white mb-2">
                  {isAr ? 'الاسم الأول' : 'First name'}
                </label>
                <input
                  type="text"
                  value={formData.firstName}
                  onChange={(e) => {
                    setFormData({ ...formData, firstName: e.target.value });
                    if (firstNameError) setFirstNameError(null);
                  }}
                  required
                  className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                  placeholder={isAr ? 'الاسم الأول' : 'First name'}
                />
                {firstNameError && (
                  <p className="mt-1 text-xs text-red-600 dark:text-red-400">{firstNameError}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-ink-900 dark:text-white mb-2">
                  {isAr ? 'اسم العائلة' : 'Last name'}
                </label>
                <input
                  type="text"
                  value={formData.lastName}
                  onChange={(e) => {
                    setFormData({ ...formData, lastName: e.target.value });
                    if (lastNameError) setLastNameError(null);
                  }}
                  required
                  className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                  placeholder={isAr ? 'اسم العائلة' : 'Last name'}
                />
                {lastNameError && (
                  <p className="mt-1 text-xs text-red-600 dark:text-red-400">{lastNameError}</p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-ink-900 dark:text-white mb-2">
                {t.signup.email}
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                placeholder={t.signup.email_placeholder}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-ink-900 dark:text-white mb-2">
                {t.signup.password}
              </label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                placeholder={t.signup.password_placeholder}
              />
              {passwordError && (
                <p className="mt-1 text-xs text-red-600 dark:text-red-400">{passwordError}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-ink-900 dark:text-white mb-2">
                {t.signup.confirm_password}
              </label>
              <input
                type="password"
                value={formData.confirmPassword}
                onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                required
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                placeholder={t.signup.confirm_password_placeholder}
              />
            </div>

            {submitError && (
              <div className="rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
                {submitError}
              </div>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full btn btn-primary py-3 text-base font-semibold"
            >
              {loading ? t.common.loading : t.signup.submit}
            </button>
          </form>

          <div className="text-center text-sm text-slate-600 dark:text-slate-400">
            {t.signup.already_have_account}{' '}
            <Link href={`/${locale}/login`} className="text-raboo3-600 hover:text-raboo3-700 dark:text-raboo3-400 font-semibold">
              {t.signup.login_link}
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}

