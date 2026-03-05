'use client';

import { motion } from 'framer-motion';
import clsx from 'classnames';
import { CITIES, City } from '@/lib/cities';

interface CityChipsProps {
  value?: City;
  onChange?: (city: City) => void;
}

export default function CityChips({ value, onChange }: CityChipsProps) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-3">
      {CITIES.map((city) => {
        const active = value === city;
        return (
          <motion.button
            key={city}
            type="button"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.97 }}
            className={clsx(
              'rounded-full border px-4 py-2 text-sm font-semibold transition-colors',
              active
                ? 'border-raboo3-500 bg-raboo3-50 text-raboo3-700 shadow-soft dark:border-raboo3-400 dark:bg-raboo3-500/10 dark:text-raboo3-300'
                : 'border-black/10 bg-white text-slate-600 hover:border-raboo3-400 dark:border-white/10 dark:bg-ink-900/60 dark:text-slate-300'
            )}
            onClick={() => onChange?.(city)}
            aria-pressed={active}
          >
            {city}
          </motion.button>
        );
      })}
    </div>
  );
}
