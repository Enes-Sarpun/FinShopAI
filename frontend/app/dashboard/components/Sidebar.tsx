"use client";
import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  ShoppingBag, LayoutDashboard, MessageSquarePlus,
  Settings, LogOut, ChevronDown,
  Wallet, Brain, PanelLeftClose, PanelLeftOpen, Menu, X,
  Sun, Moon, Monitor,
} from "lucide-react";
import { authApi, chatApi } from "@/lib/api";
import { useTheme } from "@/lib/ThemeContext";
import type { ChatHistory } from "@/types";

interface SidebarProps {
  userName?: string;
  userEmail?: string;
}

const NAV_ITEMS = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/chat", icon: MessageSquarePlus, label: "Yeni Sohbet" },
];

const BOTTOM_ITEMS = [
  { href: "/onboarding/budget", icon: Wallet, label: "Bütçe Ayarları" },
  { href: "/onboarding/personality", icon: Brain, label: "Kişilik Testi" },
  { href: "/settings", icon: Settings, label: "Ayarlar" },
];

interface ContentProps {
  collapsed: boolean;
  setCollapsed: (v: boolean) => void;
  userName?: string;
  userEmail?: string;
  history: ChatHistory[];
  onClose?: () => void;
}

function ThemeToggle({ collapsed }: { collapsed: boolean }) {
  const { theme, setTheme } = useTheme();

  const next = theme === "light" ? "dark" : theme === "dark" ? "system" : "light";
  const Icon = theme === "dark" ? Moon : theme === "system" ? Monitor : Sun;
  const label = theme === "dark" ? "Koyu" : theme === "system" ? "Sistem" : "Açık";

  return (
    <button
      onClick={() => setTheme(next)}
      title={`Tema: ${label} (değiştir)`}
      className="flex items-center gap-3 w-full px-2.5 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
    >
      <Icon className="w-4 h-4 flex-shrink-0" />
      {!collapsed && <span className="truncate">{label}</span>}
    </button>
  );
}

function SidebarContent({ collapsed, setCollapsed, userName, userEmail, history, onClose }: ContentProps) {
  const pathname = usePathname();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const initials = userName
    ? userName.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2)
    : "?";

  return (
    <div className="flex flex-col h-full">
      {/* ── Üst: Logo + Collapse ── */}
      <div className="flex items-center justify-between px-3 py-3 border-b border-gray-200/80 dark:border-gray-700/60">
        {!collapsed && (
          <Link href="/dashboard" className="flex items-center gap-2 px-1" onClick={onClose}>
            <div className="w-6 h-6 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0">
              <ShoppingBag className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-bold text-gray-900 dark:text-gray-100 text-sm">FinShop AI</span>
          </Link>
        )}
        <button
          onClick={onClose ? onClose : () => setCollapsed(!collapsed)}
          className={`p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-gray-500 dark:text-gray-400 ${collapsed ? "mx-auto" : ""}`}
        >
          {onClose
            ? <X className="w-4 h-4" />
            : collapsed
              ? <PanelLeftOpen className="w-4 h-4" />
              : <PanelLeftClose className="w-4 h-4" />
          }
        </button>
      </div>

      {/* ── Ana Nav ── */}
      <div className="px-2 pt-3 space-y-0.5">
        {NAV_ITEMS.map(({ href, icon: Icon, label }) => (
          <Link
            key={href}
            href={href}
            title={collapsed ? label : undefined}
            onClick={onClose}
            className={`flex items-center gap-3 px-2.5 py-2 rounded-lg text-sm transition-all duration-150 ${
              pathname === href
                ? "bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium"
                : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100"
            }`}
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            {!collapsed && <span className="truncate">{label}</span>}
          </Link>
        ))}
      </div>

      {/* ── Geçmiş Sohbetler ── */}
      {!collapsed && (
        <div className="flex-1 overflow-y-auto px-2 pt-4 min-h-0">
          <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider px-2.5 mb-2">
            Geçmiş
          </p>
          <div className="space-y-0.5">
            {history.length === 0 ? (
              <p className="text-xs text-gray-400 dark:text-gray-500 px-2.5 py-2">Henüz sohbet yok</p>
            ) : (
              history.map((item) => (
                <Link
                  key={item.id}
                  href={`/chat?load=${item.id}`}
                  onClick={onClose}
                  className="block px-2.5 py-2 rounded-lg text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100 transition-colors truncate"
                  title={item.message}
                >
                  {item.message.length > 32 ? item.message.slice(0, 32) + "…" : item.message}
                </Link>
              ))
            )}
          </div>
        </div>
      )}
      {collapsed && <div className="flex-1" />}

      {/* ── Alt: Profil ── */}
      <div className="border-t border-gray-200/80 dark:border-gray-700/60 px-2 py-2 space-y-0.5">
        <ThemeToggle collapsed={collapsed} />
        {BOTTOM_ITEMS.map(({ href, icon: Icon, label }) => (
          <Link
            key={href}
            href={href}
            title={collapsed ? label : undefined}
            onClick={onClose}
            className="flex items-center gap-3 px-2.5 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            {!collapsed && <span className="truncate">{label}</span>}
          </Link>
        ))}

        {/* Kullanıcı */}
        <div className="relative" ref={userMenuRef}>
          <button
            onClick={() => setUserMenuOpen((p) => !p)}
            title={collapsed ? (userName || "Kullanıcı") : undefined}
            className="w-full flex items-center gap-3 px-2.5 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
              {initials}
            </div>
            {!collapsed && (
              <>
                <div className="flex-1 text-left min-w-0">
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate leading-tight">{userName || "Kullanıcı"}</p>
                  {userEmail && <p className="text-xs text-gray-400 dark:text-gray-500 truncate leading-tight">{userEmail}</p>}
                </div>
                <ChevronDown className={`w-3.5 h-3.5 text-gray-400 flex-shrink-0 transition-transform ${userMenuOpen ? "rotate-180" : ""}`} />
              </>
            )}
          </button>

          {userMenuOpen && (
            <div className={`absolute bottom-full mb-2 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 overflow-hidden z-50 ${collapsed ? "left-full ml-2 w-48" : "left-0 right-0"}`}>
              <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
                <p className="text-sm font-semibold text-gray-800 dark:text-gray-100 truncate">{userName || "Kullanıcı"}</p>
                <p className="text-xs text-gray-400 dark:text-gray-500 truncate mt-0.5">{userEmail || ""}</p>
              </div>
              <div className="py-1">
                <Link href="/settings/account" onClick={() => { setUserMenuOpen(false); onClose?.(); }}
                  className="block px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                  Hesabım
                </Link>
                <Link href="/settings" onClick={() => { setUserMenuOpen(false); onClose?.(); }}
                  className="block px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                  Ayarlar
                </Link>
              </div>
              <div className="border-t border-gray-100 dark:border-gray-700 py-1">
                <button onClick={authApi.logout}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                  <LogOut className="w-4 h-4" />
                  Çıkış Yap
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Sidebar({ userName, userEmail }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [history, setHistory] = useState<ChatHistory[]>([]);

  useEffect(() => {
    chatApi.getHistory(20)
      .then((d: unknown) => {
        const data = d as { history: ChatHistory[] };
        const seen = new Set<string>();
        const filtered = (data.history || []).filter((h) => {
          if (h.role !== "user") return false;
          const key = h.message.trim().toLowerCase().slice(0, 60);
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });
        setHistory(filtered.slice(0, 12));
      })
      .catch(() => {});
  }, []);

  return (
    <>
      {/* ── Desktop sidebar ── */}
      <aside
        className={`hidden md:flex flex-col h-screen border-r transition-all duration-300 ease-in-out flex-shrink-0
          bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl
          border-gray-200/80 dark:border-gray-700/60
          ${collapsed ? "w-[60px]" : "w-[240px]"}`}
      >
        <SidebarContent
          collapsed={collapsed}
          setCollapsed={setCollapsed}
          userName={userName}
          userEmail={userEmail}
          history={history}
        />
      </aside>

      {/* ── Mobile: hamburger butonu ── */}
      <button
        className="md:hidden fixed top-3 left-3 z-40 w-9 h-9 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm border border-gray-200/80 dark:border-gray-700/60 rounded-xl flex items-center justify-center shadow-sm text-gray-600 dark:text-gray-300"
        onClick={() => setMobileOpen(true)}
        aria-label="Menüyü aç"
      >
        <Menu className="w-4 h-4" />
      </button>

      {/* ── Mobile: drawer overlay ── */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              className="md:hidden fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
            />
            {/* Drawer panel */}
            <motion.aside
              className="md:hidden fixed left-0 top-0 bottom-0 z-50 w-[260px] flex flex-col
                bg-white/90 dark:bg-gray-900/90 backdrop-blur-xl
                border-r border-gray-200/80 dark:border-gray-700/60 shadow-2xl"
              initial={{ x: -260 }}
              animate={{ x: 0 }}
              exit={{ x: -260 }}
              transition={{ type: "spring", damping: 28, stiffness: 260 }}
            >
              <SidebarContent
                collapsed={false}
                setCollapsed={() => {}}
                userName={userName}
                userEmail={userEmail}
                history={history}
                onClose={() => setMobileOpen(false)}
              />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
