"use client";

import React, { useEffect, useState } from "react";
import { 
  TrendingUp, 
  TrendingDown, 
  Wallet, 
  Target, 
  Activity, 
  Info 
} from "lucide-react";
import { formatPrice, getBudgetStatusColor,cn } from "@/lib/utils";
import type { Budget } from "@/types";

interface BudgetCardsProps {
  budget: Budget;
}

export default function BudgetCards({ budget }: BudgetCardsProps) {
  const metrics = budget.financial_metrics;
  const [animatedWidth, setAnimatedWidth] = useState(0);

  // Progress bar animasyonu için useEffect [GÖREV: ARKADAŞ 1]
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedWidth(Math.min(metrics.expense_ratio, 100));
    }, 100);
    return () => clearTimeout(timer);
  }, [metrics.expense_ratio]);

  // Gider oranına göre dinamik renk belirleme [GÖREV: ARKADAŞ 1]
  const getProgressColor = (ratio: number) => {
    if (ratio < 50) return "bg-green-500";
    if (ratio < 80) return "bg-yellow-500";
    return "bg-red-500";
  };

  const cards = [
    { 
      label: "Aylık Gelir", 
      value: formatPrice(metrics.total_income), 
      color: "text-green-600", 
      bgColor: "bg-green-50",
      icon: <TrendingUp className="w-5 h-5 text-green-600" />,
      description: "Tüm kaynaklardan gelen toplam kazancın."
    },
    { 
      label: "Sabit Giderler", 
      value: formatPrice(metrics.fixed_expenses), 
      color: "text-red-500", 
      bgColor: "bg-red-50",
      icon: <TrendingDown className="w-5 h-5 text-red-500" />,
      description: "Kira, fatura gibi değişmeyen aylık ödemelerin."
    },
    { 
      label: "Harcanabilir", 
      value: formatPrice(metrics.spendable_after_savings), 
      color: "text-blue-600", 
      bgColor: "bg-blue-50",
      icon: <Wallet className="w-5 h-5 text-blue-600" />,
      description: "Tasarruf ve sabit giderler sonrası kalan bütçen."
    },
    { 
      label: "Tasarruf Hedefi", 
      value: formatPrice(metrics.savings_goal), 
      color: "text-purple-600", 
      bgColor: "bg-purple-50",
      icon: <Target className="w-5 h-5 text-purple-600" />,
      description: "Bu ay kenara ayırmayı hedeflediğin miktar."
    },
  ];

  return (
    <div className="space-y-6">
      {/* Üst Özet Kartlar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((item) => (
          <div 
            key={item.label} 
            className="group card hover:shadow-lg transition-all duration-300 cursor-pointer border border-transparent hover:border-gray-200"
            title={item.description}
          >
            <div className="flex items-center justify-between mb-3">
              <div className={`p-2 rounded-lg ${item.bgColor}`}>
                {item.icon}
              </div>
              <Info className="w-4 h-4 text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">{item.label}</p>
              <p className={`text-2xl font-bold tracking-tight ${item.color}`}>
                {item.value}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Bütçe Sağlığı ve Progress Bar */}
      <div className="card shadow-sm border border-gray-100">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-gray-700" />
            <h2 className="font-bold text-gray-800 text-lg">Bütçe Sağlığı</h2>
          </div>
          <div className="flex items-center gap-2">
             <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${getBudgetStatusColor(budget.status)} bg-opacity-10`}>
              {budget.status === "healthy" ? "● Sağlıklı" : budget.status === "warning" ? "● Dikkat" : "● Kritik"}
            </span>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600 font-medium">Gider Kullanım Oranı</span>
            <span className={`font-bold ${metrics.expense_ratio > 80 ? 'text-red-500' : 'text-gray-700'}`}>
              %{metrics.expense_ratio}
            </span>
          </div>
          
          <div className="w-full bg-gray-100 rounded-full h-4 overflow-hidden shadow-inner">
            <div
              className={`${getProgressColor(metrics.expense_ratio)} h-full rounded-full transition-all duration-1000 ease-out shadow-sm`}
              style={{ width: `${animatedWidth}%` }}
            />
          </div>

          <div className="grid grid-cols-3 text-[10px] uppercase tracking-widest text-gray-400 font-semibold pt-1">
            <span>Düşük</span>
            <span className="text-center">Orta</span>
            <span className="text-right">Yüksek</span>
          </div>
        </div>

        <p className="text-xs text-gray-400 mt-6 leading-relaxed italic">
          * Bu veriler girdiğin aylık bütçe ve harcama alışkanlıklarına göre anlık hesaplanmaktadır.
        </p>
      </div>
    </div>
  );
}