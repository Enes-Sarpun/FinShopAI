"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { budgetApi, authApi } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { formatPrice, getBudgetStatusColor, getSpendingTypeLabel } from "@/lib/utils";
import type { Budget, Personality } from "@/types";

export default function DashboardPage() {
  const router = useRouter();
  const { userId, loading } = useAuth();
  const [budget, setBudget] = useState<Budget | null>(null);
  const [personality, setPersonality] = useState<Personality | null>(null);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (!userId) return;
    Promise.all([
      budgetApi.getAnalysis(userId).catch(() => null),
      authApi.me().catch(() => null),
    ]).then(([b, _]) => {
      setBudget(b as Budget | null);
      setFetching(false);
    });
  }, [userId]);

  if (loading || fetching) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  const metrics = budget?.financial_metrics;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <nav className="bg-white border-b border-gray-100 px-6 py-4 flex justify-between items-center">
        <h1 className="font-bold text-gray-900 text-lg">FinShop AI</h1>
        <div className="flex items-center gap-4">
          <Link href="/chat" className="btn-primary text-sm py-2 px-4">Alışverişe Başla</Link>
          <button onClick={authApi.logout} className="text-sm text-gray-500 hover:text-gray-700">Çıkış</button>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {/* Bütçe Durumu */}
        {metrics ? (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: "Aylık Gelir", value: formatPrice(metrics.total_income), color: "text-green-600" },
                { label: "Sabit Giderler", value: formatPrice(metrics.fixed_expenses), color: "text-red-500" },
                { label: "Harcanabilir", value: formatPrice(metrics.spendable_after_savings), color: "text-blue-600" },
                { label: "Tasarruf Hedefi", value: formatPrice(metrics.savings_goal), color: "text-purple-600" },
              ].map((item) => (
                <div key={item.label} className="card text-center">
                  <p className="text-xs text-gray-500 mb-1">{item.label}</p>
                  <p className={`text-xl font-bold ${item.color}`}>{item.value}</p>
                </div>
              ))}
            </div>

            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-gray-800">Bütçe Sağlığı</h2>
                <span className={`font-bold capitalize ${getBudgetStatusColor(budget?.status || "")}`}>
                  {budget?.status === "healthy" ? "Sağlıklı" : budget?.status === "warning" ? "Dikkat" : "Kritik"}
                </span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-3">
                <div
                  className="bg-blue-600 h-3 rounded-full"
                  style={{ width: `${Math.min(metrics.expense_ratio, 100)}%` }}
                />
              </div>
              <p className="text-sm text-gray-500 mt-2">Gider oranı: %{metrics.expense_ratio}</p>
            </div>

            {budget?.savings_tips && budget.savings_tips.length > 0 && (
              <div className="card">
                <h2 className="font-semibold text-gray-800 mb-3">Tasarruf Önerileri</h2>
                <ul className="space-y-2">
                  {budget.savings_tips.map((tip, i) => (
                    <li key={i} className="text-sm text-gray-600">{tip}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        ) : (
          <div className="card text-center py-10">
            <p className="text-gray-500 mb-4">Henüz bütçe bilgisi girilmemiş.</p>
            <Link href="/onboarding/budget" className="btn-primary">Bütçe Oluştur</Link>
          </div>
        )}

        {/* Hızlı Erişim */}
        <div className="card">
          <h2 className="font-semibold text-gray-800 mb-4">Hızlı Erişim</h2>
          <div className="grid grid-cols-2 gap-3">
            <Link href="/chat" className="btn-secondary text-center text-sm">Alışveriş Asistanı</Link>
            <Link href="/chat/history" className="btn-secondary text-center text-sm">Geçmiş Aramalar</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
