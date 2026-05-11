"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { budgetApi, personalityApi } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import type { Budget, Personality } from "@/types";
import Navbar from "./components/Navbar";
import BudgetCards from "./components/BudgetCards";
import SavingsTips from "./components/SavingsTips";
import QuickActions from "./components/QuickActions";

export default function DashboardPage() {
  const { userId, loading } = useAuth();
  const [budget, setBudget] = useState<Budget | null>(null);
  const [personality, setPersonality] = useState<Personality | null>(null);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (!userId) return;
    Promise.all([
      budgetApi.getAnalysis(userId).catch(() => null),
      personalityApi.getProfile(userId).catch(() => null),
    ]).then(([b, p]) => {
      setBudget(b as Budget | null);
      setPersonality(p as Personality | null);
      setFetching(false);
    });
  }, [userId]);

  if (loading || fetching) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {budget ? (
          <>
            <BudgetCards budget={budget} />
            <SavingsTips tips={budget.savings_tips ?? []} personality={personality} />
          </>
        ) : (
          <div className="card text-center py-10">
            <p className="text-gray-500 mb-4">Henüz bütçe bilgisi girilmemiş.</p>
            <Link href="/onboarding/budget" className="btn-primary">Bütçe Oluştur</Link>
          </div>
        )}

        <QuickActions />
      </div>
    </div>
  );
}
