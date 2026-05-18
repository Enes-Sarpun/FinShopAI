"use client";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import {
  Plus, ShoppingCart, Car, HeartPulse, GraduationCap,
  Film, Shirt, Receipt, Package, Trash2, Wallet, AlertTriangle,
} from "lucide-react";
import toast from "react-hot-toast";
import { budgetApi } from "@/lib/api";
import type { Expense, ExpenseCategory } from "@/types";
import AddExpenseModal from "./AddExpenseModal";

interface ExpenseTrackerProps {
  userId: string;
  monthSpending: number;
  remainingSpendable: number;
  /** Modal kayıt başarılı olduğunda dashboard verilerini yenilemek için */
  onChange: () => Promise<void> | void;
}

const CATEGORY_VISUAL: Record<ExpenseCategory, { icon: typeof ShoppingCart; tint: string }> = {
  groceries:     { icon: ShoppingCart,   tint: "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-300" },
  transport:     { icon: Car,            tint: "bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300" },
  health:        { icon: HeartPulse,     tint: "bg-rose-50 text-rose-600 dark:bg-rose-900/30 dark:text-rose-300" },
  education:     { icon: GraduationCap,  tint: "bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-300" },
  entertainment: { icon: Film,           tint: "bg-purple-50 text-purple-600 dark:bg-purple-900/30 dark:text-purple-300" },
  clothing:      { icon: Shirt,          tint: "bg-pink-50 text-pink-600 dark:bg-pink-900/30 dark:text-pink-300" },
  bills:         { icon: Receipt,        tint: "bg-orange-50 text-orange-600 dark:bg-orange-900/30 dark:text-orange-300" },
  other:         { icon: Package,        tint: "bg-gray-100 text-gray-600 dark:bg-gray-700/50 dark:text-gray-300" },
};

function categoryVisual(category: string) {
  return CATEGORY_VISUAL[(category as ExpenseCategory)] ?? CATEGORY_VISUAL.other;
}

function formatTL(n: number) {
  return new Intl.NumberFormat("tr-TR").format(Math.round(n)) + " ₺";
}

function RelTime({ iso }: { iso: string }) {
  const { t } = useTranslation();
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  if (mins < 1) return <span>{t("wishlist.relJustNow")}</span>;
  if (mins < 60) return <span>{t("wishlist.relMins", { n: mins })}</span>;
  if (hours < 24) return <span>{t("wishlist.relHours", { n: hours })}</span>;
  return <span>{t("wishlist.relDays", { n: days })}</span>;
}

export default function ExpenseTracker({
  userId,
  monthSpending,
  remainingSpendable,
  onChange,
}: ExpenseTrackerProps) {
  const { t } = useTranslation();
  const [modalOpen, setModalOpen] = useState(false);
  const [items, setItems] = useState<Expense[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadRecent() {
    setLoading(true);
    try {
      const data = await budgetApi.listExpenses(userId, 5) as { items: Expense[] };
      setItems(data.items ?? []);
    } catch {
      // sessiz hata, yine de boş liste göster
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (userId) loadRecent();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  async function handleSubmit(data: { category: ExpenseCategory; amount: number; description?: string }) {
    const res = await budgetApi.addExpense(userId, data.category, data.amount, data.description) as {
      success: boolean;
      expense_id?: string;
      error?: string;
    };

    if (!res.success) {
      throw new Error(res.error || t("expense.error"));
    }

    // Anında local listeye ekle (optimistic UX) — sonra zaten reload edeceğiz
    const optimistic: Expense = {
      id: res.expense_id ?? `tmp-${Date.now()}`,
      user_id: userId,
      category: data.category,
      amount: data.amount,
      description: data.description ?? null,
      created_at: new Date().toISOString(),
    };
    setItems((prev) => [optimistic, ...prev].slice(0, 5));

    // Toast + Undo
    const expenseId = res.expense_id;
    toast.success(
      (toastObj) => (
        <span className="flex items-center gap-3">
          <span>{t("expense.addedToast", { amount: formatTL(data.amount).replace(" ₺", "") })}</span>
          {expenseId && (
            <button
              onClick={async () => {
                toast.dismiss(toastObj.id);
                try {
                  await budgetApi.deleteExpense(expenseId);
                  toast(t("expense.undoneToast"), { icon: "↩️" });
                  setItems((prev) => prev.filter((i) => i.id !== expenseId));
                  await onChange();
                } catch {
                  toast.error(t("expense.removeFailed"));
                }
              }}
              className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline"
            >
              {t("expense.undo")}
            </button>
          )}
        </span>
      ),
      { duration: 5000 }
    );

    // Üst component dashboard'u tazelesin (metrikler değişti)
    await onChange();
    // Listemizi de tazele
    loadRecent();
  }

  async function handleDelete(expense: Expense) {
    // Optimistic
    setItems((prev) => prev.filter((i) => i.id !== expense.id));
    try {
      await budgetApi.deleteExpense(expense.id);
      toast(t("expense.removed"), { icon: "🗑️" });
      await onChange();
    } catch {
      toast.error(t("expense.removeFailed"));
      // Geri ekle
      loadRecent();
    }
  }

  const overBudget = remainingSpendable < 0;

  return (
    <>
      <div className="card">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-indigo-50 dark:bg-indigo-900/30 flex items-center justify-center flex-shrink-0">
              <Wallet className="w-4 h-4 text-indigo-600 dark:text-indigo-300" />
            </div>
            <h3 className="font-semibold text-gray-900 dark:text-gray-100 text-sm">
              {t("expense.title")}
            </h3>
          </div>
          <button
            onClick={() => setModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 active:scale-95 transition-all duration-150 shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            {t("expense.addShort")}
          </button>
        </div>

        {/* Özet — Bu ay harcanan / Kalan harcanabilir */}
        <div className="grid grid-cols-2 gap-2.5 mb-4">
          <div className="bg-gray-50 dark:bg-gray-800/60 rounded-xl p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">{t("expense.spentThisMonth")}</p>
            <p className="text-lg font-bold text-rose-600 dark:text-rose-300 font-numeric">
              {formatTL(monthSpending)}
            </p>
          </div>
          <div className={`rounded-xl p-3 ${overBudget ? "bg-red-50 dark:bg-red-900/20" : "bg-emerald-50/60 dark:bg-emerald-900/20"}`}>
            <p className={`text-xs mb-0.5 flex items-center gap-1 ${overBudget ? "text-red-600 dark:text-red-300" : "text-emerald-700 dark:text-emerald-300"}`}>
              {overBudget && <AlertTriangle className="w-3 h-3" />}
              {t("expense.remainingSpendable")}
            </p>
            <p className={`text-lg font-bold font-numeric ${overBudget ? "text-red-600 dark:text-red-300" : "text-emerald-700 dark:text-emerald-300"}`}>
              {formatTL(remainingSpendable)}
            </p>
          </div>
        </div>

        {overBudget && (
          <div className="text-xs text-red-600 dark:text-red-300 bg-red-50 dark:bg-red-900/20 border border-red-200/60 dark:border-red-900/40 rounded-xl px-3 py-2 mb-3 flex items-start gap-2">
            <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
            <span>{t("expense.overBudget")}</span>
          </div>
        )}

        {/* Liste */}
        {loading ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="flex items-center gap-3 p-2">
                <div className="skeleton w-9 h-9 rounded-xl" />
                <div className="flex-1 space-y-1.5">
                  <div className="skeleton h-3 w-3/4 rounded" />
                  <div className="skeleton h-3 w-1/3 rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-5">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {t("expense.emptyTitle")}
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              {t("expense.emptyDesc")}
            </p>
          </div>
        ) : (
          <>
            <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2 px-1">
              {t("expense.recent")}
            </p>
            <div className="space-y-0.5">
              <AnimatePresence mode="popLayout">
                {items.map((item) => {
                  const v = categoryVisual(item.category);
                  const Icon = v.icon;
                  return (
                    <motion.div
                      key={item.id}
                      layout
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className="flex items-center gap-3 p-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/60 group transition-colors"
                    >
                      <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${v.tint}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">
                          {item.description?.trim() || t(`expense.category.${item.category}`)}
                        </p>
                        <p className="text-xs text-gray-400 dark:text-gray-500">
                          {t(`expense.category.${item.category}`)} · <RelTime iso={item.created_at} />
                        </p>
                      </div>
                      <span className="text-sm font-bold text-gray-900 dark:text-gray-100 font-numeric flex-shrink-0">
                        −{formatTL(item.amount)}
                      </span>
                      <button
                        onClick={() => handleDelete(item)}
                        className="p-1.5 rounded-lg text-gray-300 dark:text-gray-600 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 opacity-0 group-hover:opacity-100 transition-all flex-shrink-0"
                        title={t("expense.deleteTitle")}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          </>
        )}
      </div>

      <AddExpenseModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleSubmit}
      />
    </>
  );
}
