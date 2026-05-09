'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { useI18n, useT } from '@/i18n/useTranslations';
import { useNotifications } from '@/contexts/NotificationContext';
import { getFavorites, removeFavorite, type FavoriteItem } from '@/lib/favorites';
import { translateCity, translateDistrict } from '@/lib/translateLocations';
import { supabase } from '@/lib/supabase/client';
import SARIcon from '@/components/SARIcon';

function districtEmbedAsObject(
  row: unknown,
): { city_ar?: string | null; district_ar?: string | null } | null {
  if (row == null) return null;
  if (Array.isArray(row)) {
    const first = row[0];
    if (first && typeof first === 'object') {
      return first as { city_ar?: string | null; district_ar?: string | null };
    }
    return null;
  }
  if (typeof row === 'object') return row as { city_ar?: string | null; district_ar?: string | null };
  return null;
}

export type SupabaseFavoriteRow = {
  id: string;
  district_id: number;
  property_type_ar: string;
  predicted_price_per_sqm: number | null;
  created_at: string;
  city_ar?: string | null;
  district_ar?: string | null;
  district?: { city_ar: string; district_ar: string } | { city_ar: string; district_ar: string }[] | null;
};

export default function AccountPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const router = useRouter();
  const { user, updateProfile, refreshProfile, logout, deleteAccount } = useAuth();
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
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [supabaseFavorites, setSupabaseFavorites] = useState<SupabaseFavoriteRow[]>([]);
  const [useSupabaseFavorites, setUseSupabaseFavorites] = useState(false);
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
    setFavorites(getFavorites());
  }, []);

  // جلب المفضلة مرة عند ظهور المستخدم — نعتمد على user.id فقط لتفادي حلقة (لا نستدعي getUser هنا)
  useEffect(() => {
    if (!supabase || !user?.id) {
      setUseSupabaseFavorites(false);
      return;
    }
    let cancelled = false;
    (async () => {
      const { data: rows, error } = await supabase
        .from('favorites')
        .select(
          'id, district_id, property_type_ar, predicted_price_per_sqm, created_at, city_ar, district_ar, district(city_ar, district_ar)',
        )
        .eq('user_id', user.id)
        .order('created_at', { ascending: false });
      if (cancelled) return;
      if (!error && rows?.length !== undefined) {
        setSupabaseFavorites(rows as unknown as SupabaseFavoriteRow[]);
        setUseSupabaseFavorites(true);
      } else {
        setUseSupabaseFavorites(false);
      }
    })();
    return () => { cancelled = true; };
  }, [user?.id]);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supabase) {
      addNotification({
        type: 'error',
        title: isAr ? 'خطأ' : 'Error',
        message: isAr ? 'اتصال Supabase غير متوفر.' : 'Supabase connection not available.',
        duration: 4000,
      });
      return;
    }

    const { data: { user: authUser } } = await supabase.auth.getUser();
    if (!authUser) {
      addNotification({
        type: 'error',
        title: isAr ? 'تسجيل الدخول مطلوب' : 'Login required',
        message: isAr ? 'سجّلي الدخول أولاً.' : 'Please sign in first.',
        duration: 4000,
      });
      return;
    }

    setSaving(true);
    setShowSavedMessage(false);

    const newFirstName = firstName.trim();
    const newLastName = lastName.trim();
    const newEmail = email.trim();
    const newPhone = phone?.toString().trim() || null;

    try {
      const now = new Date().toISOString();
      const emailChanged = newEmail !== (authUser.email ?? '');

      // --- Email change: server route with service_role (auth.admin.updateUserById + email_confirm: true). No client updateUser for email. ---
      if (emailChanged) {
        const { data: { session } } = await supabase.auth.getSession();
        const accessToken = session?.access_token;
        if (!accessToken) throw new Error(isAr ? 'انتهت الجلسة. سجّلي الدخول مرة أخرى.' : 'Session expired. Please sign in again.');
        const res = await fetch('/api/account/update-email', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
          body: JSON.stringify({ newEmail }),
        });
        const json = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(json?.error ?? (isAr ? 'فشل تحديث الإيميل.' : 'Failed to update email.'));
      }

      // Update Auth user_metadata only (name, phone). Email already handled above when changed.
      const { error: authError } = await supabase.auth.updateUser({
        data: {
          first_name: newFirstName,
          last_name: newLastName,
          ...(newPhone != null && newPhone !== '' && { phone: newPhone }),
        },
      });
      if (authError) throw authError;

      // Sync public.users (profile mirror). Server route already synced email when email changed.
      const { error: upsertError } = await supabase.from('users').upsert(
        {
          id: authUser.id,
          email: newEmail,
          first_name: newFirstName,
          last_name: newLastName,
          phone: newPhone || null,
          updated_at: now,
          created_at: now,
        },
        { onConflict: 'id' }
      );
      if (upsertError) throw upsertError;

      updateProfile({
        firstName: newFirstName,
        lastName: newLastName,
        email: newEmail,
        phone: newPhone || undefined,
      });
      setShowSavedMessage(true);
      setIsEditing(false);
      if (savePopupTimerRef.current) clearTimeout(savePopupTimerRef.current);
      savePopupTimerRef.current = setTimeout(() => setShowSavedMessage(false), 4000);

      if (emailChanged) {
        addNotification({
          type: 'system',
          title: isAr ? 'تم الحفظ' : 'Saved',
          message: isAr ? 'تم تحديث إيميل تسجيل الدخول. يمكنك استخدام الإيميل الجديد في المرة القادمة.' : 'Login email updated. You can use the new email next time you sign in.',
          duration: 5000,
        });
      }
    } catch (err: unknown) {
      const errObj = err && typeof err === 'object' ? (err as { message?: string; code?: string }) : {};
      const message = typeof errObj.message === 'string' ? errObj.message : (isAr ? 'فشل الحفظ.' : 'Save failed.');
      addNotification({
        type: 'error',
        title: isAr ? 'فشل الحفظ' : 'Save failed',
        message,
        duration: 5000,
      });
    } finally {
      setSaving(false);
    }
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

  const handleRemoveFavorite = (city_ar: string, district_ar: string) => {
    removeFavorite(city_ar, district_ar);
    setFavorites(getFavorites());
    addNotification({
      type: 'system',
      title: isAr ? 'تمت الإزالة' : 'Removed',
      message: isAr ? 'تم إزالة الحي من المفضلة.' : 'District removed from favorites.',
      duration: 2000,
    });
  };

  const handleRemoveSupabaseFavorite = async (id: string) => {
    if (!supabase) return;
    const { error } = await supabase.from('favorites').delete().eq('id', id);
    if (error) {
      if (typeof console !== 'undefined' && console.error) console.error('Account remove favorite:', error);
      addNotification({ type: 'error', title: isAr ? 'فشل الإزالة' : 'Remove failed', message: error.message ?? '', duration: 3000 });
      return;
    }
    setSupabaseFavorites((prev) => prev.filter((f) => f.id !== id));
    addNotification({
      type: 'system',
      title: isAr ? 'تمت الإزالة' : 'Removed',
      message: isAr ? 'تم إزالة الحي من المفضلة.' : 'District removed from favorites.',
      duration: 2000,
    });
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

          {/* قسم المفضلة في صفحة الحساب */}
          <section className="pt-4 border-t border-slate-200 dark:border-slate-800">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3">
              {t.account.favorites_title}
            </h2>
            {useSupabaseFavorites ? (
              supabaseFavorites.length === 0 ? (
                <p className="text-slate-600 dark:text-slate-400 text-sm py-2">
                  {t.account.favorites_empty}
                </p>
              ) : (
                <ul className="space-y-2">
                  {supabaseFavorites.map((fav) => {
                    const embed = districtEmbedAsObject(fav.district);
                    const cityAr = ((fav.city_ar ?? embed?.city_ar) ?? '').trim();
                    const districtAr = ((fav.district_ar ?? embed?.district_ar) ?? '').trim();
                    const cityLabel = cityAr ? translateCity(cityAr, locale) : '';
                    const districtLabel = districtAr ? translateDistrict(districtAr, locale) : '';
                    const titleLine =
                      districtLabel ||
                      districtAr ||
                      (isAr ? `حي #${fav.district_id}` : `District #${fav.district_id}`);
                    const subtitleLine = cityLabel || cityAr || (fav.property_type_ar ? fav.property_type_ar : '');
                    const priceStr =
                      fav.predicted_price_per_sqm != null
                        ? fav.predicted_price_per_sqm.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US')
                        : null;
                    return (
                      <li
                        key={fav.id}
                        className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/30 px-4 py-3"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-ink-900 dark:text-white">{titleLine}</p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">{subtitleLine}</p>
                          {priceStr != null && (
                            <p className="text-xs text-raboo3-600 dark:text-raboo3-400 mt-1">
                              {isAr ? 'سعر المتر وقت الحفظ: ' : 'Price/m² when saved: '}
                              {priceStr} <SARIcon />/{isAr ? 'م²' : 'm²'}
                            </p>
                          )}
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveSupabaseFavorite(fav.id)}
                          className="p-1.5 text-slate-500 hover:text-red-600 dark:text-slate-400 dark:hover:text-red-400 shrink-0"
                          aria-label={t.account.remove_favorite}
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )
            ) : favorites.length === 0 ? (
              <p className="text-slate-600 dark:text-slate-400 text-sm py-2">
                {t.account.favorites_empty}
              </p>
            ) : (
              <ul className="space-y-2">
                {favorites.map((fav) => {
                  const cityLabel = translateCity(fav.city_ar, locale);
                  const districtLabel = translateDistrict(fav.district_ar, locale);
                  return (
                    <li
                      key={`${fav.city_ar}-${fav.district_ar}`}
                      className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/30 px-4 py-3"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-ink-900 dark:text-white">{districtLabel || cityLabel}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">{cityLabel}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveFavorite(fav.city_ar, fav.district_ar)}
                        className="p-1.5 text-slate-500 hover:text-red-600 dark:text-slate-400 dark:hover:text-red-400 shrink-0"
                        aria-label={t.account.remove_favorite}
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          {/* قسم طرق التواصل مع فريق ربوع تمت إزالته من الواجهة بناءً على طلب التصميم */}

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

