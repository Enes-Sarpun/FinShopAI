"use client";
import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, Wallet, PiggyBank, AlertTriangle, CheckCircle, Info } from "lucide-react";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import CountUp from "react-countup";
import type { Budget } from "@/types";

interface BudgetCardsProps {
  budget: Budget;
}

const STATUS_BADGE: Record<string, string> = {
  healthy: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  warning: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  critical: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300",
};

const STATUS_ICON: Record<string, typeof CheckCircle> = {
  healthy: CheckCircle,
  warning: AlertTriangle,
  critical: AlertTriangle,
};

const STATUS_ICON_COLOR: Record<string, string> = {
  healthy: "text-emerald-500",
  warning: "text-amber-500",
  critical: "text-red-500",
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
  const { t } = useTranslation();
  const metrics = budget.financial_metrics;
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setMounted(true), 100);
    return () => clearTimeout(timer);
  }, []);

  const STATUS_LABELS: Record<string, string> = {
    healthy: t("budget.statusHealthy"),
    warning: t("budget.statusWarning"),
    critical: t("budget.statusCritical"),
  };

  // Eğer backend bu ay harcananı veriyorsa, gerçek "kalan harcanabilir"i göster
  const monthSpending = metrics.current_month_spending ?? 0;
  const remainingSpendable = metrics.remaining_spendable ?? metrics.spendable_after_savings;
  const overBudget = remainingSpendable < 0;

  const cards = [
    {
      label: t("budget.monthlyIncome"),
      value: metrics.total_income,
      icon: TrendingUp,
      iconBg: "bg-emerald-50 dark:bg-emerald-900/20",
      iconColor: "text-emerald-600 dark:text-emerald-400",
      valueColor: "text-emerald-700 dark:text-emerald-300",
      shadow: "hover:shadow-card-income",
    },
    {
      label: t("budget.fixedExpenses"),
      value: metrics.fixed_expenses,
      icon: TrendingDown,
      iconBg: "bg-red-50 dark:bg-red-900/20",
      iconColor: "text-red-500 dark:text-red-400",
      valueColor: "text-red-600 dark:text-red-300",
      shadow: "hover:shadow-card-expense",
    },
    {
      label: t("budget.spendable"),
      value: remainingSpendable,
      icon: Wallet,
      iconBg: overBudget ? "bg-red-50 dark:bg-red-900/20" : "bg-indigo-50 dark:bg-indigo-900/20",
      iconColor: overBudget ? "text-red-500 dark:text-red-400" : "text-indigo-600 dark:text-indigo-400",
      valueColor: overBudget ? "text-red-600 dark:text-red-300" : "text-indigo-700 dark:text-indigo-300",
      shadow: "hover:shadow-card-available",
    },
    {
      label: t("budget.savingsGoal"),
      value: metrics.savings_goal,
      icon: PiggyBank,
      iconBg: "bg-purple-50 dark:bg-purple-900/20",
      iconColor: "text-purple-600 dark:text-purple-400",
      valueColor: "text-purple-700 dark:text-purple-300",
      shadow: "hover:shadow-card-savings",
    },
  ];

  // Multi-segment bar: Sabit gider + bu ay yapılan harcamalar (variable) + tasarruf + kalan
  const income = metrics.total_income || 1;
  const expensePct = Math.min((metrics.fixed_expenses / income) * 100, 100);
  const variableSpentPct = Math.min((monthSpending / income) * 100, Math.max(0, 100 - expensePct));
  const savingsPct = Math.min(
    (metrics.savings_goal / income) * 100,
    Math.max(0, 100 - expensePct - variableSpentPct)
  );
  const spendablePct = Math.min(
    (Math.max(0, remainingSpendable) / income) * 100,
    Math.max(0, 100 - expensePct - variableSpentPct - savingsPct)
  );

  const StatusIcon = STATUS_ICON[budget.status] ?? Info;

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
          <h2 className="font-semibold text-gray-800 dark:text-gray-100">{t("budget.health")}</h2>
          <span className={`text-xs font-semibold px-3 py-1 rounded-full flex items-center gap-1.5 ${STATUS_BADGE[budget.status] ?? STATUS_BADGE.healthy}`}>
            <StatusIcon className={`w-3.5 h-3.5 ${STATUS_ICON_COLOR[budget.status]}`} />
            {STATUS_LABELS[budget.status] ?? budget.status}
          </span>
        </div>

        {/* Multi-segment bar */}
        <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-4 overflow-hidden flex">
          <motion.div
            className="bg-gradient-to-r from-red-400 to-red-500 h-4 rounded-l-full"
            initial={{ width: 0 }}
            animate={{ width: mounted ? `${expensePct}%` : "0%" }}
            transition={{ duration: 0.8, ease: "easeOut", delay: 0.5 }}
            title={`${t("budget.fixedExpenses")}: %${expensePct.toFixed(0)}`}
          />
          {variableSpentPct > 0 && (
            <motion.div
              className="bg-gradient-to-r from-rose-300 to-rose-400 h-4"
              initial={{ width: 0 }}
              animate={{ width: mounted ? `${variableSpentPct}%` : "0%" }}
              transition={{ duration: 0.8, ease: "easeOut", delay: 0.55 }}
              title={`${t("budget.monthSpending")}: %${variableSpentPct.toFixed(0)}`}
            />
          )}
          <motion.div
            className="bg-gradient-to-r from-purple-400 to-purple-500 h-4"
            initial={{ width: 0 }}
            animate={{ width: mounted ? `${savingsPct}%` : "0%" }}
            transition={{ duration: 0.8, ease: "easeOut", delay: 0.6 }}
            title={`${t("budget.legendSavings")}: %${savingsPct.toFixed(0)}`}
          />
          <motion.div
            className="bg-gradient-to-r from-emerald-400 to-emerald-500 h-4 rounded-r-full"
            initial={{ width: 0 }}
            animate={{ width: mounted ? `${spendablePct}%` : "0%" }}
            transition={{ duration: 0.8, ease: "easeOut", delay: 0.7 }}
            title={`${t("budget.legendSpendable")}: %${spendablePct.toFixed(0)}`}
          />
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3">
          <span className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
            <span className="w-2.5 h-2.5 rounded-full bg-red-400 inline-block" />
            {t("budget.legendExpenses")} %{expensePct.toFixed(0)}
          </span>
          {variableSpentPct > 0 && (
            <span className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-300 inline-block" />
              {t("budget.monthSpending")} %{variableSpentPct.toFixed(0)}
            </span>
          )}
          <span className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-400 inline-block" />
            {t("budget.legendSavings")} %{savingsPct.toFixed(0)}
          </span>
          <span className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 inline-block" />
            {t("budget.legendSpendable")} %{spendablePct.toFixed(0)}
          </span>
        </div>

        {/* Extra metrics row */}
        <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
          <div className="text-center">
            <p className="text-xs text-gray-400 dark:text-gray-500 mb-0.5">{t("budget.availableBudget")}</p>
            <p className="text-sm font-bold text-indigo-600 dark:text-indigo-400 font-numeric">
              <CountUp end={metrics.available_budget} duration={1.2} separator="." decimals={0} suffix=" ₺" useEasing />
            </p>
          </div>
          <div className="text-center border-x border-gray-100 dark:border-gray-700">
            <p className="text-xs text-gray-400 dark:text-gray-500 mb-0.5">{t("budget.monthSpending")}</p>
            <p className="text-sm font-bold text-rose-600 dark:text-rose-300 font-numeric">
              <CountUp end={monthSpending} duration={1.2} separator="." decimals={0} suffix=" ₺" useEasing />
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-400 dark:text-gray-500 mb-0.5">{t("budget.expenseRatio")}</p>
            <p className="text-sm font-bold text-gray-700 dark:text-gray-300 font-numeric">
              %{Math.min(metrics.expense_ratio, 100).toFixed(0)}
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
