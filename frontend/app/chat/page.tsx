"use client";
import { useState, useRef, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { chatApi, authApi } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { formatPrice } from "@/lib/utils";
import type { ChatResponse, Product } from "@/types";
import { Send, Sparkles, ShoppingBag, Trash2, Star } from "lucide-react";
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

const WELCOME: Msg[] = [
  { role: "bot", text: "Merhaba! Bütçene uygun ürünler bulmana yardım edebilirim 🛍️" },
  { role: "bot", text: "Ne aramak istersin? Örneğin: \"Babama Babalar Günü'ne özel bir hediye almak istiyorum, ne önerirsin?\"" },
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
  try { sessionStorage.setItem(key, JSON.stringify(msgs)); } catch {}
}

interface UserInfo { full_name?: string; email?: string; }

export default function ChatPage() {
  const { loading } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [messages, setMessages] = useState<Msg[]>(WELCOME);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [loadingThread, setLoadingThread] = useState(false);
  const [user, setUser] = useState<UserInfo | null>(null);
  // Aktif konuşmanın ID'si (backend metadata.conversation_id ile birebir).
  // URL'deki ?load=ID veya backend response'undan gelir.
  const activeThreadId = useRef<string | null>(null);
  const paramHandled = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    authApi.me().then((d) => setUser(d as UserInfo)).catch(() => {});
    setHydrated(true);
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
    const cached = loadFromStorage(storageKey(null));
    if (cached) setMessages(cached);
    paramHandled.current = true;
    if (q) send(q);
  // eslint-disable-next-line react-hooks/exhaustive-deps
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

  async function send(text: string) {
    if (!text.trim() || sending) return;
    setInput("");
    if (inputRef.current) inputRef.current.style.height = "auto";
    setMessages((prev) => [...prev, { role: "user", text }]);
    setSending(true);

    // Aktif sohbet ID'sini backend'e ilet — yoksa yeni sohbet açacak.
    const sendingThreadId = activeThreadId.current;

    try {
      const data = await chatApi.send(text, sendingThreadId) as ChatResponse;

      // İlk mesaj sonrası (yeni sohbet) backend'den conversation_id geliyor.
      // Bunu yakala, aktif thread olarak set et ve URL'i ?load=<id> ile güncelle.
      const returnedConvId = data.conversation_id ?? null;
      if (!sendingThreadId && returnedConvId) {
        const oldKey = storageKey(null);
        const newKey = storageKey(returnedConvId);
        // SessionStorage'daki "new" anahtarını conv ID'li anahtara taşı
        try {
          const existing = sessionStorage.getItem(oldKey);
          if (existing) {
            sessionStorage.setItem(newKey, existing);
            sessionStorage.removeItem(oldKey);
          }
        } catch {}
        activeThreadId.current = returnedConvId;
        // URL'i değiştirirken sayfayı yeniden yükleme — replace ile pushState
        router.replace(`/chat?load=${returnedConvId}`, { scroll: false });
      }

      if (!data.is_product_request) {
        setMessages((prev) => [...prev, {
          role: "bot",
          text: data.reply || "Başka bir konuda yardımcı olabilir miyim?",
        }]);
        return;
      }

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
      // Backend'den gelen teknik hata mesajlarını kullanıcı dostu hale getir
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
      setSending(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }

  function clearChat() {
    sessionStorage.removeItem(storageKey(activeThreadId.current));
    activeThreadId.current = null;
    setMessages(WELCOME);
    // URL'i temizle — yeni sohbet conversation_id olmadan başlasın
    router.replace("/chat", { scroll: false });
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

  if (loading) return (
    <div className="flex h-screen items-center justify-center" style={{ background: "var(--bg-mesh)" }}>
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg-mesh)" }}>
      <Sidebar userName={user?.full_name} userEmail={user?.email} />

      <div className="flex flex-col flex-1 min-w-0">

        {/* Üst bar — glassmorphism */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-white/60 dark:border-gray-700/60 flex-shrink-0 bg-white/75 dark:bg-gray-900/75 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-sm">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">FinShop Asistanı</p>
              <p className="text-xs text-emerald-500 flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full inline-block" />
                Çevrimiçi
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={clearChat}
              className="p-2 hover:bg-gray-100/80 dark:hover:bg-gray-700/50 rounded-xl transition-colors text-gray-400 hover:text-gray-600"
              title="Bu sohbeti temizle">
              <Trash2 className="w-4 h-4" />
            </button>
            <button onClick={deleteHistory}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-colors border border-red-100 dark:border-red-900/40">
              <Trash2 className="w-3.5 h-3.5" />
              Geçmişi Sil
            </button>
          </div>
        </header>

        {/* Mesajlar */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">
            {loadingThread ? (
              <ThreadSkeleton />
            ) : (
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
            )}
            {sending && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input */}
        <div className="border-t border-white/40 dark:border-gray-700/40 px-4 py-5 flex-shrink-0" style={{ background: "var(--bg-mesh)" }}>
          <div className="max-w-2xl mx-auto">
            <div className="flex items-center gap-3 border border-white/60 dark:border-gray-600/60 rounded-2xl px-4 py-3 focus-within:ring-2 focus-within:ring-blue-400/60 focus-within:border-blue-400/60 transition-all shadow-sm" style={{ background: "rgba(255,255,255,0.18)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)" }}>
              <textarea
                ref={inputRef}
                rows={1}
                className="flex-1 bg-transparent text-sm text-gray-800 dark:text-gray-100 placeholder-gray-400/80 resize-none outline-none leading-normal"
                placeholder="Bugün ne arıyoruz? Ürün, bütçe, hediye... 🛍️"
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                disabled={sending}
                style={{ height: "auto", minHeight: "22px" }}
              />
              <button onClick={() => send(input)} disabled={!input.trim() || sending}
                className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg flex items-center justify-center transition-all flex-shrink-0 shadow-sm active:scale-95">
                <Send className="w-3.5 h-3.5 text-white" />
              </button>
            </div>
            <p className="text-center text-xs text-gray-400/60 mt-2">
              FinShop AI hata yapabilir, yanıtlarını kontrol ediniz.
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
    budgetStatus === "warning"  ? "border-l-4 border-amber-400 bg-amber-50/80 dark:bg-amber-900/20" :
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
      <div className={`max-w-[75%] rounded-2xl rounded-bl-sm px-4 py-3 text-sm leading-relaxed shadow-sm ${accent || "bg-white/85 dark:bg-gray-800/85 border border-white/80 dark:border-gray-700/60 text-gray-800 dark:text-gray-100"}`}
        style={!accent ? { backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)" } : {}}>
        {text}
      </div>
    </motion.div>
  );
}

function TypingIndicator() {
  return (
    <motion.div
      className="flex justify-start gap-3"
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0 shadow-sm">
        <Sparkles className="w-3.5 h-3.5 text-white" />
      </div>
      <div className="bg-white/85 dark:bg-gray-800/85 border border-white/80 dark:border-gray-700/60 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm flex items-center gap-1.5"
        style={{ backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)" }}>
        {[0, 150, 300].map((delay, i) => (
          <span
            key={i}
            className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
            style={{ animationDelay: `${delay}ms` }}
          />
        ))}
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
          <div className="bg-white/85 dark:bg-gray-800/85 border border-white/80 dark:border-gray-700/60 rounded-2xl rounded-bl-sm px-4 py-3 text-sm text-blue-600 dark:text-blue-400 font-medium shadow-sm"
            style={{ backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)" }}>
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

        {/* Bütçeye uygun alternatifler */}
        {hasAlternatives && (
          <div className="space-y-2">
            <p className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold px-1">
              ✓ Bütçene uygun seçenekler ({products.length})
            </p>
            {products.map((product, i) => <ProductCard key={i} product={product} />)}
          </div>
        )}

        {/* Bütçeyi aşan orijinal ürünler */}
        {hasOverBudget && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 px-1">
              <span className="text-xs text-amber-600 dark:text-amber-400 font-semibold">
                ⚠️ Bütçeni aşan ürünler ({overBudgetProducts!.length})
              </span>
            </div>
            {overBudgetProducts!.map((product, i) => (
              <ProductCard key={`ob-${i}`} product={product} overBudget />
            ))}
          </div>
        )}

        {/* Ne alternatif ne over_budget yoksa */}
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
        className={`flex gap-3 rounded-2xl p-3 transition-all group ${overBudget
          ? "bg-amber-50/85 dark:bg-amber-900/20 border border-amber-200/60 dark:border-amber-700/40 hover:border-amber-300/60"
          : "bg-white/85 dark:bg-gray-800/85 border border-white/80 dark:border-gray-700/60 hover:shadow-glass-hover hover:border-blue-200/60 dark:hover:border-blue-700/40"
        }`}
        style={{ backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)" }}
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

      {/* Yıldız butonu — kartın dışında z-index ile üstte */}
      <button
        onClick={handleStar}
        disabled={loading}
        className="absolute top-2.5 right-2.5 z-10 p-1.5 rounded-full bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm hover:bg-yellow-50 dark:hover:bg-yellow-900/30 transition-all shadow-sm"
        title={starred ? "Takipten çıkar" : "Fiyat takibine al"}
      >
        <Star
          className={[
            "w-4 h-4 transition-all duration-200",
            popping ? "animate-star-pop" : "",
            starred
              ? "fill-yellow-400 text-yellow-400 drop-shadow-star"
              : "text-gray-400 hover:text-yellow-400",
          ].join(" ")}
        />
      </button>
    </div>
  );
}
