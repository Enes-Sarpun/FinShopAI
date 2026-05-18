"use client";
import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import {
  ShoppingBag, LayoutDashboard, MessageSquarePlus,
  Settings, LogOut, ChevronDown,
  Wallet, Brain, PanelLeftClose, PanelLeftOpen, Menu, X,
  Sun, Moon, Monitor, Pencil, Check, Star, Trash2,
} from "lucide-react";
import { authApi, chatApi } from "@/lib/api";
import { useTheme } from "@/lib/ThemeContext";
import type { ChatHistory } from "@/types";

interface SidebarProps {
  userName?: string;
  userEmail?: string;
}

interface ContentProps {
  collapsed: boolean;
  setCollapsed: (v: boolean) => void;
  userName?: string;
  userEmail?: string;
  history: ChatHistory[];
  onDeleteHistoryItem: (id: string) => void;
  onClose?: () => void;
}

function ThemeToggle({ collapsed }: { collapsed: boolean }) {
  const { theme, setTheme } = useTheme();
  const { t } = useTranslation();

  const next = theme === "light" ? "dark" : theme === "dark" ? "system" : "light";
  const Icon = theme === "dark" ? Moon : theme === "system" ? Monitor : Sun;
  const label = theme === "dark" ? t("theme.dark") : theme === "system" ? t("theme.system") : t("theme.light");

  return (
    <button
      onClick={() => setTheme(next)}
      title={`${t("theme.chooseTheme")}: ${label}`}
      className="flex items-center gap-3 w-full px-2.5 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
    >
      <Icon className="w-4 h-4 flex-shrink-0" />
      {!collapsed && <span className="truncate">{label}</span>}
    </button>
  );
}

function ChatItem({ item, onDelete, onClose }: {
  item: ChatHistory;
  onDelete: (id: string) => void;
  onClose?: () => void;
}) {
  const { t } = useTranslation();
  const [isEditing, setIsEditing] = useState(false);
  const [title, setTitle] = useState((item.metadata?.title as string) || item.message);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const searchParams = useSearchParams();
  const isActive = searchParams?.get("load") === item.id;

  async function handleSave() {
    if (!title.trim() || title === ((item.metadata?.title as string) || item.message)) {
      setIsEditing(false);
      return;
    }
    setIsSaving(true);
    try {
      await chatApi.updateTitle(item.id, title);
      item.metadata = { ...item.metadata, title };
    } catch {
      // ignore
    } finally {
      setIsSaving(false);
      setIsEditing(false);
    }
  }

  async function handleDelete(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm(t("navigation.confirmDeleteChat"))) return;
    setIsDeleting(true);
    try {
      await chatApi.deleteConversation(item.id);
      onDelete(item.id);
      // Aktif sohbet silindiyse yeni sohbet sayfasına dön
      if (isActive) {
        window.location.href = "/chat";
      }
    } catch {
      alert(t("navigation.deleteChatError"));
    } finally {
      setIsDeleting(false);
    }
  }

  const displayTitle = (item.metadata?.title as string) || item.message;

  if (isEditing) {
    return (
      <div className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-800">
        <input
          autoFocus
          className="flex-1 min-w-0 bg-transparent text-xs outline-none text-gray-900 dark:text-gray-100"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSave();
            if (e.key === "Escape") {
              setTitle(displayTitle);
              setIsEditing(false);
            }
          }}
          disabled={isSaving}
        />
        <button onClick={handleSave} disabled={isSaving} className="p-1 flex-shrink-0 text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 rounded">
          <Check className="w-3 h-3" />
        </button>
        <button onClick={() => { setTitle(displayTitle); setIsEditing(false); }} disabled={isSaving} className="p-1 flex-shrink-0 text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 rounded">
          <X className="w-3 h-3" />
        </button>
      </div>
    );
  }

  return (
    <div className={`group flex items-center justify-between px-2.5 py-0.5 rounded-lg transition-colors ${isActive ? "bg-blue-50/50 dark:bg-blue-900/20" : "hover:bg-gray-100 dark:hover:bg-gray-800"}`}>
      <Link
        href={`/chat?load=${item.id}`}
        onClick={onClose}
        className={`flex-1 min-w-0 py-1.5 text-xs truncate ${isActive ? "text-blue-700 dark:text-blue-300 font-medium" : "text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-100"}`}
        title={displayTitle}
      >
        {displayTitle.length > 32 ? displayTitle.slice(0, 32) + "…" : displayTitle}
      </Link>
      <div className="flex items-center gap-0.5 flex-shrink-0">
        <button
          onClick={() => setIsEditing(true)}
          className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-blue-500 transition-opacity"
          title={t("navigation.rename")}
        >
          <Pencil className="w-3 h-3" />
        </button>
        <button
          onClick={handleDelete}
          disabled={isDeleting}
          className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-opacity disabled:opacity-50"
          title={t("navigation.deleteChat")}
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}

function SidebarContent({ collapsed, setCollapsed, userName, userEmail, history, onDeleteHistoryItem, onClose }: ContentProps) {
  const { t } = useTranslation();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const loadId = searchParams?.get("load");
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  const navItems = [
    { href: "/dashboard", icon: LayoutDashboard, label: t("navigation.dashboard") },
    { href: "/chat", icon: MessageSquarePlus, label: t("navigation.newChat") },
    { href: "/watchlist", icon: Star, label: t("navigation.watchlist") },
  ];

  const bottomItems = [
    { href: "/onboarding/budget", icon: Wallet, label: t("navigation.budgetSettings") },
    { href: "/onboarding/personality", icon: Brain, label: t("navigation.personalityTest") },
    { href: "/settings", icon: Settings, label: t("navigation.settings") },
  ];

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
        {navItems.map(({ href, icon: Icon, label }) => (
          <Link
            key={href}
            href={href}
            title={collapsed ? label : undefined}
            onClick={onClose}
            className={`flex items-center gap-3 px-2.5 py-2 rounded-lg text-sm transition-all duration-150 ${
              (pathname === href && (href !== "/chat" || !loadId))
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
            {t("navigation.history")}
          </p>
          <div className="space-y-0.5">
            {history.length === 0 ? (
              <p className="text-xs text-gray-400 dark:text-gray-500 px-2.5 py-2">{t("navigation.noChats")}</p>
            ) : (
              history.map((item) => (
                <ChatItem key={item.id} item={item} onDelete={onDeleteHistoryItem} onClose={onClose} />
              ))
            )}
          </div>
        </div>
      )}
      {collapsed && <div className="flex-1" />}

      {/* ── Alt: Profil ── */}
      <div className="border-t border-gray-200/80 dark:border-gray-700/60 px-2 py-2 space-y-0.5">
        <ThemeToggle collapsed={collapsed} />
        {bottomItems.map(({ href, icon: Icon, label }) => (
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
            title={collapsed ? (userName || t("navigation.user")) : undefined}
            className="w-full flex items-center gap-3 px-2.5 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
              {initials}
            </div>
            {!collapsed && (
              <>
                <div className="flex-1 text-left min-w-0">
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate leading-tight">{userName || t("navigation.user")}</p>
                  {userEmail && <p className="text-xs text-gray-400 dark:text-gray-500 truncate leading-tight">{userEmail}</p>}
                </div>
                <ChevronDown className={`w-3.5 h-3.5 text-gray-400 flex-shrink-0 transition-transform ${userMenuOpen ? "rotate-180" : ""}`} />
              </>
            )}
          </button>

          {userMenuOpen && (
            <div className={`absolute bottom-full mb-2 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 overflow-hidden z-50 ${collapsed ? "left-full ml-2 w-48" : "left-0 right-0"}`}>
              <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
                <p className="text-sm font-semibold text-gray-800 dark:text-gray-100 truncate">{userName || t("navigation.user")}</p>
                <p className="text-xs text-gray-400 dark:text-gray-500 truncate mt-0.5">{userEmail || ""}</p>
              </div>
              <div className="py-1">
                <Link href="/settings/account" onClick={() => { setUserMenuOpen(false); onClose?.(); }}
                  className="block px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                  {t("navigation.myAccount")}
                </Link>
                <Link href="/settings" onClick={() => { setUserMenuOpen(false); onClose?.(); }}
                  className="block px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                  {t("navigation.settings")}
                </Link>
              </div>
              <div className="border-t border-gray-100 dark:border-gray-700 py-1">
                <button onClick={authApi.logout}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                  <LogOut className="w-4 h-4" />
                  {t("common.logout")}
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
  const { t } = useTranslation();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [history, setHistory] = useState<ChatHistory[]>([]);

  // Rota veya conversation_id değişince listeyi yenile
  // (yeni sohbet oluşunca veya clearChat sonrası URL değişince otomatik güncellenir)
  useEffect(() => {
    chatApi.getConversations(15)
      .then((d: unknown) => {
        const data = d as { history: ChatHistory[] };
        setHistory(data.history || []);
      })
      .catch(() => {});
  }, [pathname, searchParams]);

  // Yeni sohbette LLM başlık üretimi ~1-2sn sürer. Liste yüklendikten 3sn sonra
  // bir kez daha çekerek başlığın görünmesini sağla.
  const loadId = searchParams?.get("load");
  useEffect(() => {
    if (!loadId) return;
    const timer = setTimeout(() => {
      chatApi.getConversations(15)
        .then((d: unknown) => {
          const data = d as { history: ChatHistory[] };
          setHistory(data.history || []);
        })
        .catch(() => {});
    }, 3000);
    return () => clearTimeout(timer);
  }, [loadId]);

  const handleDeleteHistoryItem = (id: string) => {
    setHistory((prev) => prev.filter((h) => h.id !== id));
  };

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
          onDeleteHistoryItem={handleDeleteHistoryItem}
        />
      </aside>

      {/* ── Mobile: hamburger butonu ── */}
      <button
        className="md:hidden fixed top-3 left-3 z-40 w-9 h-9 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm border border-gray-200/80 dark:border-gray-700/60 rounded-xl flex items-center justify-center shadow-sm text-gray-600 dark:text-gray-300"
        onClick={() => setMobileOpen(true)}
        aria-label={t("navigation.openMenu")}
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
                onDeleteHistoryItem={handleDeleteHistoryItem}
                onClose={() => setMobileOpen(false)}
              />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
