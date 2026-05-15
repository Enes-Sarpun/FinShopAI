"use client";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { authApi, chatApi } from "@/lib/api";
import { useTheme } from "@/lib/ThemeContext";
import { useLang } from "@/lib/LangContext";
import Sidebar from "@/app/dashboard/components/Sidebar";
import {
  User, Mail, ArrowLeft, Pencil, Check, X,
  ShoppingBag, Brain, Wallet, Bell, Globe,
  Shield, LogOut, Sun, Moon, Monitor, ChevronDown,
  Camera, Upload, Trash2,
} from "lucide-react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";

interface UserInfo { full_name?: string; email?: string; }

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, delay, ease: [0.25, 0.1, 0.25, 1] as const },
});

// ── Banner gradient presets ────────────────────────────────────────────────
const BANNER_PRESETS = [
  { id: "indigo", style: "linear-gradient(135deg, #667eea, #764ba2)", label: "Mor-İndigo" },
  { id: "ocean", style: "linear-gradient(135deg, #2563eb, #7c3aed)", label: "Mavi-Mor" },
  { id: "sunset", style: "linear-gradient(135deg, #f093fb, #f5576c)", label: "Gün Batımı" },
  { id: "teal", style: "linear-gradient(135deg, #0ea5e9, #10b981)", label: "Okyanus" },
  { id: "night", style: "linear-gradient(135deg, #0f172a, #4c1d95)", label: "Gece" },
  { id: "spring", style: "linear-gradient(135deg, #84cc16, #22c55e)", label: "Bahar" },
  { id: "rose", style: "linear-gradient(135deg, #ec4899, #a855f7)", label: "Galaksi" },
  { id: "minimal", style: "linear-gradient(135deg, #e2e8f0, #94a3b8)", label: "Minimal" },
];

const BANNER_KEY = "finshop_banner";
const AVATAR_KEY = "finshop_avatar";
const MAX_AVATAR_BYTES = 2 * 1024 * 1024;

// ── Inline edit field ──────────────────────────────────────────────────────
function EditField({ label, value, onSave }: { label: string; value: string; onSave: (v: string) => Promise<void> }) {
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
          <p className="text-sm font-medium text-gray-800 dark:text-gray-200 max-w-[280px] truncate" title={value}>
            {value || "—"}
          </p>
        )}
      </div>
      {editing ? (
        <div className="flex items-center gap-1 flex-shrink-0">
          <button onClick={handleSave} disabled={saving}
            className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/30 text-blue-600 hover:bg-blue-100 transition-colors">
            <Check className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => { setDraft(value); setEditing(false); }}
            className="p-1.5 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-gray-200 transition-colors">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : (
        <button onClick={() => setEditing(true)}
          className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex-shrink-0">
          <Pencil className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}

// ── Theme segment control ──────────────────────────────────────────────────
function ThemeSelector() {
  const { theme, setTheme } = useTheme();
  const { t } = useTranslation();
  const options = [
    { value: "light" as const, icon: Sun, label: t("theme.light") },
    { value: "dark" as const, icon: Moon, label: t("theme.dark") },
    { value: "system" as const, icon: Monitor, label: t("theme.system") },
  ];

  return (
    <div className="flex gap-1 bg-gray-100 dark:bg-gray-700/60 rounded-xl p-1">
      {options.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
            theme === value
              ? "bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm"
              : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
          }`}
        >
          <Icon className="w-3.5 h-3.5" />
          {label}
        </button>
      ))}
    </div>
  );
}

// ── Language selector ──────────────────────────────────────────────────────
function LangSelector() {
  const { lang, setLang } = useLang();
  const [open, setOpen] = useState(false);
  const options = [
    { value: "tr" as const, flag: "🇹🇷", label: "Türkçe" },
    { value: "en" as const, flag: "🇬🇧", label: "English" },
  ];
  const current = options.find((o) => o.value === lang) ?? options[0];

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((p) => !p)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-500 transition-colors"
      >
        <span>{current.flag}</span>
        <span>{current.label}</span>
        <ChevronDown className={`w-3.5 h-3.5 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.97 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full mt-1 bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 shadow-lg overflow-hidden z-20 min-w-[130px]"
          >
            {options.map(({ value, flag, label }) => (
              <button
                key={value}
                onClick={() => { setLang(value); setOpen(false); }}
                className={`w-full flex items-center gap-2 px-4 py-2.5 text-sm transition-colors ${
                  lang === value
                    ? "bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                    : "text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                }`}
              >
                <span>{flag}</span>
                <span>{label}</span>
                {lang === value && <Check className="w-3.5 h-3.5 ml-auto" />}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Banner picker ──────────────────────────────────────────────────────────
function BannerPicker({ current, onSelect, onClose }: {
  current: string; onSelect: (style: string) => void; onClose: () => void;
}) {
  const { t } = useTranslation();
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="absolute right-3 top-3 bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-100 dark:border-gray-700 p-3 z-10 w-64"
    >
      <div className="flex items-center justify-between mb-2.5">
        <p className="text-xs font-semibold text-gray-700 dark:text-gray-300">{t("account.chooseBannerStyle")}</p>
        <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className="grid grid-cols-4 gap-2">
        {BANNER_PRESETS.map((p) => (
          <button
            key={p.id}
            onClick={() => { onSelect(p.style); onClose(); }}
            title={p.label}
            className={`h-8 rounded-lg transition-all ${current === p.style ? "ring-2 ring-blue-500 ring-offset-1 scale-105" : "hover:scale-105"}`}
            style={{ background: p.style }}
          />
        ))}
      </div>
    </motion.div>
  );
}

// ── Avatar picker ──────────────────────────────────────────────────────────
function AvatarMenu({ hasAvatar, onUpload, onRemove, onClose }: {
  hasAvatar: boolean;
  onUpload: () => void;
  onRemove: () => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  return (
    <motion.div
      initial={{ opacity: 0, y: -4, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -4, scale: 0.97 }}
      transition={{ duration: 0.15 }}
      className="absolute left-1/2 -translate-x-1/2 top-full mt-2 bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 shadow-lg overflow-hidden z-30 min-w-[190px]"
    >
      <button
        onClick={() => { onUpload(); onClose(); }}
        className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
      >
        <Upload className="w-3.5 h-3.5" />
        {t("account.uploadPhoto")}
      </button>
      {hasAvatar && (
        <button
          onClick={() => { onRemove(); onClose(); }}
          className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors border-t border-gray-100 dark:border-gray-700"
        >
          <Trash2 className="w-3.5 h-3.5" />
          {t("account.removePhoto")}
        </button>
      )}
    </motion.div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────
export default function AccountPage() {
  const { t } = useTranslation();
  const { loading } = useAuth();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [fetching, setFetching] = useState(true);
  const [searchCount, setSearchCount] = useState(0);
  const [bannerStyle, setBannerStyle] = useState(BANNER_PRESETS[0].style);
  const [bannerPickerOpen, setBannerPickerOpen] = useState(false);
  const [avatar, setAvatar] = useState<string | null>(null);
  const [avatarMenuOpen, setAvatarMenuOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const avatarRootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem(BANNER_KEY);
    if (saved) setBannerStyle(saved);

    const savedAvatar = localStorage.getItem(AVATAR_KEY);
    if (savedAvatar) setAvatar(savedAvatar);

    Promise.all([
      authApi.me().catch(() => null),
      chatApi.getHistory(100).catch(() => null),
    ]).then(([u, h]) => {
      setUser(u as UserInfo | null);
      const hist = (h as { history?: unknown[] } | null)?.history ?? [];
      setSearchCount(hist.length);
    }).finally(() => setFetching(false));
  }, []);

  // Avatar menüsünü dışa tıklayınca kapat
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (avatarRootRef.current && !avatarRootRef.current.contains(e.target as Node)) {
        setAvatarMenuOpen(false);
      }
    }
    if (avatarMenuOpen) {
      document.addEventListener("mousedown", handleClick);
      return () => document.removeEventListener("mousedown", handleClick);
    }
  }, [avatarMenuOpen]);

  function handleBannerSelect(style: string) {
    setBannerStyle(style);
    localStorage.setItem(BANNER_KEY, style);
  }

  function handleAvatarPick() {
    fileInputRef.current?.click();
  }

  function handleAvatarRemove() {
    setAvatar(null);
    localStorage.removeItem(AVATAR_KEY);
    toast.success(t("account.removePhoto"));
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      toast.error("Lütfen bir görsel dosyası seçin.");
      return;
    }
    if (file.size > MAX_AVATAR_BYTES) {
      toast.error("Görsel 2 MB'tan küçük olmalı.");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      try {
        localStorage.setItem(AVATAR_KEY, dataUrl);
        setAvatar(dataUrl);
        toast.success(t("account.changePhoto"));
      } catch {
        toast.error("Görsel kaydedilemedi.");
      }
    };
    reader.onerror = () => toast.error("Görsel okunamadı.");
    reader.readAsDataURL(file);
  }

  const initials = user?.full_name
    ? user.full_name.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2)
    : "?";

  async function saveName(name: string) {
    setUser((prev) => prev ? { ...prev, full_name: name } : prev);
  }

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg-mesh)" }}>
      <Sidebar userName={user?.full_name} userEmail={user?.email} />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-6 py-8">

          <Link href="/dashboard"
            className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition-colors mb-6">
            <ArrowLeft className="w-4 h-4" />
            {t("account.backToDashboard")}
          </Link>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            className="hidden"
            onChange={handleFileChange}
          />

          {loading || fetching ? (
            <div className="flex justify-center py-20">
              <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="space-y-5">

              {/* ── Profil Header ── */}
              <motion.div {...fadeUp(0)} className="card p-0 overflow-hidden">
                {/* Banner */}
                <div className="relative h-40" style={{ background: bannerStyle }}>
                  <button
                    onClick={() => setBannerPickerOpen((p) => !p)}
                    className="absolute top-3 right-3 px-2.5 py-1.5 bg-black/30 hover:bg-black/50 text-white text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 backdrop-blur-sm"
                  >
                    <Pencil className="w-3 h-3" />
                    {t("account.editBanner")}
                  </button>

                  <AnimatePresence>
                    {bannerPickerOpen && (
                      <BannerPicker
                        current={bannerStyle}
                        onSelect={handleBannerSelect}
                        onClose={() => setBannerPickerOpen(false)}
                      />
                    )}
                  </AnimatePresence>
                </div>

                {/* Avatar — yarısı banner'a biner */}
                <div className="px-6 pb-5">
                  <div className="-mt-12">
                    <div className="relative inline-block" ref={avatarRootRef}>
                      <button
                        type="button"
                        onClick={() => setAvatarMenuOpen((p) => !p)}
                        className="group relative w-24 h-24 rounded-2xl border-4 border-white dark:border-gray-900 shadow-xl flex items-center justify-center text-3xl font-bold flex-shrink-0 overflow-hidden focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                        style={!avatar ? { background: "linear-gradient(135deg, #2563eb, #7c3aed)", color: "#fff" } : undefined}
                        title={t("account.changePhoto")}
                      >
                        {avatar ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={avatar} alt="" className="w-full h-full object-cover" />
                        ) : (
                          <span>{initials}</span>
                        )}
                        <span className="absolute inset-0 bg-black/45 flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                          <Camera className="w-5 h-5 text-white mb-0.5" />
                          <span className="text-white text-[10px] font-medium uppercase tracking-wide">{t("account.changePhoto")}</span>
                        </span>
                      </button>

                      <AnimatePresence>
                        {avatarMenuOpen && (
                          <AvatarMenu
                            hasAvatar={!!avatar}
                            onUpload={handleAvatarPick}
                            onRemove={handleAvatarRemove}
                            onClose={() => setAvatarMenuOpen(false)}
                          />
                        )}
                      </AnimatePresence>
                    </div>
                    <div className="mt-3">
                      <p className="font-bold text-gray-900 dark:text-gray-100 text-xl max-w-[320px] truncate" title={user?.full_name}>
                        {user?.full_name || t("account.user")}
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">{user?.email}</p>
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-3 gap-3 pt-4 mt-4 border-t border-gray-100 dark:border-gray-700">
                    <Link href="/chat/history" className="text-center group cursor-pointer">
                      <p className="text-xs text-gray-400 dark:text-gray-500 mb-1">{t("account.searches")}</p>
                      <div className="flex items-center justify-center gap-1">
                        <ShoppingBag className="w-3.5 h-3.5 text-blue-500" />
                        <span className="font-bold text-gray-800 dark:text-gray-200 text-sm group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                          {searchCount > 0 ? searchCount : "—"}
                        </span>
                      </div>
                      {searchCount === 0 && (
                        <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5 leading-tight">{t("account.searchesEmpty")}</p>
                      )}
                    </Link>
                    <Link href="/onboarding/personality" className="text-center border-x border-gray-100 dark:border-gray-700 group cursor-pointer">
                      <p className="text-xs text-gray-400 dark:text-gray-500 mb-1">{t("account.analyses")}</p>
                      <div className="flex items-center justify-center gap-1">
                        <Brain className="w-3.5 h-3.5 text-purple-500" />
                        <span className="font-bold text-gray-800 dark:text-gray-200 text-sm group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">1</span>
                      </div>
                    </Link>
                    <Link href="/onboarding/budget" className="text-center group cursor-pointer">
                      <p className="text-xs text-gray-400 dark:text-gray-500 mb-1">{t("account.budgetPlan")}</p>
                      <div className="flex items-center justify-center gap-1">
                        <Wallet className="w-3.5 h-3.5 text-emerald-500" />
                        <span className="font-bold text-emerald-600 dark:text-emerald-400 text-sm">{t("common.active")}</span>
                      </div>
                    </Link>
                  </div>
                </div>
              </motion.div>

              {/* ── Hesap Bilgileri ── */}
              <motion.div {...fadeUp(0.08)} className="card">
                <h2 className="font-semibold text-gray-800 dark:text-gray-100 mb-4">{t("account.accountInfo")}</h2>
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <div className="w-9 h-9 bg-gray-100 dark:bg-gray-700 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5">
                      <User className="w-4 h-4 text-gray-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <EditField label={t("account.fullName")} value={user?.full_name ?? ""} onSave={saveName} />
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 bg-gray-100 dark:bg-gray-700 rounded-xl flex items-center justify-center flex-shrink-0">
                      <Mail className="w-4 h-4 text-gray-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-gray-400 mb-0.5">{t("account.email")}</p>
                      <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{user?.email || "—"}</p>
                    </div>
                    <span className="text-xs text-gray-400 dark:text-gray-500 flex-shrink-0">{t("account.notChangeable")}</span>
                  </div>
                </div>
              </motion.div>

              {/* ── Tercihler ── */}
              <motion.div {...fadeUp(0.14)} className="card">
                <h2 className="font-semibold text-gray-800 dark:text-gray-100 mb-4">{t("account.preferences")}</h2>
                <div className="space-y-4">
                  {/* Tema */}
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 bg-gray-100 dark:bg-gray-700 rounded-xl flex items-center justify-center flex-shrink-0">
                      <Moon className="w-4 h-4 text-gray-500" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">{t("account.appearance")}</p>
                      <ThemeSelector />
                    </div>
                  </div>

                  {/* Dil */}
                  <div className="flex items-center gap-3 pt-3 border-t border-gray-100 dark:border-gray-700/60">
                    <div className="w-9 h-9 bg-gray-100 dark:bg-gray-700 rounded-xl flex items-center justify-center flex-shrink-0">
                      <Globe className="w-4 h-4 text-gray-500" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-0.5">{t("account.language")}</p>
                      <p className="text-xs text-gray-400 dark:text-gray-500">{t("account.languageDesc")}</p>
                    </div>
                    <LangSelector />
                  </div>

                  {/* Bildirimler */}
                  <div className="flex items-center gap-3 pt-3 border-t border-gray-100 dark:border-gray-700/60">
                    <div className="w-9 h-9 bg-gray-100 dark:bg-gray-700 rounded-xl flex items-center justify-center flex-shrink-0">
                      <Bell className="w-4 h-4 text-gray-500" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{t("account.notifications")}</p>
                      <p className="text-xs text-gray-400 dark:text-gray-500">{t("account.notificationsDesc")}</p>
                    </div>
                    <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 px-2 py-0.5 rounded-full flex-shrink-0">
                      {t("common.comingSoon")}
                    </span>
                  </div>
                </div>
              </motion.div>

              {/* ── Güvenlik ── */}
              <motion.div {...fadeUp(0.2)} className="card">
                <h2 className="font-semibold text-gray-800 dark:text-gray-100 mb-4">{t("account.security")}</h2>
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-gray-100 dark:bg-gray-700 rounded-xl flex items-center justify-center flex-shrink-0">
                    <Shield className="w-4 h-4 text-gray-500" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{t("account.twoFactor")}</p>
                    <p className="text-xs text-gray-400 dark:text-gray-500">{t("account.twoFactorDesc")}</p>
                  </div>
                  <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 px-2 py-0.5 rounded-full flex-shrink-0">
                    {t("common.comingSoon")}
                  </span>
                </div>
              </motion.div>

              {/* ── Finansal Profil ── */}
              <motion.div {...fadeUp(0.26)} className="card p-0 overflow-hidden">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-5 py-3 border-b border-gray-100 dark:border-gray-700">
                  {t("account.financialProfile")}
                </p>
                <Link href="/onboarding/budget"
                  className="flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors border-b border-gray-100 dark:border-gray-700 text-sm">
                  <span className="font-medium text-gray-700 dark:text-gray-300">{t("account.updateBudget")}</span>
                  <span className="text-xs text-blue-600 dark:text-blue-400">{t("account.editAction")}</span>
                </Link>
                <Link href="/onboarding/personality"
                  className="flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors text-sm">
                  <span className="font-medium text-gray-700 dark:text-gray-300">{t("account.renewPersonality")}</span>
                  <span className="text-xs text-blue-600 dark:text-blue-400">{t("account.editAction")}</span>
                </Link>
              </motion.div>

              {/* ── Çıkış ── */}
              <motion.div {...fadeUp(0.3)}>
                <button
                  onClick={authApi.logout}
                  className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl border border-red-100 dark:border-red-900/40 text-red-500 dark:text-red-400 text-sm font-medium hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  {t("common.logout")}
                </button>
              </motion.div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
