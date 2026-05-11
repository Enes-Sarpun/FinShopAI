"use client";
import { formatPrice, getBudgetStatusColor } from "@/lib/utils";
import type { Budget } from "@/types";

// GÖREV: ARKADAŞ 1
// Bu component bütçe özet kartlarını ve sağlık göstergesini içeriyor.
// Yapılabilecekler:
//   - Kartlara ikon ekle (lucide-react'tan)
//   - Progress bar'a animasyon ekle
//   - Gider oranı için renk kodlaması (yeşil/sarı/kırmızı)
//   - Kartları tıklanabilir yap, detay sayfasına yönlendir
//   - Tooltip ekle (her metriğin ne anlama geldiği)

interface BudgetCardsProps {
  budget: Budget;
}

export default function BudgetCards({ budget }: BudgetCardsProps) {
  const metrics = budget.financial_metrics;

  const cards = [
    { label: "Aylık Gelir", value: formatPrice(metrics.total_income), color: "text-green-600" },
    { label: "Sabit Giderler", value: formatPrice(metrics.fixed_expenses), color: "text-red-500" },
    { label: "Harcanabilir", value: formatPrice(metrics.spendable_after_savings), color: "text-blue-600" },
    { label: "Tasarruf Hedefi", value: formatPrice(metrics.savings_goal), color: "text-purple-600" },
  ];

  return (
    <div className="space-y-4">
      {/* Özet Kartlar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {cards.map((item) => (
          <div key={item.label} className="card text-center">
            <p className="text-xs text-gray-500 mb-1">{item.label}</p>
            <p className={`text-xl font-bold ${item.color}`}>{item.value}</p>
          </div>
        ))}
      </div>

      {/* Bütçe Sağlığı */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-800">Bütçe Sağlığı</h2>
          <span className={`font-bold ${getBudgetStatusColor(budget.status)}`}>
            {budget.status === "healthy" ? "Sağlıklı" : budget.status === "warning" ? "Dikkat" : "Kritik"}
          </span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-3">
          <div
            className="bg-blue-600 h-3 rounded-full transition-all duration-500"
            style={{ width: `${Math.min(metrics.expense_ratio, 100)}%` }}
          />
        </div>
        <p className="text-sm text-gray-500 mt-2">Gider oranı: %{metrics.expense_ratio}</p>
      </div>
    </div>
  );
}
