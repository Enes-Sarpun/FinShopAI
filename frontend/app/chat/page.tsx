"use client";
import { useState, useRef, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { chatApi, authApi } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { formatPrice } from "@/lib/utils";
import type { ChatResponse, Product } from "@/types";
import { Send, Sparkles, ShoppingBag, Trash2, Star, Zap, ChevronDown } from "lucide-react";
import { useTranslation } from "react-i18next";
import Image from "next/image";
import toast from "react-hot-toast";
import { wishlistService } from "@/lib/wishlistService";
import Sidebar from "@/app/dashboard/components/Sidebar";

function storageKey(id: string | null) {
  return id ? `finshop_thread_v2_${id}` : "finshop_thread_v2_new";
}

type MsgRole = "user" | "bot" | "products";
interface Msg {
  role: MsgRole;
  text?: string;
  products?: Product[];
  overBudgetProducts?: Product[];
  topPick?: { product_name: string; reason: string; value_score: number } | null;
  advice?: string;
  budgetStatus?: string;
}

const WELCOME: Msg[] = [];

const PRODUCT_SEARCH_STEPS = [
  "Düşünülüyor",
  "Ürün kategorisi analiz ediliyor",
  "Fiyat aralığı hesaplanıyor",
  "Seçenekler getiriliyor",
  "Sonuçlar hazırlanıyor",
];

function loadFromStorage(key: string): Msg[] | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Msg[];
    return parsed.length > 0 ? parsed : null;
  } catch { return null; }
}

function saveToStorage(key: string, msgs: Msg[]) {
  try { sessionStorage.setItem(key, JSON.stringify(msgs)); } catch { }
}

interface UserInfo { full_name?: string; email?: string; }


function ChatPageInner() {
  const { t } = useTranslation();
  const { loading } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [messages, setMessages] = useState<Msg[]>(WELCOME);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [productSteps, setProductSteps] = useState<string[]>([]);
  const stepTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [loadingThread, setLoadingThread] = useState(false);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const activeThreadId = useRef<string | null>(null);
  const paramHandled = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const modelMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    authApi.me().then((d) => setUser(d as UserInfo)).catch(() => { });
    setHydrated(true);
  }, []);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (modelMenuRef.current && !modelMenuRef.current.contains(e.target as Node)) {
        setModelMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const loadId = searchParams.get("load");
  const q = searchParams.get("q");

  useEffect(() => {
    if (!hydrated) return;

    if (loadId) {
      activeThreadId.current = loadId;
      const key = storageKey(loadId);
      const cached = loadFromStorage(key);
      if (cached && cached.length > 0) {
        setMessages(cached);
        setLoadingThread(false);
        return;
      }

      setLoadingThread(true);
      setMessages([]);
      paramHandled.current = true;
      chatApi.getThread(loadId).then((d: unknown) => {
        const data = d as { thread: { id: string; message: string; role: string; metadata?: Record<string, unknown> }[] };
        const thread = data.thread || [];
        if (thread.length === 0) {
          setMessages([{ role: "bot", text: "Bu sohbet bulunamadı veya yüklenemedi." }]);
          return;
        }

        const restored: Msg[] = [];
        for (const msg of thread) {
          if (msg.role === "user") {
            restored.push({ role: "user", text: msg.message });
          } else if (msg.role === "assistant") {
            const meta = msg.metadata || {};
            if (meta.type === "products") {
              const payload = meta.payload as {
                affordability_message?: string;
                summary?: string;
                financial_advice?: string;
                top_pick?: { product_name: string; reason: string; value_score: number } | null;
                products?: Product[];
                over_budget_products?: Product[];
                budget_status?: string;
              };
              if (payload?.summary)
                restored.push({ role: "bot", text: payload.summary, budgetStatus: payload.budget_status });
              const hasP = (payload?.products?.length ?? 0) > 0;
              const hasOB = (payload?.over_budget_products?.length ?? 0) > 0;
              if (hasP || hasOB)
                restored.push({ role: "products", products: payload?.products ?? [], overBudgetProducts: payload?.over_budget_products ?? [], topPick: payload?.top_pick ?? null, advice: payload?.financial_advice ?? undefined });
            } else {
              if (msg.message) restored.push({ role: "bot", text: msg.message });
            }
          }
        }
        if (restored.length > 0) {
          setMessages(restored);
          saveToStorage(key, restored);
        } else {
          setMessages([{ role: "bot", text: "Sohbet yüklendi fakat gösterilecek mesaj bulunamadı." }]);
        }
      }).catch(() => {
        setMessages([{ role: "bot", text: "⚠️ Sohbet yüklenirken bir hata oluştu." }]);
      }).finally(() => {
        setLoadingThread(false);
      });
      return;
    }

    activeThreadId.current = null;
    if (!q) {
      try { sessionStorage.removeItem(storageKey(null)); } catch { }
      setMessages([]);
    }
    paramHandled.current = true;
    if (q) send(q);
  }, [hydrated, loadId, q]);

  useEffect(() => {
    if (!hydrated) return;
    saveToStorage(storageKey(activeThreadId.current), messages);
  }, [messages, hydrated]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  function handleInputChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  // Basit client-side ürün arama tespiti — adımları gösterip göstermeyeceğimize karar verir
  function looksLikeProductSearch(text: string): boolean {
    const t = text.toLowerCase();
    const productHints = [
      "öner", "arıyorum", "satın", "hediye", "almak", "lazım",
      "ucuz", "uygun", "fiyat", "ürün", "laptop", "telefon",
      "bilgisayar", "kulaklık", "tablet", "saat", "ayakkabı",
      "tv", "kamera", "klavye", "mouse", "monitör", "şarj",
      "iphone", "samsung", "xiaomi", "apple", "huawei", "sony",
      "alternatif", "karşılaştır", "indirim",
    ];
    return productHints.some((kw) => t.includes(kw));
  }

  async function send(text: string) {
    if (!text.trim() || sending) return;
    setInput("");
    if (inputRef.current) inputRef.current.style.height = "auto";
    setMessages((prev) => [...prev, { role: "user", text }]);
    setSending(true);
    setProductSteps([]);

    const sendingThreadId = activeThreadId.current;
    const isLikelyProduct = looksLikeProductSearch(text);

    try {
      const apiPromise = chatApi.send(text, sendingThreadId) as Promise<ChatResponse>;

      let stepsDone = false;
      let stepIndex = 0;
      const STEP_INTERVAL = 3800;

      if (isLikelyProduct) {
        // Adımları hemen başlat, 3 nokta gösterme
        setSending(false);
        setProductSteps([PRODUCT_SEARCH_STEPS[0]]);

        const advanceStep = () => {
          if (stepsDone) return;
          stepIndex++;
          setProductSteps(PRODUCT_SEARCH_STEPS.slice(0, stepIndex + 1));
          if (stepIndex < PRODUCT_SEARCH_STEPS.length - 1) {
            stepTimerRef.current = setTimeout(advanceStep, STEP_INTERVAL);
          }
        };
        stepTimerRef.current = setTimeout(advanceStep, STEP_INTERVAL);
      }
      // isLikelyProduct === false ise sending=true kalır → TypingIndicator (3 nokta) görünür

      // API cevabını bekle
      const data = await apiPromise;
      stepsDone = true;
      if (stepTimerRef.current) clearTimeout(stepTimerRef.current);

      const returnedConvId = data.conversation_id ?? null;
      if (!sendingThreadId && returnedConvId) {
        const oldKey = storageKey(null);
        const newKey = storageKey(returnedConvId);
        try {
          const existing = sessionStorage.getItem(oldKey);
          if (existing) {
            sessionStorage.setItem(newKey, existing);
            sessionStorage.removeItem(oldKey);
          }
        } catch { }
        activeThreadId.current = returnedConvId;
        router.replace(`/chat?load=${returnedConvId}`, { scroll: false });
      }

      if (!data.is_product_request) {
        setProductSteps([]);
        setMessages((prev) => [...prev, {
          role: "bot",
          text: data.reply || "Başka bir konuda yardımcı olabilir miyim?",
        }]);
        return;
      }

      // Ürün araması — kalan adımları hızlıca tikle, sonra sonuçları göster
      for (let i = stepIndex + 1; i <= PRODUCT_SEARCH_STEPS.length; i++) {
        setProductSteps(PRODUCT_SEARCH_STEPS.slice(0, i));
        await new Promise((r) => setTimeout(r, 280));
      }
      await new Promise((r) => setTimeout(r, 350));
      setProductSteps([]);

      const newMsgs: Msg[] = [];
      if (data.recommendation?.summary)
        newMsgs.push({ role: "bot", text: data.recommendation.summary, budgetStatus: data.budget_status });

      const hasProducts = (data.products?.length ?? 0) > 0;
      const hasOverBudget = (data.over_budget_products?.length ?? 0) > 0;

      if (hasProducts || hasOverBudget) {
        newMsgs.push({
          role: "products",
          products: data.products ?? [],
          overBudgetProducts: data.over_budget_products ?? [],
          topPick: data.recommendation?.top_pick ?? null,
          advice: data.recommendation?.financial_advice ?? undefined,
        });
      } else {
        newMsgs.push({ role: "bot", text: "Ürün bulunamadı, farklı bir arama deneyin." });
      }
      setMessages((prev) => [...prev, ...newMsgs]);
    } catch (err: unknown) {
      const raw = err instanceof Error ? err.message : "Bir hata oluştu.";
      const msg =
        raw.toLowerCase().includes("güvenlik") ||
          raw.toLowerCase().includes("moderasyon") ||
          raw.toLowerCase().includes("mesajınız")
          ? raw
          : raw.startsWith("4") || raw.startsWith("5")
            ? "Şu an yanıt veremiyorum, lütfen tekrar dene."
            : raw;
      setMessages((prev) => [...prev, { role: "bot", text: `⚠️ ${msg}` }]);
    } finally {
      if (stepTimerRef.current) clearTimeout(stepTimerRef.current);
      setSending(false);
      setProductSteps([]);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }

  async function deleteHistory() {
    if (!confirm("Tüm geçmiş silinecek. Emin misin?")) return;
    try {
      await chatApi.deleteHistory();
      Object.keys(sessionStorage)
        .filter((k) => k.startsWith("finshop_thread_v2_"))
        .forEach((k) => sessionStorage.removeItem(k));
      setMessages(WELCOME);
      window.location.href = "/chat";
    } catch {
      alert("Geçmiş silinirken hata oluştu.");
    }
  }

  const isEmpty = messages.length === 0 && !sending && !loadingThread;

  if (loading) return (
    <div className="flex h-screen items-center justify-center" style={{ background: "var(--bg-mesh)" }}>
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg-mesh)" }}>
      <Sidebar userName={user?.full_name} userEmail={user?.email} />

      <div className="flex flex-col flex-1 min-w-0">

        {/* ── Top Bar ── */}
        <header className="flex items-center justify-between px-5 py-2.5 border-b border-gray-200/60 dark:border-gray-700/60 flex-shrink-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl">
          {/* Sol: Model selector */}
          <div className="relative" ref={modelMenuRef}>
            <button
              onClick={() => setModelMenuOpen((p) => !p)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors group"
            >
              <span className="text-sm font-semibold text-gray-800 dark:text-gray-100">FinShop AI</span>
              <span className="text-xs text-gray-400 dark:text-gray-500 font-medium">1.0</span>
              <ChevronDown className={`w-3.5 h-3.5 text-gray-400 transition-transform duration-200 ${modelMenuOpen ? "rotate-180" : ""}`} />
            </button>

            <AnimatePresence>
              {modelMenuOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -6, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -6, scale: 0.97 }}
                  transition={{ duration: 0.15 }}
                  className="absolute top-full left-0 mt-1.5 w-56 bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-700 rounded-2xl shadow-xl overflow-hidden z-50"
                >
                  <div className="p-2 space-y-0.5">
                    <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-blue-50 dark:bg-blue-900/30">
                      <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Sparkles className="w-3.5 h-3.5 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-gray-800 dark:text-gray-100">FinShop AI 1.0</p>
                        <p className="text-[10px] text-blue-600 dark:text-blue-400">Aktif model</p>
                      </div>
                      <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full flex-shrink-0" />
                    </div>
                    <div className="px-3 py-2 opacity-40 pointer-events-none">
                      <p className="text-xs font-medium text-gray-600 dark:text-gray-400">FinShop AI 2.0</p>
                      <p className="text-[10px] text-gray-400">Yakında</p>
                    </div>
                  </div>
                  <div className="border-t border-gray-100 dark:border-gray-700 px-3 py-2.5">
                    <p className="text-[10px] text-gray-400 leading-relaxed">Manus + Gemini altyapısı üzerinde çalışır. Ürün araştırması ve finansal öneriler için optimize edilmiştir.</p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Sağ: Kredi + Geçmişi Sil */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
              <Zap className="w-3.5 h-3.5 text-gray-400" />
              <span className="text-xs font-medium text-gray-400 dark:text-gray-500">Kredi — Yakında</span>
            </div>
            <button
              onClick={deleteHistory}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-colors border border-red-100 dark:border-red-900/40"
            >
              <Trash2 className="w-3.5 h-3.5" />
              {t("chat.deleteHistory")}
            </button>
          </div>
        </header>

        {/* ── Mesajlar ── */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">

            {/* Welcome hero */}
            <AnimatePresence>
              {isEmpty && (
                <motion.div
                  key="welcome-hero"
                  className="flex flex-col items-center justify-center pt-20 pb-8 gap-6"
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12, scale: 0.97 }}
                  transition={{ duration: 0.4 }}
                >
                  <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-3xl flex items-center justify-center shadow-lg">
                    <Sparkles className="w-10 h-10 text-white" />
                  </div>
                  <div className="text-center space-y-2">
                    <h2 className="text-3xl font-bold text-gray-900 dark:text-gray-100">{t("chat.heroQuestion")}</h2>
                    <p className="text-sm text-gray-400 dark:text-gray-500">{t("chat.heroSubtitle")}</p>
                  </div>

                  <div className="flex flex-wrap gap-2 justify-center max-w-md mt-2">
                    {(t("chat.suggestions", { returnObjects: true }) as string[]).map((s) => (
                      <button
                        key={s}
                        onClick={() => send(s)}
                        className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-blue-300 dark:hover:border-blue-600 transition-all shadow-sm"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <AnimatePresence initial={false}>
              {messages.map((msg, i) => {
                if (msg.role === "user") return <UserBubble key={i} text={msg.text!} />;
                if (msg.role === "bot") return <BotBubble key={i} text={msg.text!} budgetStatus={msg.budgetStatus} />;
                if (msg.role === "products") return (
                  <ProductsMessage key={i} products={msg.products!} overBudgetProducts={msg.overBudgetProducts ?? []} topPick={msg.topPick} advice={msg.advice} />
                );
                return null;
              })}
            </AnimatePresence>

            <AnimatePresence>
              {sending && <TypingIndicator key="typing" />}
              {productSteps.length > 0 && (
                <ProductStepsIndicator key="steps" steps={productSteps} allSteps={PRODUCT_SEARCH_STEPS} />
              )}
            </AnimatePresence>
            {loadingThread && <ThreadSkeleton />}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* ── Input alanı ── */}
        <div className="px-4 pb-5 pt-3 flex-shrink-0 bg-white/60 dark:bg-gray-900/60 backdrop-blur-xl border-t border-gray-200/40 dark:border-gray-700/40">
          <div className="max-w-2xl mx-auto">
            <div className="relative bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm focus-within:border-blue-400 dark:focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-400/20 transition-all">
              <textarea
                ref={inputRef}
                rows={1}
                className="w-full bg-transparent text-sm text-gray-800 dark:text-gray-100 placeholder-gray-400 resize-none outline-none leading-normal px-4 pt-3.5 pb-12"
                placeholder={t("chat.placeholder")}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                disabled={sending}
                style={{ height: "auto", minHeight: "22px" }}
              />
              <div className="absolute bottom-3 right-3">
                <button
                  onClick={() => send(input)}
                  disabled={!input.trim() || sending}
                  className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg flex items-center justify-center transition-all active:scale-95 shadow-sm"
                >
                  <Send className="w-3.5 h-3.5 text-white" />
                </button>
              </div>
            </div>
            <p className="text-center text-xs text-gray-400/60 mt-2">
              {t("chat.disclaimer")}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ThreadSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {[75, 55, 80, 45, 65].map((w, i) => (
        <div key={i} className={`flex ${i % 2 === 0 ? "justify-start gap-3" : "justify-end"}`}>
          {i % 2 === 0 && (
            <div className="w-7 h-7 rounded-lg bg-gray-200 dark:bg-gray-700 flex-shrink-0 mt-1" />
          )}
          <div
            className="h-9 rounded-2xl bg-gray-200 dark:bg-gray-700"
            style={{ width: `${w}%`, maxWidth: "75%" }}
          />
        </div>
      ))}
    </div>
  );
}

function UserBubble({ text }: { text: string }) {
  return (
    <motion.div
      className="flex justify-end"
      initial={{ opacity: 0, y: 8, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.25 }}
    >
      <div className="max-w-[75%] bg-gradient-to-br from-blue-500 to-indigo-600 text-white rounded-2xl rounded-br-sm px-4 py-3 text-sm leading-relaxed shadow-sm">
        {text}
      </div>
    </motion.div>
  );
}

function BotBubble({ text, budgetStatus }: { text: string; budgetStatus?: string }) {
  const accent =
    budgetStatus === "healthy" ? "border-l-4 border-emerald-400 bg-emerald-50/80 dark:bg-emerald-900/20" :
      budgetStatus === "warning" ? "border-l-4 border-amber-400 bg-amber-50/80 dark:bg-amber-900/20" :
        budgetStatus === "critical" ? "border-l-4 border-red-400 bg-red-50/80 dark:bg-red-900/20" : "";
  return (
    <motion.div
      className="flex justify-start gap-3"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0 mt-1 shadow-sm">
        <Sparkles className="w-3.5 h-3.5 text-white" />
      </div>
      <div className={`max-w-[75%] rounded-2xl rounded-bl-sm px-4 py-3 text-sm leading-relaxed shadow-sm ${accent || "bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 text-gray-800 dark:text-gray-100"}`}>
        {text}
      </div>
    </motion.div>
  );
}

// Sadece sohbet/chitchat için — basit 3 nokta
function TypingIndicator() {
  return (
    <motion.div
      className="flex justify-start gap-3"
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 4 }}
      transition={{ duration: 0.2 }}
    >
      <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0 mt-1 shadow-sm">
        <Sparkles className="w-3.5 h-3.5 text-white" />
      </div>
      <div className="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="w-1.5 h-1.5 bg-blue-400 rounded-full inline-block"
            animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
            transition={{ duration: 1.1, repeat: Infinity, delay: i * 0.18, ease: "easeInOut" }}
          />
        ))}
      </div>
    </motion.div>
  );
}

// Sadece ürün araması için — adımlı şeffaf geçiş
function ProductStepsIndicator({ steps, allSteps }: { steps: string[]; allSteps: string[] }) {
  return (
    <motion.div
      className="flex justify-start gap-3"
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 4 }}
      transition={{ duration: 0.2 }}
    >
      <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0 mt-1 shadow-sm">
        <Sparkles className="w-3.5 h-3.5 text-white" />
      </div>
      <div className="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm space-y-1.5 min-w-[220px]">
        <AnimatePresence initial={false}>
          {allSteps.map((step, index) => {
            const isVisible = index < steps.length;
            const isDone = index < steps.length - 1;
            const isCurrent = index === steps.length - 1;
            if (!isVisible) return null;
            return (
              <motion.div
                key={step}
                className="flex items-center gap-2.5"
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
              >
                <div className="w-4 h-4 flex items-center justify-center flex-shrink-0">
                  {isDone && (
                    <motion.span
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ duration: 0.2 }}
                      className="text-emerald-500 font-bold text-sm leading-none"
                    >✓</motion.span>
                  )}
                  {isCurrent && (
                    <motion.div
                      animate={{ scale: [1, 1.15, 1], opacity: [0.7, 1, 0.7] }}
                      transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
                    >
                      <Sparkles className="w-3.5 h-3.5 text-blue-500" />
                    </motion.div>
                  )}
                </div>
                <span className={`text-xs leading-tight ${isDone ? "text-gray-400 dark:text-gray-500" : "text-gray-700 dark:text-gray-200 font-medium"}`}>
                  {step}
                </span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

function ProductsMessage({ products, overBudgetProducts, topPick, advice }: {
  products: Product[];
  overBudgetProducts?: Product[];
  topPick?: { product_name: string; reason: string; value_score: number } | null;
  advice?: string;
}) {
  const { t } = useTranslation();
  const hasAlternatives = products.length > 0;
  const hasOverBudget = (overBudgetProducts?.length ?? 0) > 0;

  return (
    <motion.div
      className="flex justify-start gap-3"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0 mt-1 shadow-sm">
        <Sparkles className="w-3.5 h-3.5 text-white" />
      </div>
      <div className="flex-1 max-w-[85%] space-y-3">
        {advice && (
          <div className="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-2xl rounded-bl-sm px-4 py-3 text-sm text-blue-600 dark:text-blue-400 font-medium shadow-sm">
            {advice}
          </div>
        )}
        {topPick && (
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/30 dark:to-indigo-900/30 border border-blue-200/60 dark:border-blue-700/40 rounded-2xl px-4 py-3 shadow-sm">
            <span className="text-xs font-bold text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/50 px-2 py-0.5 rounded-full">EN İYİ SEÇİM</span>
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-100 mt-2">{topPick.product_name}</p>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{topPick.reason}</p>
            <p className="text-xs text-blue-500 mt-1 font-numeric">Değer puanı: {topPick.value_score}/10</p>
          </div>
        )}

        {hasAlternatives && (
          <div className="space-y-2">
            <p className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold px-1">
              {t("chat.budgetMatches", { count: products.length })}
            </p>
            {products.map((product, i) => <ProductCard key={i} product={product} />)}
          </div>
        )}

        {hasOverBudget && (
          <div className="space-y-2">
            <p className="text-xs text-amber-600 dark:text-amber-400 font-semibold px-1">
              {t("chat.overBudget", { count: overBudgetProducts!.length })}
            </p>
            {overBudgetProducts!.map((product, i) => (
              <ProductCard key={`ob-${i}`} product={product} overBudget />
            ))}
          </div>
        )}

        {!hasAlternatives && !hasOverBudget && (
          <p className="text-xs text-gray-400 font-medium px-1">Ürün bulunamadı</p>
        )}
      </div>
    </motion.div>
  );
}

function ProductCard({ product, overBudget }: { product: Product; overBudget?: boolean }) {
  const [starred, setStarred] = useState(false);
  const [popping, setPopping] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setStarred(wishlistService.isStarred(product.name));
  }, [product.name]);

  async function handleStar(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (loading) return;
    setLoading(true);
    setPopping(true);
    setTimeout(() => setPopping(false), 500);

    try {
      if (starred) {
        const items = await wishlistService.getAll();
        const item = items.find((i) => i.product_name === product.name);
        if (item) await wishlistService.remove(item.id);
        setStarred(false);
        toast("Takipten çıkarıldı", { icon: "☆" });
      } else {
        await wishlistService.add({
          name: product.name,
          price: product.price,
          url: product.url,
          image_url: product.image_url,
          seller: product.seller,
        });
        setStarred(true);
        toast.success("Takip listesine eklendi! Fiyatı düşünce haber vereceğiz 🔔");
      }
    } catch {
      toast.error("Bir hata oluştu, tekrar dene.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative">
      {overBudget && (
        <div className="absolute -top-1.5 left-3 z-10 bg-amber-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-sm">
          Bütçeni Aşıyor
        </div>
      )}
      <motion.a
        href={product.url}
        target="_blank"
        rel="noopener noreferrer"
        className={`flex gap-3 rounded-2xl p-3 transition-all group border ${overBudget
          ? "bg-amber-50 dark:bg-amber-900/20 border-amber-200/60 dark:border-amber-700/40 hover:border-amber-300"
          : "bg-white dark:bg-gray-800 border-gray-100 dark:border-gray-700 hover:border-blue-200 dark:hover:border-blue-700 hover:shadow-md"
          }`}
        whileHover={{ y: -2 }}
        transition={{ duration: 0.15 }}
      >
        {product.image_url ? (
          <div className="relative w-16 h-16 flex-shrink-0 rounded-xl overflow-hidden bg-gray-100">
            <Image src={product.image_url} alt={product.name} fill className="object-cover" unoptimized />
          </div>
        ) : (
          <div className="w-16 h-16 rounded-xl bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
            <ShoppingBag className="w-6 h-6 text-blue-400" />
          </div>
        )}
        <div className="flex-1 min-w-0 pr-8">
          <p className="text-sm font-medium text-gray-800 dark:text-gray-100 line-clamp-2 leading-snug group-hover:text-blue-700 dark:group-hover:text-blue-400 transition-colors">{product.name}</p>
          <p className="text-base font-bold text-blue-600 dark:text-blue-400 mt-1 font-numeric">{formatPrice(product.price)}</p>
          <div className="flex items-center gap-2 mt-0.5">
            <p className="text-xs text-gray-400">{product.seller}</p>
            {product.rating > 0 && <p className="text-xs text-amber-500">★ {product.rating}</p>}
          </div>
          {product.recommendation_reason && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1.5 line-clamp-1">{product.recommendation_reason}</p>
          )}
        </div>
      </motion.a>

      <button
        onClick={handleStar}
        disabled={loading}
        className="absolute top-2.5 right-2.5 z-10 p-1.5 rounded-full bg-white dark:bg-gray-900 hover:bg-yellow-50 dark:hover:bg-yellow-900/30 transition-all shadow-sm border border-gray-100 dark:border-gray-700"
        title={starred ? "Takipten çıkar" : "Fiyat takibine al"}
      >
        <Star
          className={[
            "w-4 h-4 transition-all duration-200",
            popping ? "animate-star-pop" : "",
            starred ? "fill-yellow-400 text-yellow-400 drop-shadow-star" : "text-gray-400 hover:text-yellow-400",
          ].join(" ")}
        />
      </button>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={null}>
      <ChatPageInner />
    </Suspense>
  );
}
