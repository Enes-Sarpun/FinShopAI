"use client";
import { useState, useEffect } from "react";
import { Sparkles, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const TIPS = [
  "Alışveriş öncesi fiyat karşılaştırması yaparak ortalama %15 tasarruf edebilirsin.",
  "Aylık aboneliklerini gözden geçir — kullanmadığın hizmetleri iptal etmek bütçeni rahatlatır.",
  "Market alışverişine listeyle gitmek dürtüsel harcamaları önler.",
  "İndirim sezonlarında ihtiyaç listeni hazır tut, fırsatları kaçırma.",
  "Büyük alımlardan önce 24 saat bekle — gerçekten ihtiyacın var mı?",
  "Küçük tutarları küçümseme: günlük 20 TL kahve, yılda 7.300 TL eder.",
  "Tasarruf hedefini görsel olarak takip etmek motivasyonunu artırır.",
];

const SESSION_KEY = "finshop_daily_tip_dismissed";

export default function DailyTip() {
  const [visible, setVisible] = useState(false);
  const [tip, setTip] = useState("");

  useEffect(() => {
    const dismissed = sessionStorage.getItem(SESSION_KEY);
    if (dismissed) return;

    const dayIndex = new Date().getDay();
    setTip(TIPS[dayIndex % TIPS.length]);
    setVisible(true);
  }, []);

  function dismiss() {
    sessionStorage.setItem(SESSION_KEY, "1");
    setVisible(false);
  }

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: -8, height: 0 }}
          animate={{ opacity: 1, y: 0, height: "auto" }}
          exit={{ opacity: 0, y: -8, height: 0 }}
          transition={{ duration: 0.35, ease: [0.25, 0.1, 0.25, 1] }}
          className="overflow-hidden"
        >
          <div className="flex items-start gap-3 bg-gradient-to-r from-indigo-50 to-blue-50 dark:from-indigo-900/20 dark:to-blue-900/20 border border-indigo-100 dark:border-indigo-800/40 rounded-2xl px-4 py-3 mb-6">
            <div className="w-8 h-8 bg-indigo-100 dark:bg-indigo-900/40 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5">
              <Sparkles className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div className="flex-1">
              <p className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 mb-0.5">Günün İpucu</p>
              <p className="text-sm text-gray-700 dark:text-gray-300">{tip}</p>
            </div>
            <button
              onClick={dismiss}
              className="p-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-white/60 dark:hover:bg-gray-700/40 transition-colors flex-shrink-0"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
