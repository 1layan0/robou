'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { useI18n, useT } from '@/i18n/useTranslations';
import { useNotifications } from '@/contexts/NotificationContext';

export default function AccountPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const router = useRouter();
  const { user, updateProfile, logout, deleteAccount } = useAuth();
  const { addNotification } = useNotifications();

  const [firstName, setFirstName] = useState(user?.firstName ?? '');
  const [lastName, setLastName] = useState(user?.lastName ?? '');
  const [email, setEmail] = useState(user?.email ?? '');
  const [phone, setPhone] = useState(user?.phone ?? '');
  const [saving, setSaving] = useState(false);
  const [showSavedMessage, setShowSavedMessage] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const savePopupTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // إذا المستخدم غير مسجل دخول، نحوله لصفحة تسجيل الدخول
  useEffect(() => {
    if (!user) {
      router.replace(`/${locale}/login`);
    }
  }, [user, router, locale]);

  useEffect(() => {
    if (user) {
      setFirstName(user.firstName ?? '');
      setLastName(user.lastName ?? '');
      setEmail(user.email ?? '');
      setPhone(user.phone ?? '');
    }
  }, [user]);

  useEffect(() => {
    return () => {
      if (savePopupTimerRef.current) clearTimeout(savePopupTimerRef.current);
    };
  }, []);

  if (!user) {
    // عرض بسيط أثناء التحويل
    return (
      <main className="section min-h-screen flex items-center justify-center" dir={isAr ? 'rtl' : 'ltr'}>
        <p className="text-slate-500 dark:text-slate-300 text-sm">
          {isAr ? 'جاري تحويلك إلى صفحة تسجيل الدخول...' : 'Redirecting you to the login page...'}
        </p>
      </main>
    );
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setShowSavedMessage(false);

    const newData = {
      firstName: firstName.trim(),
      lastName: lastName.trim(),
      email: email.trim(),
      phone: phone?.toString().trim() || '',
    };

    updateProfile(newData);

    setSaving(false);
    setShowSavedMessage(true);
    setIsEditing(false);
    if (savePopupTimerRef.current) clearTimeout(savePopupTimerRef.current);
    savePopupTimerRef.current = setTimeout(() => setShowSavedMessage(false), 4000);
  };

  const closeSavedPopup = () => {
    if (savePopupTimerRef.current) {
      clearTimeout(savePopupTimerRef.current);
      savePopupTimerRef.current = null;
    }
    setShowSavedMessage(false);
  };

  const handleLogout = () => {
    setShowLogoutConfirm(false);
    logout();
    addNotification({
      type: 'system',
      title: isAr ? 'تم تسجيل الخروج' : 'Logged out',
      message: isAr ? 'تم تسجيل خروجك بنجاح.' : 'You have been logged out successfully.',
      duration: 2500,
    });
    router.push(`/${locale}`);
  };

  const handleConfirmDelete = () => {
    setShowDeleteConfirm(false);
    deleteAccount();
    addNotification({
      type: 'system',
      title: isAr ? 'تم حذف الحساب' : 'Account deleted',
      message: isAr ? 'تم حذف حسابك.' : 'Your account has been deleted.',
      duration: 3000,
    });
    router.push(`/${locale}`);
  };

  return (
    <main className="section min-h-screen flex items-center justify-center" dir={isAr ? 'rtl' : 'ltr'}>
      {showSavedMessage && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="saved-popup-title"
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50"
          onClick={closeSavedPopup}
        >
          <div
            className="bg-white dark:bg-ink-900 rounded-2xl shadow-xl max-w-sm w-full p-6 text-center border border-slate-200 dark:border-slate-700"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center text-green-600 dark:text-green-400 text-2xl">
              ✓
            </div>
            <h2 id="saved-popup-title" className="text-lg font-bold text-ink-900 dark:text-white mb-2">
              {isAr ? 'تم الحفظ' : 'Saved'}
            </h2>
            <p className="text-slate-600 dark:text-slate-300 text-sm mb-6">
              {isAr ? 'تم حفظ التعديل.' : 'Your changes have been saved.'}
            </p>
            <button
              type="button"
              onClick={closeSavedPopup}
              className="w-full py-2.5 px-4 rounded-xl bg-green-600 hover:bg-green-700 text-white font-semibold text-sm transition-colors"
            >
              {isAr ? 'موافق' : 'OK'}
            </button>
          </div>
        </div>
      )}
      {showDeleteConfirm && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-confirm-title"
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50"
          onClick={() => setShowDeleteConfirm(false)}
        >
          <div
            className="bg-white dark:bg-ink-900 rounded-2xl shadow-xl max-w-sm w-full p-6 text-center border border-slate-200 dark:border-slate-700"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center text-red-600 dark:text-red-400 text-2xl">
              !
            </div>
            <h2 id="delete-confirm-title" className="text-lg font-bold text-ink-900 dark:text-white mb-2">
              {isAr ? 'حذف الحساب' : 'Delete account'}
            </h2>
            <p className="text-slate-600 dark:text-slate-300 text-sm mb-6">
              {isAr ? 'هل أنت متأكد من حذف حسابك؟' : 'Are you sure you want to delete your account?'}
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 py-2.5 px-4 rounded-xl border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 font-semibold text-sm hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                {isAr ? 'إلغاء' : 'Cancel'}
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                className="flex-1 py-2.5 px-4 rounded-xl bg-red-600 hover:bg-red-700 text-white font-semibold text-sm transition-colors"
              >
                {isAr ? 'تأكيد الحذف' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
      {showLogoutConfirm && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="logout-confirm-title"
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50"
          onClick={() => setShowLogoutConfirm(false)}
        >
          <div
            className="bg-white dark:bg-ink-900 rounded-2xl shadow-xl max-w-sm w-full p-6 text-center border border-slate-200 dark:border-slate-700"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="logout-confirm-title" className="text-lg font-bold text-ink-900 dark:text-white mb-2">
              {isAr ? 'تسجيل الخروج' : 'Log out'}
            </h2>
            <p className="text-slate-600 dark:text-slate-300 text-sm mb-6">
              {isAr ? 'هل أنت متأكد من تسجيل الخروج؟' : 'Are you sure you want to log out?'}
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setShowLogoutConfirm(false)}
                className="flex-1 py-2.5 px-4 rounded-xl border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 font-semibold text-sm hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                {isAr ? 'إلغاء' : 'Cancel'}
              </button>
              <button
                type="button"
                onClick={handleLogout}
                className="flex-1 py-2.5 px-4 rounded-xl bg-red-600 hover:bg-red-700 text-white font-semibold text-sm transition-colors"
              >
                {isAr ? 'تسجيل الخروج' : 'Log out'}
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="container max-w-2xl">
        <div className="card p-8 space-y-8">
          <header className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-extrabold text-ink-900 dark:text-white">
                {isAr ? 'حسابي' : 'My Account'}
              </h1>
              <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
                {isAr ? 'نظرة عامة على حسابك وإدارة بياناتك.' : 'Overview of your account and personal details.'}
              </p>
            </div>
          </header>

          <section>
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">
              {isAr ? 'البيانات الشخصية' : 'Personal information'}
            </h2>

            {!isEditing ? (
              <>
                <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/30 p-4 space-y-3">
                  <div>
                    <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                      {isAr ? 'الاسم الأول' : 'First name'}
                    </span>
                    <p className="text-ink-900 dark:text-white font-medium">{user.firstName || '—'}</p>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                      {isAr ? 'اسم العائلة' : 'Last name'}
                    </span>
                    <p className="text-ink-900 dark:text-white font-medium">{user.lastName || '—'}</p>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                      {isAr ? 'البريد الإلكتروني' : 'Email'}
                    </span>
                    <p className="text-ink-900 dark:text-white font-medium">{user.email || '—'}</p>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                      {isAr ? 'رقم الهاتف' : 'Phone number'}
                    </span>
                    <p className="text-ink-900 dark:text-white font-medium">{user.phone || '—'}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  className="mt-4 w-full py-3 rounded-xl border-2 border-dashed border-raboo3-400 text-raboo3-600 dark:text-raboo3-400 font-semibold text-sm hover:bg-raboo3-50 dark:hover:bg-raboo3-900/20 transition-colors"
                >
                  {isAr ? 'تعديل ملفي الشخصي' : 'Edit my profile'}
                </button>
              </>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-sm font-medium text-ink-900 dark:text-white mb-1">
                      {isAr ? 'الاسم الأول' : 'First name'}
                    </label>
                    <input
                      type="text"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      required
                      className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                      placeholder={isAr ? 'الاسم الأول' : 'First name'}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-ink-900 dark:text-white mb-1">
                      {isAr ? 'اسم العائلة' : 'Last name'}
                    </label>
                    <input
                      type="text"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      required
                      className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                      placeholder={isAr ? 'اسم العائلة' : 'Last name'}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-ink-900 dark:text-white mb-1">
                    {isAr ? 'البريد الإلكتروني' : 'Email'}
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                    placeholder="example@email.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-ink-900 dark:text-white mb-1">
                    {isAr ? 'رقم الهاتف' : 'Phone number'}
                  </label>
                  <input
                    type="tel"
                    value={phone ?? ''}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
                    placeholder={isAr ? 'أدخل رقم هاتفك (اختياري)' : 'Enter your phone number (optional)'}
                  />
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setFirstName(user.firstName ?? '');
                      setLastName(user.lastName ?? '');
                      setEmail(user.email ?? '');
                      setPhone(user.phone ?? '');
                      setIsEditing(false);
                    }}
                    className="flex-1 py-3 rounded-xl border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 font-semibold text-sm hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  >
                    {isAr ? 'إلغاء' : 'Cancel'}
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="flex-1 btn btn-primary py-3 text-base font-semibold"
                  >
                    {saving
                      ? isAr
                        ? 'جاري الحفظ...'
                        : 'Saving...'
                      : isAr
                        ? 'حفظ التغييرات'
                        : 'Save changes'}
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(true)}
                  className="mt-6 w-full py-3 rounded-xl bg-red-600 hover:bg-red-700 text-white font-semibold text-sm transition-colors"
                >
                  {isAr ? 'حذف حساب' : 'Delete account'}
                </button>
              </form>
            )}
          </section>

          <section className="pt-4 border-t border-slate-200 dark:border-slate-800">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3">
              {isAr ? 'طرق التواصل مع فريق ربوع' : 'Contact Robou team'}
            </h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <a
                href="mailto:support@robou.sa"
                className="card p-4 flex items-center gap-3 hover:border-raboo3-400 hover:bg-raboo3-50 dark:hover:bg-raboo3-900/20"
              >
                <span className="w-10 h-10 flex-shrink-0 flex items-center justify-center text-slate-700 dark:text-slate-200">
                  <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect width="20" height="16" x="2" y="4" rx="2" />
                    <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                  </svg>
                </span>
                <div>
                  <div className="text-sm font-semibold">
                    {isAr ? 'البريد الإلكتروني' : 'Email'}
                  </div>
                  <div className="text-xs text-slate-600 dark:text-slate-300">support@robou.sa</div>
                </div>
              </a>
              <a
                href="https://wa.me/966500000000"
                target="_blank"
                rel="noreferrer"
                className="card p-4 flex items-center gap-3 hover:border-raboo3-400 hover:bg-raboo3-50 dark:hover:bg-raboo3-900/20"
              >
                <span className="w-10 h-10 flex-shrink-0 flex items-center justify-center">
                  <svg className="w-7 h-7" viewBox="0 0 24 24" fill="#25D366">
                    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                  </svg>
                </span>
                <div>
                  <div className="text-sm font-semibold">
                    {isAr ? 'واتساب' : 'WhatsApp'}
                  </div>
                  <div className="text-xs text-slate-600 dark:text-slate-300">
                    {isAr ? 'تواصل مباشر مع فريق ربوع' : 'Direct chat with Robou team'}
                  </div>
                </div>
              </a>
              <a
                href="https://x.com/robou"
                target="_blank"
                rel="noreferrer"
                className="card p-4 flex items-center gap-3 hover:border-raboo3-400 hover:bg-raboo3-50 dark:hover:bg-raboo3-900/20"
              >
                <span className="w-10 h-10 flex-shrink-0 flex items-center justify-center bg-black dark:bg-white rounded-lg">
                  <svg className="w-5 h-5 text-white dark:text-black" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                  </svg>
                </span>
                <div>
                  <div className="text-sm font-semibold">
                    X
                  </div>
                  <div className="text-xs text-slate-600 dark:text-slate-300">@robou</div>
                </div>
              </a>
              <a
                href="https://instagram.com/robou"
                target="_blank"
                rel="noreferrer"
                className="card p-4 flex items-center gap-3 hover:border-raboo3-400 hover:bg-raboo3-50 dark:hover:bg-raboo3-900/20"
              >
                <span className="w-10 h-10 flex-shrink-0 flex items-center justify-center">
                  <svg className="w-7 h-7" viewBox="0 0 24 24" fill="url(#ig-gradient)">
                    <defs>
                      <linearGradient id="ig-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#FD5949" />
                        <stop offset="50%" stopColor="#D6249F" />
                        <stop offset="100%" stopColor="#285AEB" />
                      </linearGradient>
                    </defs>
                    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.766 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z" />
                  </svg>
                </span>
                <div>
                  <div className="text-sm font-semibold">
                    {isAr ? 'إنستقرام' : 'Instagram'}
                  </div>
                  <div className="text-xs text-slate-600 dark:text-slate-300">@robou</div>
                </div>
              </a>
            </div>
          </section>

          <section className="pt-4 border-t border-slate-200 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setShowLogoutConfirm(true)}
              className="w-full py-3 rounded-xl bg-red-600 text-white font-semibold text-sm shadow-sm hover:bg-red-700 transition-colors"
            >
              {isAr ? 'تسجيل الخروج' : 'Log out'}
            </button>
          </section>
        </div>
      </div>
    </main>
  );
}

