"use client";
export const dynamic = "force-dynamic";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { authApi } from "@/lib/api";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import Sidebar from "@/app/dashboard/components/Sidebar";
import {
  User, Bell, Shield, ChevronRight, LogOut, LucideIcon,
  LifeBuoy, Bug, Lightbulb, MessageCircle, Send, CheckCircle, ChevronDown,
} from "lucide-react";

interface UserInfo { full_name?: string; email?: string; }
interface SettingsItem { href?: string; icon: LucideIcon; label: string; desc: string; disabled?: boolean; onClick?: () => void; }

const FEEDBACK_CATEGORY_DEFS = [
  { value: "bug", key: "feedback.catBug", icon: Bug, color: "text-red-500", bg: "bg-red-50 dark:bg-red-900/20", border: "border-red-200 dark:border-red-800/40" },
  { value: "suggestion", key: "feedback.catSuggestion", icon: Lightbulb, color: "text-amber-500", bg: "bg-amber-50 dark:bg-amber-900/20", border: "border-amber-200 dark:border-amber-800/40" },
  { value: "question", key: "feedback.catQuestion", icon: MessageCircle, color: "text-blue-500", bg: "bg-blue-50 dark:bg-blue-900/20", border: "border-blue-200 dark:border-blue-800/40" },
];

const PRIORITY_DEFS = [
  { value: "low", key: "feedback.prioLow" },
  { value: "medium", key: "feedback.prioMedium" },
  { value: "high", key: "feedback.prioHigh" },
];

function FeedbackForm() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState("bug");
  const [priority, setPriority] = useState("medium");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !description.trim()) return;
    setSubmitting(true);
    await new Promise((r) => setTimeout(r, 900));
    setSubmitting(false);
    setSubmitted(true);
  }

  function reset() {
    setTitle(""); setDescription(""); setCategory("bug"); setPriority("medium");
    setSubmitted(false);
  }

  return (
    <div className="card p-0 overflow-hidden">
      <button
        onClick={() => setOpen((p) => !p)}
        className="w-full flex items-center gap-4 px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors group"
      >
        <div className="w-9 h-9 bg-gray-100 dark:bg-gray-700/60 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:bg-blue-50 dark:group-hover:bg-blue-900/30 transition-colors">
          <LifeBuoy className="w-4 h-4 text-gray-500 dark:text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors" />
        </div>
        <div className="flex-1 text-left min-w-0">
          <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{t("settings.items.feedback")}</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{t("settings.items.feedbackDesc")}</p>
        </div>
        <ChevronDown className={`w-4 h-4 text-gray-300 dark:text-gray-600 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: [0.25, 0.1, 0.25, 1] }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 border-t border-gray-100 dark:border-gray-700/60 pt-4">
              {submitted ? (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex flex-col items-center text-center py-8 gap-3"
                >
                  <div className="w-12 h-12 bg-emerald-50 dark:bg-emerald-900/20 rounded-2xl flex items-center justify-center">
                    <CheckCircle className="w-6 h-6 text-emerald-500" />
                  </div>
                  <p className="text-sm font-bold text-gray-900 dark:text-gray-100">{t("feedback.successTitle")}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{t("feedback.successDesc")}</p>
                  <button onClick={reset} className="btn-primary text-xs px-4 py-2 mt-1">{t("feedback.newMessage")}</button>
                </motion.div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  {/* Kategori */}
                  <div>
                    <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">{t("feedback.categoryLabel")}</label>
                    <div className="grid grid-cols-3 gap-2">
                      {FEEDBACK_CATEGORY_DEFS.map(({ value, key, icon: Icon, color, bg, border }) => (
                        <button
                          key={value}
                          type="button"
                          onClick={() => setCategory(value)}
                          className={`flex flex-col items-center gap-1.5 py-2.5 rounded-xl border-2 transition-all duration-200 ${
                            category === value
                              ? `${border} ${bg}`
                              : "border-gray-100 dark:border-gray-700 bg-white dark:bg-gray-800/40 hover:border-gray-200 dark:hover:border-gray-600"
                          }`}
                        >
                          <div className={`w-7 h-7 rounded-lg ${bg} flex items-center justify-center`}>
                            <Icon className={`w-3.5 h-3.5 ${color}`} />
                          </div>
                          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{t(key)}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Öncelik */}
                  <div>
                    <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">{t("feedback.priorityLabel")}</label>
                    <div className="flex gap-2">
                      {PRIORITY_DEFS.map(({ value, key }) => (
                        <button
                          key={value}
                          type="button"
                          onClick={() => setPriority(value)}
                          className={`px-3 py-1 rounded-full text-xs font-medium border transition-all duration-200 ${
                            priority === value
                              ? "bg-blue-600 text-white border-blue-600"
                              : "border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-gray-300"
                          }`}
                        >
                          {t(key)}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Başlık */}
                  <div>
                    <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1.5">{t("feedback.titleLabel")}</label>
                    <input
                      type="text"
                      className="input w-full text-sm"
                      placeholder={t("feedback.titlePlaceholder")}
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      required
                    />
                  </div>

                  {/* Açıklama */}
                  <div>
                    <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1.5">{t("feedback.descLabel")}</label>
                    <textarea
                      className="input w-full resize-none text-sm"
                      rows={3}
                      placeholder={t("feedback.descPlaceholder")}
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      required
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={submitting || !title.trim() || !description.trim()}
                    className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50 text-sm"
                  >
                    {submitting
                      ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      : <Send className="w-3.5 h-3.5" />
                    }
                    {submitting ? t("feedback.submitting") : t("feedback.submit")}
                  </button>
                </form>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function SettingsPage() {
  const { t } = useTranslation();
  const { loading } = useAuth();
  const [user, setUser] = useState<UserInfo | null>(null);

  const accountItems: SettingsItem[] = [
    { href: "/settings/account", icon: User, label: t("settings.items.accountInfo"), desc: t("settings.items.accountInfoDesc") },
  ];

  const appItems: SettingsItem[] = [
    { href: "/settings/notifications", icon: Bell, label: t("settings.items.notifications"), desc: t("settings.items.notificationsDesc") },
    { href: "/settings/privacy", icon: Shield, label: t("settings.items.privacy"), desc: t("settings.items.privacyDesc") },
  ];

  useEffect(() => {
    authApi.me().then((d) => setUser(d as UserInfo)).catch(() => {});
  }, []);

  function renderItems(items: SettingsItem[]) {
    return (
      <div className="card p-0 overflow-hidden">
        {items.map((item, i) => {
          const Icon = item.icon;
          const isLast = i === items.length - 1;
          const inner = (
            <>
              <div className="w-9 h-9 bg-gray-100 dark:bg-gray-700/60 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:bg-blue-50 dark:group-hover:bg-blue-900/30 transition-colors">
                <Icon className="w-4 h-4 text-gray-500 dark:text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{item.label}</p>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{item.desc}</p>
              </div>
              <ChevronRight className="w-4 h-4 text-gray-300 dark:text-gray-600 group-hover:text-gray-400 flex-shrink-0" />
            </>
          );
          const cls = `flex items-center gap-4 px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors group ${item.disabled ? "pointer-events-none opacity-50" : ""} ${!isLast ? "border-b border-gray-100 dark:border-gray-700/60" : ""}`;
          if (item.href) return <Link key={item.label} href={item.href} className={cls}>{inner}</Link>;
          return <button key={item.label} onClick={item.onClick} className={`w-full text-left ${cls}`}>{inner}</button>;
        })}
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg-mesh)" }}>
      <Sidebar userName={user?.full_name} userEmail={user?.email} />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-6 py-8">
          <motion.h1
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-6"
          >
            {t("settings.title")}
          </motion.h1>

          {loading ? (
            <div className="flex justify-center py-20">
              <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35 }}
              className="space-y-6"
            >
              {/* Hesap */}
              <div>
                <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2 px-1">{t("settings.section.account")}</p>
                {renderItems(accountItems)}
              </div>

              {/* Uygulama */}
              <div>
                <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2 px-1">{t("settings.section.app")}</p>
                {renderItems(appItems)}
              </div>

              {/* Yardım */}
              <div>
                <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2 px-1">{t("settings.section.help")}</p>
                <FeedbackForm />
              </div>

              {/* Oturum */}
              <div>
                <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2 px-1">{t("settings.section.session")}</p>
                <div className="card p-0 overflow-hidden">
                  <button
                    onClick={authApi.logout}
                    className="w-full flex items-center gap-4 px-5 py-4 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors group"
                  >
                    <div className="w-9 h-9 bg-gray-100 dark:bg-gray-700/60 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:bg-red-100 dark:group-hover:bg-red-900/40 transition-colors">
                      <LogOut className="w-4 h-4 text-gray-500 dark:text-gray-400 group-hover:text-red-500 transition-colors" />
                    </div>
                    <div className="flex-1 text-left">
                      <p className="text-sm font-medium text-gray-800 dark:text-gray-200 group-hover:text-red-500 transition-colors">{t("settings.items.logout")}</p>
                      <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{t("settings.items.logoutDesc")}</p>
                    </div>
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </main>
    </div>
  );
}
