"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { budgetApi } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="block text-sm text-gray-600 mb-1">{label}</label>
      <input
        type="number"
        min="0"
        className="input"
        placeholder="0"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

const EXPENSE_LABELS: Record<string, string> = {
  rent: "Kira", electricity: "Elektrik", water: "Su", gas: "Doğalgaz",
  internet: "İnternet", phone: "Telefon", loan_payment: "Kredi", insurance: "Sigorta",
  groceries: "Market", transportation: "Ulaşım", health: "Sağlık",
  education: "Eğitim", entertainment: "Eğlence", clothing: "Giyim",
};

export default function BudgetPage() {
  const router = useRouter();
  const { userId, loading } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [income, setIncome] = useState({ salary: "", extra_income: "" });
  const [expenses, setExpenses] = useState({
    rent: "", electricity: "", water: "", gas: "",
    internet: "", phone: "", loan_payment: "", insurance: "",
    groceries: "", transportation: "", health: "",
    education: "", entertainment: "", clothing: "",
  });
  const [savings, setSavings] = useState({ savings_goal: "", savings_purpose: "" });

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!userId) return;
    setError("");
    setSubmitting(true);
    try {
      await budgetApi.create(
        userId,
        { salary: Number(income.salary), extra_income: Number(income.extra_income) },
        Object.fromEntries(Object.entries(expenses).map(([k, v]) => [k, Number(v) || 0])),
        { savings_goal: Number(savings.savings_goal), savings_purpose: savings.savings_purpose }
      );
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Hata oluştu");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-10 px-4">
      <div className="card w-full max-w-2xl mx-auto">
        <h1 className="text-xl font-bold text-gray-900 mb-2">Bütçe Bilgileri</h1>
        <p className="text-gray-500 text-sm mb-6">Sana özel öneriler sunabilmemiz için aylık gelir ve giderlerini gir.</p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Gelir */}
          <section>
            <h2 className="font-semibold text-gray-700 mb-3">Gelir (TL)</h2>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Maaş" value={income.salary} onChange={(v) => setIncome((p) => ({ ...p, salary: v }))} />
              <Field label="Ek Gelir" value={income.extra_income} onChange={(v) => setIncome((p) => ({ ...p, extra_income: v }))} />
            </div>
          </section>

          {/* Sabit Giderler */}
          <section>
            <h2 className="font-semibold text-gray-700 mb-3">Sabit Giderler (TL)</h2>
            <div className="grid grid-cols-2 gap-4">
              {(["rent", "electricity", "water", "gas", "internet", "phone", "loan_payment", "insurance"] as const).map((k) => (
                <Field
                  key={k}
                  label={EXPENSE_LABELS[k]}
                  value={expenses[k]}
                  onChange={(v) => setExpenses((p) => ({ ...p, [k]: v }))}
                />
              ))}
            </div>
          </section>

          {/* Değişken Giderler */}
          <section>
            <h2 className="font-semibold text-gray-700 mb-3">Değişken Giderler (TL)</h2>
            <div className="grid grid-cols-2 gap-4">
              {(["groceries", "transportation", "health", "education", "entertainment", "clothing"] as const).map((k) => (
                <Field
                  key={k}
                  label={EXPENSE_LABELS[k]}
                  value={expenses[k]}
                  onChange={(v) => setExpenses((p) => ({ ...p, [k]: v }))}
                />
              ))}
            </div>
          </section>

          {/* Tasarruf */}
          <section>
            <h2 className="font-semibold text-gray-700 mb-3">Tasarruf Hedefi</h2>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Aylık Tasarruf (TL)" value={savings.savings_goal} onChange={(v) => setSavings((p) => ({ ...p, savings_goal: v }))} />
              <div>
                <label className="block text-sm text-gray-600 mb-1">Tasarruf Amacı</label>
                <input
                  type="text"
                  className="input"
                  placeholder="Tatil, araba..."
                  value={savings.savings_purpose}
                  onChange={(e) => setSavings((p) => ({ ...p, savings_purpose: e.target.value }))}
                />
              </div>
            </div>
          </section>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <button type="submit" className="btn-primary w-full" disabled={submitting || !income.salary}>
            {submitting ? "Kaydediliyor..." : "Devam Et"}
          </button>
        </form>
      </div>
    </div>
  );
}
