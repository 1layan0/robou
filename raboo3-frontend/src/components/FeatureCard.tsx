'use client'

import { motion, useReducedMotion } from 'framer-motion'
import { ReactNode } from 'react'

interface FeatureCardProps {
  icon: ReactNode
  title: string
  description: string
}

export default function FeatureCard({ icon, title, description }: FeatureCardProps) {
  const prefersReducedMotion = useReducedMotion()
  return (
    <motion.div
      className="group relative h-full overflow-hidden rounded-2xl border border-slate-200/60 bg-gradient-to-br from-white to-slate-50/50 p-6 shadow-lg shadow-slate-900/5 transition-all duration-300 dark:border-slate-800/60 dark:from-ink-900/80 dark:to-ink-900/40 dark:shadow-slate-900/20"
      whileHover={prefersReducedMotion ? undefined : { y: -8, scale: 1.02 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-raboo3-500/5 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
      <div className="relative z-10">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-raboo3-100 to-raboo3-50 text-2xl shadow-md transition-transform duration-300 group-hover:scale-110 dark:from-raboo3-900/40 dark:to-raboo3-900/20">
          {icon}
        </div>
        <h3 className="mb-2 text-xl font-bold text-ink-900 dark:text-white">{title}</h3>
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{description}</p>
      </div>
    </motion.div>
  )
}
