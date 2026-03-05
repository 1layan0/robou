'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useNotifications } from '@/contexts/NotificationContext';
import Link from 'next/link';
import { useI18n, useT } from '@/i18n/useTranslations';
import { useAuth } from '@/contexts/AuthContext';

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFirstNameError(null);
    setLastNameError(null);
    setPasswordError(null);
    setLoading(true);

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

    // Mock signup - replace with actual API call
    setTimeout(() => {
      login({
        firstName: formData.firstName.trim() || (isAr ? 'مستخدم' : 'User'),
        lastName: formData.lastName.trim() || '',
        email: formData.email.trim(),
        phone: '',
      });
      addNotification({
        type: 'success',
        title: isAr ? 'تم إنشاء الحساب بنجاح' : 'Account Created',
        message: isAr ? 'مرحباً بك في منصة ربوع' : 'Welcome to Robou',
        duration: 3000,
      });
      router.push(`/${locale}`);
      setLoading(false);
    }, 1500);
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

