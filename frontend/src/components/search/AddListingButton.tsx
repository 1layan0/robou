'use client';

import Link from 'next/link';
import { useI18n } from '@/i18n/useTranslations';
import { motion } from 'framer-motion';

export default function AddListingButton() {
  const { locale } = useI18n();
  const isAr = locale === 'ar';

  return (
    <Link href={`/${locale}/app/land/add`}>
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-raboo3-600 text-white font-semibold shadow-lg shadow-raboo3-500/25 hover:shadow-xl hover:shadow-raboo3-500/30 transition-all duration-300"
      >
        <span className="text-xl">+</span>
        <span>{isAr ? 'أضف أرض للبيع' : 'Add Land for Sale'}</span>
      </motion.button>
    </Link>
  );
}

