"use client";
import { Lightbulb, CheckCircle2, RefreshCw, ArrowRight, Star } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";
import type { Personality } from "@/types";

interface SavingsTipsProps {
  tips: string[];
  personality?: Personality | null;
}

const SPENDING_TYPE_CONFIG = {
  dengeli: {
    label: "Dengeli Harcayıcı",
    badge: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800",
    accent: "border-l-blue-400",
    tipColor: "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400",
    numberBg: "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300",
  },
  tutumlu: {
    label: "Tutumlu Harcayıcı",
    badge: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800",
    accent: "border-l-emerald-400",
    tipColor: "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400",
    numberBg: "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300",
  },
  savruk: {
    label: "Savruk Harcayıcı",
    badge: "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-800",
    accent: "border-l-orange-400",
    tipColor: "bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400",
    numberBg: "bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-300",
  },
};

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, delay, ease: [0.25, 0.1, 0.25, 1] as const },
});

export default function SavingsTips({ tips, personality }: SavingsTipsProps) {
  const config =
    SPENDING_TYPE_CONFIG[personality?.spending_type as keyof typeof SPENDING_TYPE_CONFIG] ??
    SPENDING_TYPE_CONFIG.dengeli;

  return (
    <div className="space-y-4">
      {/* Kişilik Profili */}
      {personality && (
        <motion.div {...fadeUp(0)} className={`card border-l-4 ${config.accent}`}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-800 dark:text-gray-100">Finansal Profil</h2>
            <div className="flex items-center gap-2">
              <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${config.badge}`}>
                {config.label}
              </span>
              <Link
                href="/onboarding/personality"
                className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                title="Kişilik Testini Yenile"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
          {personality.strengths?.length > 0 && (
            <ul className="space-y-1.5">
              {personality.strengths.map((s, i) => (
                <motion.li
                  key={i}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 + i * 0.06, duration: 0.3 }}
                  className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-300"
                >
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                  {s}
                </motion.li>
              ))}
            </ul>
          )}
        </motion.div>
      )}

      {/* Tasarruf Önerileri — individual cards */}
      {tips.length > 0 && (
        <motion.div {...fadeUp(0.1)} className="card">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-amber-50 dark:bg-amber-900/20 rounded-lg flex items-center justify-center">
              <Lightbulb className="w-4 h-4 text-amber-500" />
            </div>
            <h2 className="font-semibold text-gray-800 dark:text-gray-100">Tasarruf Önerileri</h2>
            <span className="ml-auto text-xs text-gray-400 dark:text-gray-500">{tips.length} öneri</span>
          </div>
          <div className="space-y-2">
            {tips.map((tip, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 + i * 0.07, duration: 0.3 }}
                className="flex items-start gap-3 rounded-xl border border-gray-100 dark:border-gray-700/60 bg-white/60 dark:bg-gray-800/40 px-3.5 py-3 group hover:border-gray-200 dark:hover:border-gray-600 hover:bg-white dark:hover:bg-gray-800/70 transition-all duration-200"
              >
                <span className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5 ${config.numberBg}`}>
                  {i + 1}
                </span>
                <p className="text-sm text-gray-600 dark:text-gray-300 flex-1 leading-snug">{tip}</p>
                {i === 0 && (
                  <Star className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
                )}
              </motion.div>
            ))}
          </div>

          <Link
            href="/chat"
            className="mt-4 flex items-center justify-center gap-1.5 w-full text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium py-2.5 rounded-xl border border-blue-100 dark:border-blue-900/40 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all duration-200"
          >
            Ürün Önerisi Al
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </motion.div>
      )}
    </div>
  );
}
