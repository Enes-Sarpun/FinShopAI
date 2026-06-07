"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Bell, Mail, BellOff, Info } from "lucide-react";
import { authApi } from "@/lib/api";
import { useTranslation } from "react-i18next";
import Sidebar from "@/app/dashboard/components/Sidebar";

interface UserInfo { full_name?: string; email?: string; }

function ToggleRow({ title, desc, enabled, disabled = false, onToggle }: {
  title: string; desc: string; enabled: boolean; disabled?: boolean; onToggle: () => void;
}) {
  return (
    <div className={`flex items-start justify-between gap-4 py-4 ${disabled ? "opacity-40 pointer-events-none" : ""}`}>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{title}</p>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5 leading-relaxed">{desc}</p>
      </div>
      <button
        type="button"
        onClick={onToggle}
        aria-checked={enabled}
        role="switch"
        className={`relative flex-shrink-0 w-11 h-6 rounded-full transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
          enabled ? "bg-blue-600" : "bg-gray-200 dark:bg-gray-700"
        }`}
      >
        <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-sm transition-transform duration-200 ${enabled ? "translate-x-5" : "translate-x-0"}`} />
      </button>
    </div>
  );
}

export default function NotificationsPage() {
  const { t } = useTranslation();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [browserNotif, setBrowserNotif] = useState(false);
  const [emailNotif, setEmailNotif] = useState(false);

  useEffect(() => {
    authApi.me().then((d) => setUser(d as UserInfo)).catch(() => {});
  }, []);

  const comingSoonItems: string[] = t("notifications.comingSoonItems", { returnObjects: true }) as string[];

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg-mesh)" }}>
      <Sidebar userName={user?.full_name} userEmail={user?.email} />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-6 py-8">

          <Link href="/settings" className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors mb-6">
            <ArrowLeft className="w-4 h-4" />
            {t("notifications.backToSettings")}
          </Link>

          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
            <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">{t("notifications.title")}</h1>
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">{t("notifications.subtitle")}</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08, duration: 0.35 }}
            className="space-y-4"
          >
            <div className="flex items-start gap-3 px-4 py-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800/40 rounded-2xl">
              <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">{t("notifications.infoBanner")}</p>
            </div>

            <div className="card">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 bg-indigo-50 dark:bg-indigo-900/20 rounded-xl flex items-center justify-center">
                  <Bell className="w-4 h-4 text-indigo-500" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">{t("notifications.preferencesTitle")}</p>
                  <p className="text-xs text-gray-400 dark:text-gray-500">{t("notifications.preferencesSubtitle")}</p>
                </div>
              </div>
              <div className="divide-y divide-gray-100 dark:divide-gray-700/60">
                <ToggleRow
                  title={t("notifications.browser")}
                  desc={t("notifications.browserDesc")}
                  enabled={browserNotif}
                  disabled
                  onToggle={() => setBrowserNotif((p) => !p)}
                />
                <ToggleRow
                  title={t("notifications.email")}
                  desc={t("notifications.emailDesc")}
                  enabled={emailNotif}
                  disabled
                  onToggle={() => setEmailNotif((p) => !p)}
                />
              </div>
            </div>

            <div className="card">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 bg-gray-100 dark:bg-gray-700/60 rounded-xl flex items-center justify-center">
                  <BellOff className="w-4 h-4 text-gray-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">{t("notifications.comingSoonTitle")}</p>
                  <p className="text-xs text-gray-400 dark:text-gray-500">{t("notifications.comingSoonSubtitle")}</p>
                </div>
              </div>
              <ul className="space-y-2">
                {comingSoonItems.map((item) => (
                  <li key={item} className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-gray-300 dark:bg-gray-600 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            {user?.email && (
              <div className="flex items-center gap-3 px-4 py-3 bg-gray-50 dark:bg-gray-800/60 rounded-2xl border border-gray-100 dark:border-gray-700/60">
                <Mail className="w-4 h-4 text-gray-400 flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs text-gray-500 dark:text-gray-400">{t("notifications.emailSendTo")}</p>
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{user.email}</p>
                </div>
              </div>
            )}
          </motion.div>
        </div>
      </main>
    </div>
  );
}
