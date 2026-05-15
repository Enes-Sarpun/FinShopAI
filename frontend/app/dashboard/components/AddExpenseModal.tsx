"use client";
import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import {
  X, ShoppingCart, Car, HeartPulse, GraduationCap,
  Film, Shirt, Receipt, Package, Loader2,
} from "lucide-react";
import type { ExpenseCategory } from "@/types";

interface AddExpenseModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: { category: ExpenseCategory; amount: number; description?: string }) => Promise<void>;
}

const CATEGORIES: Array<{ id: ExpenseCategory; icon: typeof ShoppingCart; tint: string }> = [
  { id: "groceries",     icon: ShoppingCart, tint: "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800/60" },
  { id: "transport",     icon: Car,          tint: "bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-300 border-blue-200 dark:border-blue-800/60" },
  { id: "health",        icon: HeartPulse,   tint: "bg-rose-50 text-rose-600 dark:bg-rose-900/20 dark:text-rose-300 border-rose-200 dark:border-rose-800/60" },
  { id: "education",     icon: GraduationCap, tint: "bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-300 border-amber-200 dark:border-amber-800/60" },
  { id: "entertainment", icon: Film,         tint: "bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-300 border-purple-200 dark:border-purple-800/60" },
  { id: "clothing",      icon: Shirt,        tint: "bg-pink-50 text-pink-600 dark:bg-pink-900/20 dark:text-pink-300 border-pink-200 dark:border-pink-800/60" },
  { id: "bills",         icon: Receipt,      tint: "bg-orange-50 text-orange-600 dark:bg-orange-900/20 dark:text-orange-300 border-orange-200 dark:border-orange-800/60" },
  { id: "other",         icon: Package,      tint: "bg-gray-100 text-gray-600 dark:bg-gray-700/50 dark:text-gray-300 border-gray-200 dark:border-gray-700/60" },
];

export default function AddExpenseModal({ open, onClose, onSubmit }: AddExpenseModalProps) {
  const { t } = useTranslation();
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState<ExpenseCategory>("groceries");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const amountInputRef = useRef<HTMLInputElement>(null);

  // Modal açıldığında alanları sıfırla ve tutar inputuna odaklan
  useEffect(() => {
    if (open) {
      setAmount("");
      setCategory("groceries");
      setDescription("");
      setError(null);
      setSubmitting(false);
      // Animasyon sonrası focus, yoksa odak alınmıyor
      const tmo = setTimeout(() => amountInputRef.current?.focus(), 80);
      return () => clearTimeout(tmo);
    }
  }, [open]);

  // ESC ile kapatma
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !submitting) onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, submitting, onClose]);

  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    const parsed = Number(amount.replace(",", "."));
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setError(t("expense.amountMustBePositive"));
      amountInputRef.current?.focus();
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        category,
        amount: parsed,
        description: description.trim() || undefined,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("expense.error"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 z-[60] bg-black/40 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => !submitting && onClose()}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            className="fixed inset-0 z-[61] flex items-center justify-center p-4 pointer-events-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="pointer-events-auto w-full max-w-md bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-700/60 overflow-hidden"
              initial={{ opacity: 0, y: 20, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.97 }}
              transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            >
              <form onSubmit={handleSubmit}>
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-700/60">
                  <h2 className="font-semibold text-gray-900 dark:text-gray-100">{t("expense.addTitle")}</h2>
                  <button
                    type="button"
                    onClick={onClose}
                    disabled={submitting}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors disabled:opacity-50"
                    aria-label={t("expense.cancel")}
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Body */}
                <div className="px-5 py-5 space-y-5">
                  {/* Amount */}
                  <div>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
                      {t("expense.amountLabel")}
                    </label>
                    <div className="relative">
                      <input
                        ref={amountInputRef}
                        type="text"
                        inputMode="decimal"
                        pattern="[0-9]*[.,]?[0-9]*"
                        placeholder={t("expense.amountPlaceholder")}
                        value={amount}
                        onChange={(e) => {
                          // Sadece sayı, nokta ve virgül
                          const v = e.target.value.replace(/[^0-9.,]/g, "");
                          setAmount(v);
                          if (error) setError(null);
                        }}
                        disabled={submitting}
                        className="w-full text-3xl font-bold font-numeric bg-transparent text-gray-900 dark:text-gray-100 border-b-2 border-gray-200 dark:border-gray-700 focus:border-blue-500 dark:focus:border-blue-400 outline-none transition-colors py-1 pr-10 placeholder-gray-300 dark:placeholder-gray-600"
                      />
                      <span className="absolute right-1 top-1/2 -translate-y-1/2 text-2xl font-bold text-gray-400 dark:text-gray-500">
                        ₺
                      </span>
                    </div>
                    {error && (
                      <p className="text-xs text-red-500 mt-1.5">{error}</p>
                    )}
                  </div>

                  {/* Category chips */}
                  <div>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                      {t("expense.categoryLabel")}
                    </label>
                    <div className="grid grid-cols-4 gap-2">
                      {CATEGORIES.map(({ id, icon: Icon, tint }) => {
                        const selected = category === id;
                        return (
                          <button
                            key={id}
                            type="button"
                            onClick={() => setCategory(id)}
                            disabled={submitting}
                            className={`group flex flex-col items-center gap-1 py-2.5 px-1.5 rounded-xl border-2 transition-all duration-150 disabled:opacity-50 ${
                              selected
                                ? `${tint} scale-[1.02] shadow-sm`
                                : "border-gray-200 dark:border-gray-700/60 bg-white/50 dark:bg-gray-800/40 text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-600"
                            }`}
                            title={t(`expense.category.${id}`)}
                          >
                            <Icon className="w-4 h-4 flex-shrink-0" />
                            <span className="text-[10px] font-medium leading-tight text-center truncate w-full">
                              {t(`expense.category.${id}`)}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Description */}
                  <div>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
                      {t("expense.noteLabel")}
                    </label>
                    <input
                      type="text"
                      placeholder={t("expense.notePlaceholder")}
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      disabled={submitting}
                      maxLength={200}
                      className="w-full text-sm bg-white dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700/60 rounded-xl px-3 py-2 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-400 transition-all"
                    />
                  </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-gray-100 dark:border-gray-700/60 bg-gray-50/60 dark:bg-gray-800/30">
                  <button
                    type="button"
                    onClick={onClose}
                    disabled={submitting}
                    className="px-4 py-2 rounded-xl text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/60 transition-colors disabled:opacity-50"
                  >
                    {t("expense.cancel")}
                  </button>
                  <button
                    type="submit"
                    disabled={submitting || !amount}
                    className="px-5 py-2 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 active:scale-95 transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm flex items-center gap-2"
                  >
                    {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                    {submitting ? t("expense.saving") : t("expense.save")}
                  </button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export { CATEGORIES as EXPENSE_CATEGORIES };
