"use client";
import { TrendingUp, TrendingDown, Wallet, PiggyBank } from "lucide-react";
import { motion } from "framer-motion";
import CountUp from "react-countup";
import type { Budget } from "@/types";

interface BudgetCardsProps {
  budget: Budget;
}

const STATUS_LABELS: Record<string, string> = {
  healthy: "Sağlıklı",
  warning: "Dikkat",
  critical: "Kritik",
};

const STATUS_BAR: Record<string, string> = {
  healthy: "bg-gradient-to-r from-emerald-400 to-emerald-500",
  warning: "bg-gradient-to-r from-amber-400 to-orange-400",
  critical: "bg-gradient-to-r from-red-400 to-red-500",
};

const STATUS_BADGE: Record<string, string> = {
  healthy: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  warning: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  critical: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300",
};

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.1, 0.25, 1] as const } },
};

export default function BudgetCards({ budget }: BudgetCardsProps) {
  const metrics = budget.financial_metrics;

  const cards = [
    {
      label: "Aylık Gelir",
      value: metrics.total_income,
      icon: TrendingUp,
      iconBg: "bg-emerald-50 dark:bg-emerald-900/20",
      iconColor: "text-emerald-600 dark:text-emerald-400",
      valueColor: "text-emerald-700 dark:text-emerald-300",
      shadow: "hover:shadow-card-income",
    },
    {
      label: "Sabit Giderler",
      value: metrics.fixed_expenses,
      icon: TrendingDown,
      iconBg: "bg-red-50 dark:bg-red-900/20",
      iconColor: "text-red-500 dark:text-red-400",
      valueColor: "text-red-600 dark:text-red-300",
      shadow: "hover:shadow-card-expense",
    },
    {
      label: "Harcanabilir",
      value: metrics.spendable_after_savings,
      icon: Wallet,
      iconBg: "bg-indigo-50 dark:bg-indigo-900/20",
      iconColor: "text-indigo-600 dark:text-indigo-400",
      valueColor: "text-indigo-700 dark:text-indigo-300",
      shadow: "hover:shadow-card-available",
    },
    {
      label: "Tasarruf Hedefi",
      value: metrics.savings_goal,
      icon: PiggyBank,
      iconBg: "bg-purple-50 dark:bg-purple-900/20",
      iconColor: "text-purple-600 dark:text-purple-400",
      valueColor: "text-purple-700 dark:text-purple-300",
      shadow: "hover:shadow-card-savings",
    },
  ];

  const expenseRatio = Math.min(metrics.expense_ratio, 100);

  return (
    <div className="space-y-4">
      {/* Özet Kartlar */}
      <motion.div
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
        variants={container}
        initial="hidden"
        animate="show"
      >
        {cards.map((c) => {
          const Icon = c.icon;
          return (
            <motion.div key={c.label} variants={item} className={`card card-hover ${c.shadow}`}>
              <div className={`w-10 h-10 rounded-xl ${c.iconBg} flex items-center justify-center mb-3`}>
                <Icon className={`w-5 h-5 ${c.iconColor}`} />
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{c.label}</p>
              <p className={`text-lg font-bold font-numeric ${c.valueColor}`}>
                <CountUp
                  end={c.value}
                  duration={1.2}
                  separator="."
                  decimal=","
                  decimals={0}
                  suffix=" ₺"
                  useEasing
                />
              </p>
            </motion.div>
          );
        })}
      </motion.div>

      {/* Bütçe Sağlığı */}
      <motion.div
        className="card"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35, duration: 0.4 }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-800 dark:text-gray-100">Bütçe Sağlığı</h2>
          <span className={`text-xs font-semibold px-3 py-1 rounded-full ${STATUS_BADGE[budget.status] ?? STATUS_BADGE.healthy}`}>
            {STATUS_LABELS[budget.status] ?? budget.status}
          </span>
        </div>
        <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
          <motion.div
            className={`${STATUS_BAR[budget.status] ?? "bg-blue-500"} h-3 rounded-full`}
            initial={{ width: 0 }}
            animate={{ width: `${expenseRatio}%` }}
            transition={{ duration: 0.8, ease: "easeOut", delay: 0.5 }}
          />
        </div>
        <div className="flex justify-between mt-2">
          <p className="text-xs text-gray-500 dark:text-gray-400">Gider oranı</p>
          <p className="text-xs font-semibold font-numeric text-gray-700 dark:text-gray-300">
            %{expenseRatio}
          </p>
        </div>
      </motion.div>
    </div>
  );
}
