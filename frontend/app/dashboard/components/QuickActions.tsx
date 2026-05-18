"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { MessageCircle, Clock, Wallet, Brain, Settings, LifeBuoy } from "lucide-react";

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
};

const cardAnim = {
  hidden: { opacity: 0, scale: 0.95, y: 12 },
  show: { opacity: 1, scale: 1, y: 0, transition: { duration: 0.35, ease: [0.25, 0.1, 0.25, 1] as const } },
};

export default function QuickActions() {
  const { t } = useTranslation();

  const actions = [
    {
      href: "/chat",
      label: t("quickActions.shoppingAssistant"),
      icon: MessageCircle,
      bg: "bg-blue-50 dark:bg-blue-900/20",
      iconColor: "text-blue-600 dark:text-blue-400",
      desc: t("quickActions.shoppingAssistantDesc"),
    },
    {
      href: "/chat/history",
      label: t("quickActions.pastSearches"),
      icon: Clock,
      bg: "bg-purple-50 dark:bg-purple-900/20",
      iconColor: "text-purple-600 dark:text-purple-400",
      desc: t("quickActions.pastSearchesDesc"),
    },
    {
      href: "/onboarding/budget",
      label: t("quickActions.updateBudget"),
      icon: Wallet,
      bg: "bg-emerald-50 dark:bg-emerald-900/20",
      iconColor: "text-emerald-600 dark:text-emerald-400",
      desc: t("quickActions.updateBudgetDesc"),
    },
    {
      href: "/onboarding/personality",
      label: t("quickActions.personalityTest"),
      icon: Brain,
      bg: "bg-orange-50 dark:bg-orange-900/20",
      iconColor: "text-orange-600 dark:text-orange-400",
      desc: t("quickActions.personalityTestDesc"),
    },
    {
      href: "/settings/account",
      label: t("quickActions.accountSettings"),
      icon: Settings,
      bg: "bg-gray-50 dark:bg-gray-700/30",
      iconColor: "text-gray-600 dark:text-gray-400",
      desc: t("quickActions.accountSettingsDesc"),
    },
    {
      href: "/support",
      label: t("quickActions.support"),
      icon: LifeBuoy,
      bg: "bg-rose-50 dark:bg-rose-900/20",
      iconColor: "text-rose-600 dark:text-rose-400",
      desc: t("quickActions.supportDesc"),
    },
  ];

  return (
    <div className="card">
      <h2 className="font-semibold text-gray-800 dark:text-gray-100 mb-4">{t("quickActions.title")}</h2>
      <motion.div
        className="grid grid-cols-2 md:grid-cols-3 gap-3"
        variants={container}
        initial="hidden"
        animate="show"
      >
        {actions.map(({ href, label, desc, icon: Icon, bg, iconColor }) => (
          <motion.div key={href} variants={cardAnim}>
            <Link
              href={href}
              className="group flex items-center gap-3 rounded-xl border border-gray-100 dark:border-gray-700/60 px-4 py-3 transition-all duration-200 hover:shadow-glass hover:-translate-y-0.5 hover:border-gray-200 dark:hover:border-gray-600 bg-white/50 dark:bg-gray-800/40 backdrop-blur-sm"
            >
              <div className={`w-9 h-9 rounded-xl ${bg} flex items-center justify-center flex-shrink-0 transition-transform duration-200 group-hover:scale-110`}>
                <Icon className={`w-4 h-4 ${iconColor}`} />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200 leading-tight truncate group-hover:text-blue-700 dark:group-hover:text-blue-400 transition-colors">
                  {label}
                </p>
                <p className="text-xs text-gray-400 dark:text-gray-500 truncate mt-0.5">{desc}</p>
              </div>
            </Link>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}
