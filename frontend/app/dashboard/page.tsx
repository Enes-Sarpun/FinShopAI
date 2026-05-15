"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { budgetApi, personalityApi, authApi } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import type { Budget, Personality } from "@/types";
import Sidebar from "./components/Sidebar";
import BudgetCards from "./components/BudgetCards";
import SavingsTips from "./components/SavingsTips";
import QuickActions from "./components/QuickActions";
import DailyTip from "./components/DailyTip";
import ChatPreview from "./components/ChatPreview";

interface UserInfo { full_name?: string; email?: string; }

function SkeletonCard() {
  return (
    <div className="card">
      <div className="skeleton h-10 w-10 rounded-xl mb-3" />
      <div className="skeleton h-3 w-20 mb-2 rounded-md" />
      <div className="skeleton h-6 w-28 rounded-md" />
    </div>
  );
}

function SkeletonSection() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => <SkeletonCard key={i} />)}
      </div>
      <div className="card">
        <div className="skeleton h-4 w-32 mb-4 rounded-md" />
        <div className="skeleton h-3 w-full rounded-full" />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { userId, loading } = useAuth();
  const [budget, setBudget] = useState<Budget | null>(null);
  const [personality, setPersonality] = useState<Personality | null>(null);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [fetching, setFetching] = useState(true);

  // Sayfa geçişinde scroll pozisyonunu sıfırla
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  }, []);

  useEffect(() => {
    if (!userId) return;
    Promise.all([
      budgetApi.getAnalysis(userId).catch(() => null),
      personalityApi.getProfile(userId).catch(() => null),
      authApi.me().catch(() => null),
    ]).then(([b, p, u]) => {
      setBudget(b as Budget | null);
      setPersonality(p as Personality | null);
      setUser(u as UserInfo | null);
      setFetching(false);
    });
  }, [userId]);

  const firstName = user?.full_name?.split(" ")[0] ?? "";

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg-mesh)" }}>
      <Sidebar userName={user?.full_name} userEmail={user?.email} />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-6 py-8">

          {/* Karşılama başlığı */}
          <motion.div
            className="mb-6"
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
              Hoş geldin{firstName ? `, ${firstName}` : ""}
              <span className="inline-block animate-wave origin-[70%_70%]">👋</span>
            </h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1 text-sm">
              Finansal durumuna göz at, alışveriş için asistanı başlat.
            </p>
          </motion.div>

          {/* Günlük ipucu banner */}
          <DailyTip />

          {loading || fetching ? (
            <div className="space-y-6">
              <SkeletonSection />
              <div className="card">
                <div className="skeleton h-4 w-28 mb-4 rounded-md" />
                <div className="grid grid-cols-2 gap-3">
                  {[0, 1, 2, 3].map((i) => (
                    <div key={i} className="skeleton h-16 rounded-xl" />
                  ))}
                </div>
              </div>
            </div>
          ) : budget ? (
            <div className="space-y-6">
              {/* Bütçe kartları */}
              <BudgetCards budget={budget} />

              {/* Ana içerik grid — 3 sütun */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Sol kolon: profil + tasarruf ipuçları + yıldızlı ürünler */}
                <div className="lg:col-span-1 space-y-4">
                  <SavingsTips tips={budget.savings_tips ?? []} personality={personality} />
                </div>

                {/* Orta + sağ kolon: chat + hızlı erişim */}
                <div className="lg:col-span-2 space-y-4">
                  <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15, duration: 0.4 }}
                  >
                    <ChatPreview />
                  </motion.div>
                  <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.25, duration: 0.4 }}
                  >
                    <QuickActions />
                  </motion.div>
                </div>
              </div>
            </div>
          ) : (
            <motion.div
              className="card text-center py-16"
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4 }}
            >
              <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-900/30 dark:to-indigo-900/30 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">💰</span>
              </div>
              <p className="text-gray-700 dark:text-gray-200 font-semibold mb-1 text-lg">Bütçen henüz oluşturulmamış</p>
              <p className="text-gray-400 dark:text-gray-500 text-sm mb-6">Kişiselleştirilmiş öneriler için bütçeni gir.</p>
              <Link href="/onboarding/budget" className="btn-primary inline-block">Bütçe Oluştur</Link>
            </motion.div>
          )}
        </div>
      </main>
    </div>
  );
}
