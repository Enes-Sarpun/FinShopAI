"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import { MessageCircle, Clock, Wallet, Brain } from "lucide-react";

const ACTIONS = [
  {
    href: "/chat",
    label: "Alışveriş Asistanı",
    icon: MessageCircle,
    gradient: "from-blue-500 to-indigo-500",
    bg: "bg-blue-50 dark:bg-blue-900/20",
    iconColor: "text-blue-600 dark:text-blue-400",
    desc: "Bütçene uygun ürün bul",
  },
  {
    href: "/chat/history",
    label: "Geçmiş Aramalar",
    icon: Clock,
    gradient: "from-purple-500 to-fuchsia-500",
    bg: "bg-purple-50 dark:bg-purple-900/20",
    iconColor: "text-purple-600 dark:text-purple-400",
    desc: "Önceki sohbetlere dön",
  },
  {
    href: "/onboarding/budget",
    label: "Bütçeyi Güncelle",
    icon: Wallet,
    gradient: "from-emerald-500 to-teal-500",
    bg: "bg-emerald-50 dark:bg-emerald-900/20",
    iconColor: "text-emerald-600 dark:text-emerald-400",
    desc: "Gelir ve giderlerini düzenle",
  },
  {
    href: "/onboarding/personality",
    label: "Kişilik Testi",
    icon: Brain,
    gradient: "from-orange-500 to-amber-500",
    bg: "bg-orange-50 dark:bg-orange-900/20",
    iconColor: "text-orange-600 dark:text-orange-400",
    desc: "Harcama profilini güncelle",
  },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07 } },
};

const cardAnim = {
  hidden: { opacity: 0, scale: 0.95, y: 12 },
  show: { opacity: 1, scale: 1, y: 0, transition: { duration: 0.35, ease: [0.25, 0.1, 0.25, 1] as const } },
};

export default function QuickActions() {
  return (
    <div className="card">
      <h2 className="font-semibold text-gray-800 dark:text-gray-100 mb-4">Hızlı Erişim</h2>
      <motion.div
        className="grid grid-cols-2 gap-3"
        variants={container}
        initial="hidden"
        animate="show"
      >
        {ACTIONS.map(({ href, label, desc, icon: Icon, bg, iconColor }) => (
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
