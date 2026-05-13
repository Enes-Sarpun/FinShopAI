"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { authApi, chatApi } from "@/lib/api";
import Sidebar from "@/app/dashboard/components/Sidebar";
import {
  User, Mail, ArrowLeft, Pencil, Check, X,
  ShoppingBag, Brain, Wallet, Bell, Moon, Globe,
  Shield, LogOut,
} from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";

interface UserInfo { full_name?: string; email?: string; id?: string; }

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, delay, ease: [0.25, 0.1, 0.25, 1] as const },
});

function EditField({
  label, value, onSave,
}: { label: string; value: string; onSave: (v: string) => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    if (draft === value) { setEditing(false); return; }
    setSaving(true);
    try { await onSave(draft); } finally { setSaving(false); setEditing(false); }
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-400 mb-0.5">{label}</p>
        {editing ? (
          <input
            autoFocus
            className="input py-1 text-sm w-full"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSave(); if (e.key === "Escape") setEditing(false); }}
          />
        ) : (
          <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{value || "—"}</p>
        )}
      </div>
      {editing ? (
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={handleSave}
            disabled={saving}
            className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/30 text-blue-600 hover:bg-blue-100 transition-colors"
          >
            <Check className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => { setDraft(value); setEditing(false); }}
            className="p-1.5 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-gray-200 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : (
        <button
          onClick={() => setEditing(true)}
          className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex-shrink-0"
        >
          <Pencil className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}

export default function AccountPage() {
  const { loading } = useAuth();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [fetching, setFetching] = useState(true);
  const [stats, setStats] = useState({ searches: 0 });

  useEffect(() => {
    Promise.all([
      authApi.me().catch(() => null),
      chatApi.getHistory(100).catch(() => null),
    ]).then(([u, h]) => {
      setUser(u as UserInfo | null);
      const hist = (h as { history?: unknown[] } | null)?.history ?? [];
      setStats({ searches: hist.length });
    }).finally(() => setFetching(false));
  }, []);

  const initials = user?.full_name
    ? user.full_name.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2)
    : "?";

  async function saveName(name: string) {
    // Name update endpoint placeholder — update optimistically
    setUser((prev) => prev ? { ...prev, full_name: name } : prev);
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-900">
      <Sidebar userName={user?.full_name} userEmail={user?.email} />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-6 py-8">

          <Link
            href="/dashboard"
            className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition-colors mb-6"
          >
            <ArrowLeft className="w-4 h-4" />
            Dashboard'a Dön
          </Link>

          {loading || fetching ? (
            <div className="flex justify-center py-20">
              <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="space-y-5">

              {/* Profile header with gradient cover */}
              <motion.div {...fadeUp(0)} className="card p-0 overflow-hidden">
                <div className="h-24 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500" />
                <div className="px-6 pb-5">
                  <div className="flex items-end gap-4 -mt-10 mb-4">
                    <div className="w-20 h-20 rounded-2xl bg-white dark:bg-gray-800 border-4 border-white dark:border-gray-800 shadow-lg flex items-center justify-center text-blue-600 dark:text-blue-400 text-2xl font-bold flex-shrink-0">
                      {initials}
                    </div>
                    <div className="pb-1">
                      <p className="font-bold text-gray-900 dark:text-gray-100 text-lg">{user?.full_name || "Kullanıcı"}</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">{user?.email}</p>
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-3 gap-3 pt-3 border-t border-gray-100 dark:border-gray-700">
                    <div className="text-center">
                      <p className="text-xs text-gray-400 dark:text-gray-500 mb-0.5">Aramalar</p>
                      <div className="flex items-center justify-center gap-1">
                        <ShoppingBag className="w-3.5 h-3.5 text-blue-500" />
                        <span className="font-bold text-gray-800 dark:text-gray-200 text-sm">{stats.searches}</span>
                      </div>
                    </div>
                    <div className="text-center border-x border-gray-100 dark:border-gray-700">
                      <p className="text-xs text-gray-400 dark:text-gray-500 mb-0.5">Analizler</p>
                      <div className="flex items-center justify-center gap-1">
                        <Brain className="w-3.5 h-3.5 text-purple-500" />
                        <span className="font-bold text-gray-800 dark:text-gray-200 text-sm">1</span>
                      </div>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-gray-400 dark:text-gray-500 mb-0.5">Bütçe Planı</p>
                      <div className="flex items-center justify-center gap-1">
                        <Wallet className="w-3.5 h-3.5 text-emerald-500" />
                        <span className="font-bold text-gray-800 dark:text-gray-200 text-sm">Aktif</span>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* Hesap Bilgileri - inline edit */}
              <motion.div {...fadeUp(0.08)} className="card">
                <h2 className="font-semibold text-gray-800 dark:text-gray-100 mb-4">Hesap Bilgileri</h2>
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <div className="w-9 h-9 bg-gray-100 dark:bg-gray-700 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5">
                      <User className="w-4 h-4 text-gray-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <EditField
                        label="Ad Soyad"
                        value={user?.full_name ?? ""}
                        onSave={saveName}
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 bg-gray-100 dark:bg-gray-700 rounded-xl flex items-center justify-center flex-shrink-0">
                      <Mail className="w-4 h-4 text-gray-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-gray-400 mb-0.5">E-posta</p>
                      <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{user?.email || "—"}</p>
                    </div>
                    <span className="text-xs text-gray-400 dark:text-gray-500 flex-shrink-0">Değiştirilemez</span>
                  </div>
                </div>
              </motion.div>

              {/* Tercihler */}
              <motion.div {...fadeUp(0.14)} className="card">
                <h2 className="font-semibold text-gray-800 dark:text-gray-100 mb-4">Tercihler</h2>
                <div className="space-y-1">
                  {[
                    { icon: Bell, label: "Bildirimler", desc: "Uygulama bildirimleri", soon: true },
                    { icon: Moon, label: "Koyu Tema", desc: "Görünüm tercihi", soon: true },
                    { icon: Globe, label: "Dil", desc: "Türkçe", soon: true },
                  ].map(({ icon: Icon, label, desc, soon }) => (
                    <div key={label} className="flex items-center gap-3 py-3 border-b border-gray-100 dark:border-gray-700/60 last:border-0">
                      <div className="w-9 h-9 bg-gray-100 dark:bg-gray-700 rounded-xl flex items-center justify-center flex-shrink-0">
                        <Icon className="w-4 h-4 text-gray-500" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{label}</p>
                        <p className="text-xs text-gray-400 dark:text-gray-500">{desc}</p>
                      </div>
                      {soon && (
                        <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 px-2 py-0.5 rounded-full flex-shrink-0">
                          Yakında
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>

              {/* Güvenlik */}
              <motion.div {...fadeUp(0.2)} className="card">
                <h2 className="font-semibold text-gray-800 dark:text-gray-100 mb-4">Güvenlik</h2>
                <div className="space-y-1">
                  {[
                    { icon: Shield, label: "İki Faktörlü Doğrulama", desc: "Hesabını daha güvenli yap", soon: true },
                  ].map(({ icon: Icon, label, desc, soon }) => (
                    <div key={label} className="flex items-center gap-3 py-3">
                      <div className="w-9 h-9 bg-gray-100 dark:bg-gray-700 rounded-xl flex items-center justify-center flex-shrink-0">
                        <Icon className="w-4 h-4 text-gray-500" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{label}</p>
                        <p className="text-xs text-gray-400 dark:text-gray-500">{desc}</p>
                      </div>
                      {soon && (
                        <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 px-2 py-0.5 rounded-full flex-shrink-0">
                          Yakında
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>

              {/* Finansal Profil kısayolları */}
              <motion.div {...fadeUp(0.26)} className="card p-0 overflow-hidden">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-5 py-3 border-b border-gray-100 dark:border-gray-700">
                  Finansal Profilim
                </p>
                <Link href="/onboarding/budget"
                  className="flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors border-b border-gray-100 dark:border-gray-700 text-sm">
                  <span className="font-medium text-gray-700 dark:text-gray-300">Bütçemi Güncelle</span>
                  <span className="text-xs text-blue-600 dark:text-blue-400">Düzenle →</span>
                </Link>
                <Link href="/onboarding/personality"
                  className="flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors text-sm">
                  <span className="font-medium text-gray-700 dark:text-gray-300">Kişilik Testini Yenile</span>
                  <span className="text-xs text-blue-600 dark:text-blue-400">Düzenle →</span>
                </Link>
              </motion.div>

              {/* Çıkış */}
              <motion.div {...fadeUp(0.3)}>
                <button
                  onClick={() => {
                    localStorage.removeItem("finshop_token");
                    window.location.href = "/auth/login";
                  }}
                  className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl border border-red-100 dark:border-red-900/40 text-red-500 dark:text-red-400 text-sm font-medium hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Çıkış Yap
                </button>
              </motion.div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
