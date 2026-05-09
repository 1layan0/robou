'use client';

import { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/lib/supabase/client';
import { useAuth } from '@/contexts/AuthContext';
import { useNotifications } from '@/contexts/NotificationContext';
import { useI18n, useT } from '@/i18n/useTranslations';

type FavoriteStarButtonProps = {
  city_ar: string;
  district_ar: string;
  district_id: number | null | undefined;
  property_type_ar: string;
  predictedPricePerSqm?: number | null;
};

export default function FavoriteStarButton({
  city_ar,
  district_ar,
  district_id,
  property_type_ar,
  predictedPricePerSqm,
}: FavoriteStarButtonProps) {
  const { user } = useAuth();
  const { addNotification } = useNotifications();
  const { locale } = useI18n();
  const t = useT();
  const isRtl = locale === 'ar';
  const [isFav, setIsFav] = useState(false);
  const [loading, setLoading] = useState(false);

  const districtIdNum = typeof district_id === 'number' && !Number.isNaN(district_id) ? district_id : null;
  const propertyType = (property_type_ar ?? '').trim();
  const canUseSupabaseFavorite = districtIdNum != null;

  const fetchFavState = useCallback(async () => {
    if (!supabase || !user?.id || !canUseSupabaseFavorite || districtIdNum == null) {
      setIsFav(false);
      return;
    }
    const { data: favoriteRow } = await supabase
      .from('favorites')
      .select('id')
      .eq('user_id', user.id)
      .eq('district_id', districtIdNum)
      .eq('property_type_ar', propertyType)
      .maybeSingle();
    setIsFav(!!favoriteRow);
  }, [user?.id, districtIdNum, propertyType, canUseSupabaseFavorite]);

  useEffect(() => {
    fetchFavState();
  }, [fetchFavState]);

  const handleClick = async () => {
    const needDistrictIdMsg = isRtl ? 'تعذّر الحفظ: معرّف الحي غير متوفر' : 'Could not save: district ID is unavailable';
    const loginRequiredMsg = t.predict.report.login_to_save_favorite;
    const failSave = isRtl ? 'فشل الحفظ' : 'Save failed';
    const failRemove = isRtl ? 'فشل الإزالة' : 'Remove failed';
    const removeFallback = isRtl ? 'تعذرت إزالة المفضلة' : 'Could not remove favorite';
    const saveFallback = isRtl ? 'تعذر حفظ المفضلة' : 'Could not save favorite';

    if (!canUseSupabaseFavorite || districtIdNum == null) {
      addNotification({
        type: 'warning',
        title: needDistrictIdMsg,
        message: needDistrictIdMsg,
        duration: 4000,
      });
      return;
    }
    if (!supabase || !user?.id) {
      addNotification({ type: 'system', title: loginRequiredMsg, message: loginRequiredMsg, duration: 3000 });
      return;
    }
    if (loading) return;

    const previous = isFav;
    setIsFav(!isFav);
    setLoading(true);

    const userId = user.id;

    if (previous) {
      const { error } = await supabase
        .from('favorites')
        .delete()
        .eq('user_id', userId)
        .eq('district_id', districtIdNum)
        .eq('property_type_ar', propertyType);
      if (error) {
        setIsFav(previous);
        if (process.env.NODE_ENV !== 'production') console.error('FavoriteStarButton delete:', error);
        addNotification({ type: 'error', title: failRemove, message: error.message ?? removeFallback, duration: 3000 });
      }
    } else {
      const payload = {
        user_id: userId,
        district_id: districtIdNum,
        property_type_ar: propertyType,
        predicted_price_per_sqm: predictedPricePerSqm ?? null,
        city_ar: (city_ar ?? '').trim() || null,
        district_ar: (district_ar ?? '').trim() || null,
      };
      const { data: upsertData, error } = await supabase.from('favorites').upsert(payload, {
        onConflict: 'user_id,district_id,property_type_ar',
        ignoreDuplicates: false,
      });
      if (error) {
        setIsFav(previous);
        if (typeof console !== 'undefined' && console.error) {
          console.error('FavoriteStarButton upsert error:', error);
          console.error('FavoriteStarButton upsert payload:', payload);
        }
        addNotification({ type: 'error', title: failSave, message: error.message ?? saveFallback, duration: 3000 });
      } else if (process.env.NODE_ENV !== 'production' && typeof console !== 'undefined' && console.log) {
        console.log('FavoriteStarButton upsert ok:', upsertData);
      }
    }
    setLoading(false);
  };

  const tooltipText =
    !canUseSupabaseFavorite
      ? (isRtl ? 'المفضلة غير متاحة لهذا الحي' : 'Favorite not available for this district')
      : isFav
        ? t.predict.report.remove_favorite
        : t.predict.report.add_favorite;

  return (
    <div className="relative group">
      <button
        type="button"
        onClick={handleClick}
        disabled={loading || !canUseSupabaseFavorite}
        aria-label={tooltipText}
        className="p-0 bg-transparent border-0 shadow-none cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none"
      >
        {isFav ? (
          <svg className="h-5 w-5 text-amber-400 fill-amber-400" viewBox="0 0 24 24" aria-hidden>
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
          </svg>
        ) : (
          <svg className="h-5 w-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
          </svg>
        )}
      </button>
      <span
        className={`pointer-events-none absolute -top-8 rounded px-2 py-1 bg-black/80 text-xs text-white opacity-0 transition group-hover:opacity-100 whitespace-nowrap ${isRtl ? 'left-0' : 'right-0'}`}
        role="tooltip"
      >
        {tooltipText}
      </span>
    </div>
  );
}
