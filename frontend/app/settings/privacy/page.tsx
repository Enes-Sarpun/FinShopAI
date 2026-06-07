"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft, Shield, Lock, Database, Eye, FileText,
  Trash2, Download, AlertTriangle, ChevronDown,
} from "lucide-react";
import { authApi } from "@/lib/api";
import { useTranslation } from "react-i18next";
import Sidebar from "@/app/dashboard/components/Sidebar";

interface UserInfo { full_name?: string; email?: string; }

function AccordionItem({ title, icon: Icon, iconBg, iconColor, children }: {
  title: string; icon: React.ElementType; iconBg: string; iconColor: string; children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card p-0 overflow-hidden">
      <button
        onClick={() => setOpen((p) => !p)}
        className="w-full flex items-center gap-4 px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors group"
      >
        <div className={`w-9 h-9 ${iconBg} rounded-xl flex items-center justify-center flex-shrink-0`}>
          <Icon className={`w-4 h-4 ${iconColor}`} />
        </div>
        <p className="flex-1 text-left text-sm font-medium text-gray-800 dark:text-gray-200">{title}</p>
        <ChevronDown className={`w-4 h-4 text-gray-300 dark:text-gray-600 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.25, 0.1, 0.25, 1] }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 pt-1 border-t border-gray-100 dark:border-gray-700/60 text-sm text-gray-600 dark:text-gray-400 leading-relaxed space-y-2">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function BulletList({ items, color }: { items: string[]; color: string }) {
  return (
    <ul className="space-y-1.5 mt-2">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-2">
          <span className={`w-1.5 h-1.5 rounded-full ${color} flex-shrink-0 mt-1.5`} />
          {item}
        </li>
      ))}
    </ul>
  );
}

export default function PrivacyPage() {
  const { t } = useTranslation();
  const [user, setUser] = useState<UserInfo | null>(null);

  useEffect(() => {
    authApi.me().then((d) => setUser(d as UserInfo)).catch(() => {});
  }, []);

  const dataStoredItems: string[] = t("privacy.dataStoredItems", { returnObjects: true }) as string[];
  const dataProtectedItems: string[] = t("privacy.dataProtectedItems", { returnObjects: true }) as string[];
  const dataPurposeItems: string[] = t("privacy.dataPurposeItems", { returnObjects: true }) as string[];
  const userRightsItems: string[] = t("privacy.userRightsItems", { returnObjects: true }) as string[];

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg-mesh)" }}>
      <Sidebar userName={user?.full_name} userEmail={user?.email} />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-6 py-8">

          <Link href="/settings" className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors mb-6">
            <ArrowLeft className="w-4 h-4" />
            {t("privacy.backToSettings")}
          </Link>

          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
            <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">{t("privacy.title")}</h1>
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">{t("privacy.subtitle")}</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08, duration: 0.35 }}
            className="space-y-4"
          >
            <div className="flex items-start gap-3 px-4 py-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-800/40 rounded-2xl">
              <Shield className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-emerald-700 dark:text-emerald-300 leading-relaxed">{t("privacy.safeBanner")}</p>
            </div>

            <AccordionItem title={t("privacy.dataStored")} icon={Database} iconBg="bg-blue-50 dark:bg-blue-900/20" iconColor="text-blue-500">
              <p>{t("privacy.dataStoredIntro")}</p>
              <BulletList items={dataStoredItems} color="bg-blue-400" />
            </AccordionItem>

            <AccordionItem title={t("privacy.dataProtected")} icon={Lock} iconBg="bg-indigo-50 dark:bg-indigo-900/20" iconColor="text-indigo-500">
              <BulletList items={dataProtectedItems} color="bg-indigo-400" />
            </AccordionItem>

            <AccordionItem title={t("privacy.dataPurpose")} icon={Eye} iconBg="bg-purple-50 dark:bg-purple-900/20" iconColor="text-purple-500">
              <p>{t("privacy.dataPurposeIntro")}</p>
              <BulletList items={dataPurposeItems} color="bg-purple-400" />
              <p className="mt-3 text-xs text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-800/60 rounded-xl px-3 py-2">
                {t("privacy.dataPurposeNote")}
              </p>
            </AccordionItem>

            <AccordionItem title={t("privacy.userRights")} icon={FileText} iconBg="bg-emerald-50 dark:bg-emerald-900/20" iconColor="text-emerald-500">
              <p>{t("privacy.userRightsIntro")}</p>
              <BulletList items={userRightsItems} color="bg-emerald-400" />
            </AccordionItem>

            <div className="card">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 bg-gray-100 dark:bg-gray-700/60 rounded-xl flex items-center justify-center">
                  <FileText className="w-4 h-4 text-gray-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">{t("privacy.dataOps")}</p>
                  <p className="text-xs text-gray-400 dark:text-gray-500">{t("privacy.dataOpsSubtitle")}</p>
                </div>
              </div>
              <div className="space-y-2 opacity-50 pointer-events-none">
                <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl border border-gray-100 dark:border-gray-700/60 bg-gray-50/60 dark:bg-gray-800/40 text-sm text-gray-600 dark:text-gray-400">
                  <Download className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <div className="text-left">
                    <p className="font-medium">{t("privacy.download")}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{t("privacy.downloadDesc")}</p>
                  </div>
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl border border-red-100 dark:border-red-900/30 bg-red-50/60 dark:bg-red-900/10 text-sm text-red-500">
                  <Trash2 className="w-4 h-4 flex-shrink-0" />
                  <div className="text-left">
                    <p className="font-medium">{t("privacy.deleteAccount")}</p>
                    <p className="text-xs text-red-400 mt-0.5">{t("privacy.deleteAccountDesc")}</p>
                  </div>
                </button>
              </div>
            </div>

            <div className="flex items-start gap-3 px-4 py-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-100 dark:border-amber-800/40 rounded-2xl">
              <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-amber-700 dark:text-amber-300 leading-relaxed">{t("privacy.contactBanner")}</p>
            </div>
          </motion.div>
        </div>
      </main>
    </div>
  );
}
