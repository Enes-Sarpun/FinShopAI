"use client";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { authApi } from "@/lib/api";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Sidebar from "@/app/dashboard/components/Sidebar";
import { User, Wallet, Brain, Bell, Shield, ChevronRight, LogOut, LucideIcon } from "lucide-react";

interface UserInfo { full_name?: string; email?: string; }
interface SettingsItem { href: string; icon: LucideIcon; label: string; desc: string; disabled?: boolean; }

export default function SettingsPage() {
  const { t } = useTranslation();
  const { loading } = useAuth();
  const [user, setUser] = useState<UserInfo | null>(null);

  const sections: { title: string; items: SettingsItem[] }[] = [
    {
      title: t("settings.section.account"),
      items: [
        { href: "/settings/account", icon: User, label: t("settings.items.accountInfo"), desc: t("settings.items.accountInfoDesc") },
      ],
    },
    {
      title: t("settings.section.financialProfile"),
      items: [
        { href: "/onboarding/budget", icon: Wallet, label: t("settings.items.budgetSettings"), desc: t("settings.items.budgetSettingsDesc") },
        { href: "/onboarding/personality", icon: Brain, label: t("settings.items.personalityTest"), desc: t("settings.items.personalityTestDesc") },
      ],
    },
    {
      title: t("settings.section.app"),
      items: [
        { href: "#", icon: Bell, label: t("settings.items.notifications"), desc: t("common.comingSoon"), disabled: true },
        { href: "#", icon: Shield, label: t("settings.items.privacy"), desc: t("common.comingSoon"), disabled: true },
      ],
    },
  ];

  useEffect(() => {
    authApi.me().then((d) => setUser(d as UserInfo)).catch(() => {});
  }, []);

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg-mesh)" }}>
      <Sidebar userName={user?.full_name} userEmail={user?.email} />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-6 py-8">
          <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-6">{t("settings.title")}</h1>

          {loading ? (
            <div className="flex justify-center py-20">
              <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="space-y-6">
              {sections.map((section) => (
                <div key={section.title}>
                  <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2 px-1">
                    {section.title}
                  </p>
                  <div className="card p-0 overflow-hidden">
                    {section.items.map((item, i) => {
                      const Icon = item.icon;
                      const isLast = i === section.items.length - 1;
                      return (
                        <Link key={item.href} href={item.href}
                          className={`flex items-center gap-4 px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors group ${
                            item.disabled ? "pointer-events-none opacity-50" : ""
                          } ${!isLast ? "border-b border-gray-100 dark:border-gray-700/60" : ""}`}>
                          <div className="w-9 h-9 bg-gray-100 dark:bg-gray-700/60 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:bg-blue-50 dark:group-hover:bg-blue-900/30 transition-colors">
                            <Icon className="w-4 h-4 text-gray-500 dark:text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{item.label}</p>
                            <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{item.desc}</p>
                          </div>
                          <ChevronRight className="w-4 h-4 text-gray-300 dark:text-gray-600 group-hover:text-gray-400 dark:group-hover:text-gray-500 flex-shrink-0" />
                        </Link>
                      );
                    })}
                  </div>
                </div>
              ))}

              <div>
                <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2 px-1">{t("settings.section.session")}</p>
                <div className="card p-0 overflow-hidden">
                  <button onClick={authApi.logout}
                    className="w-full flex items-center gap-4 px-5 py-4 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors group">
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
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
