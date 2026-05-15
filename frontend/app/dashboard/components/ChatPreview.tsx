"use client";
import { useState, useRef, useEffect, useMemo } from "react";
import Link from "next/link";
import { useTranslation } from "react-i18next";
import { Send, Sparkles, ShoppingBag, ExternalLink } from "lucide-react";
import { chatApi } from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import type { ChatResponse, Product } from "@/types";

const STORAGE_KEY = "finshop_chat_messages_v2";
// Geriye uyumluluk için ismi koruyoruz; içinde artık conversation_id saklanır.
const THREAD_KEY = "finshop_last_conversation_id_v2";

type MsgRole = "user" | "bot" | "products";

interface Msg {
  role: MsgRole;
  text?: string;
  tkey?: string;       // i18n key — runtime'da çevrilir
  products?: Product[];
  advice?: string;
}

function loadMessages(fallback: Msg[]): Msg[] {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw) as Msg[];
    if (parsed.length === 0) return fallback;
    // Eğer hiç user mesajı yoksa, eski (önceki dildeki) welcome'u taze WELCOME ile değiştir
    if (!parsed.some((m) => m.role === "user")) return fallback;
    return parsed;
  } catch {
    return fallback;
  }
}

function saveMessages(msgs: Msg[]) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(msgs));
  } catch {}
}

export default function ChatPreview() {
  const { t, i18n } = useTranslation();

  const WELCOME = useMemo<Msg[]>(() => [
    { role: "bot", tkey: "chatPreview.welcome1" },
    { role: "bot", tkey: "chatPreview.welcome2" },
  ], []);

  const SUGGESTIONS = useMemo(() => [
    t("chatPreview.suggestion1"),
    t("chatPreview.suggestion2"),
    t("chatPreview.suggestion3"),
  ], [t]);

  const [messages, setMessages] = useState<Msg[]>(WELCOME);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [lastMsgId, setLastMsgId] = useState<string | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // sessionStorage'dan yükle
  useEffect(() => {
    setMessages(loadMessages(WELCOME));
    const saved = sessionStorage.getItem(THREAD_KEY);
    if (saved) setLastMsgId(saved);
    setHydrated(true);
    // sadece ilk render'da; WELCOME değişse bile bu effect bir kez çalışmalı
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Dil değişince welcome ekranındaysa taze WELCOME'a sıçra (önbellekteki eski metni temizle)
  useEffect(() => {
    if (!hydrated) return;
    if (!messages.some((m) => m.role === "user")) {
      setMessages(WELCOME);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i18n.language, hydrated]);

  useEffect(() => {
    if (hydrated) saveMessages(messages);
  }, [messages, hydrated]);

  // Yeni mesaj geldiğinde chat'i kendi içinde en alta kaydır.
  // scrollIntoView yerine container'ın scrollTop'unu manuel set ediyoruz;
  // böylece tarayıcı dış (dashboard main) scroll'una dokunmaz.
  useEffect(() => {
    const c = scrollContainerRef.current;
    if (!c) return;
    c.scrollTo({ top: c.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send(text: string) {
    if (!text.trim() || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text }]);
    setLoading(true);

    try {
      // Aktif conversation_id'yi backend'e ilet — yoksa yeni sohbet açar
      const data = await chatApi.send(text, lastMsgId) as ChatResponse;

      // Backend'den dönen conversation_id'yi sakla (yeni sohbet ise ilk
      // mesaj sonrası dolar; sonraki mesajlar aynı sohbete eklenir).
      const convId = data.conversation_id || data.user_msg_id || null;
      if (convId) {
        setLastMsgId(convId);
        sessionStorage.setItem(THREAD_KEY, convId);
      }

      if (!data.is_product_request) {
        const reply = data.reply || t("chatPreview.errorFallback");
        setMessages((prev) => [...prev, { role: "bot", text: reply }]);
        return;
      }

      if (data.recommendation?.summary) {
        setMessages((prev) => [...prev, { role: "bot", text: data.recommendation.summary }]);
      }
      if (data.products?.length > 0) {
        setMessages((prev) => [
          ...prev,
          {
            role: "products",
            products: data.products.slice(0, 3),
            advice: data.recommendation?.financial_advice ?? undefined,
          },
        ]);
      } else {
        setMessages((prev) => [...prev, { role: "bot", text: t("chatPreview.noProducts") }]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Bir hata oluştu.";
      setMessages((prev) => [...prev, { role: "bot", text: `⚠️ ${msg}` }]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    send(input);
  }

  function clearChat() {
    setMessages(WELCOME);
    setLastMsgId(null);
    sessionStorage.removeItem(STORAGE_KEY);
    sessionStorage.removeItem(THREAD_KEY);
  }

  // Welcome ekranı: hiç user mesajı yoksa ve sadece bot karşılaması varsa
  const isWelcomeOnly = !messages.some((m) => m.role === "user");

  // "Tam ekran" linki: konuşma varsa son mesajı yükle, yoksa boş chat
  const fullscreenHref = lastMsgId ? `/chat?load=${lastMsgId}` : "/chat";

  return (
    <div className="card flex flex-col h-[600px] p-0 overflow-hidden">

      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100 dark:border-gray-700/60 bg-white/80 dark:bg-gray-900/60 backdrop-blur-sm">
        <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center flex-shrink-0">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{t("chatPreview.title")}</p>
          <p className="text-xs text-green-500 font-medium flex items-center gap-1">
            <span className="w-1.5 h-1.5 bg-green-500 rounded-full inline-block" />
            {t("common.online")}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {!isWelcomeOnly && (
            <button
              onClick={clearChat}
              className="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            >
              {t("chatPreview.clear")}
            </button>
          )}
          <Link
            href={fullscreenHref}
            className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 flex items-center gap-1 transition-colors"
          >
            {t("chatPreview.fullscreen")} <ExternalLink className="w-3 h-3" />
          </Link>
        </div>
      </div>

      {/* Mesajlar */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-3 bg-gray-50/60 dark:bg-gray-900/40"
      >

        {messages.map((msg, i) => {
          const text = msg.tkey ? t(msg.tkey) : msg.text;
          if (msg.role === "user") {
            return (
              <div key={i} className="flex justify-end">
                <div className="bubble-user">{text}</div>
              </div>
            );
          }

          if (msg.role === "bot") {
            return (
              <div key={i} className="flex justify-start">
                <div className="bubble-bot">{text}</div>
              </div>
            );
          }

          if (msg.role === "products") {
            return (
              <div key={i} className="space-y-2">
                {msg.advice && (
                  <div className="flex justify-start">
                    <div className="bubble-bot text-blue-600 dark:text-blue-400 font-medium">{msg.advice}</div>
                  </div>
                )}
                {msg.products?.map((p, j) => (
                  <MiniProductCard key={j} product={p} />
                ))}
              </div>
            );
          }

          return null;
        })}

        {/* Yazıyor animasyonu */}
        {loading && (
          <div className="flex justify-start">
            <div className="bubble-bot flex items-center gap-1.5 py-3">
              <span className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce [animation-delay:0ms]" />
              <span className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce [animation-delay:150ms]" />
              <span className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        )}

      </div>

      {/* Öneri butonları — sadece ilk açılışta */}
      {isWelcomeOnly && !loading && (
        <div className="px-4 py-2 flex flex-col gap-1.5 bg-gray-50/60 dark:bg-gray-900/40 border-t border-gray-100 dark:border-gray-700/60">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="text-left text-xs text-blue-600 dark:text-blue-300 bg-white/80 dark:bg-gray-800/60 hover:bg-blue-50 dark:hover:bg-blue-900/30 border border-blue-100 dark:border-blue-900/40 rounded-xl px-3 py-2 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="flex gap-2 px-4 py-3 border-t border-gray-100 dark:border-gray-700/60 bg-white/80 dark:bg-gray-900/60 backdrop-blur-sm"
      >
        <input
          type="text"
          className="input flex-1 text-sm py-2"
          placeholder={t("chatPreview.placeholder")}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="w-9 h-9 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 rounded-xl flex items-center justify-center transition-colors flex-shrink-0"
        >
          <Send className="w-4 h-4 text-white" />
        </button>
      </form>
    </div>
  );
}

function MiniProductCard({ product }: { product: Product }) {
  return (
    <a
      href={product.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-3 bg-white dark:bg-gray-800/70 border border-gray-100 dark:border-gray-700/60 rounded-2xl p-3 hover:shadow-md transition-shadow group"
    >
      {product.image_url ? (
        <img
          src={product.image_url}
          alt={product.name}
          className="w-12 h-12 rounded-xl object-cover flex-shrink-0 bg-gray-100 dark:bg-gray-700"
        />
      ) : (
        <div className="w-12 h-12 rounded-xl bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
          <ShoppingBag className="w-5 h-5 text-blue-400" />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-gray-800 dark:text-gray-100 line-clamp-2 leading-snug">{product.name}</p>
        <p className="text-sm font-bold text-blue-600 dark:text-blue-400 mt-0.5">{formatPrice(product.price)}</p>
        {product.rating > 0 && (
          <p className="text-xs text-yellow-500">★ {product.rating}</p>
        )}
      </div>
      <ExternalLink className="w-3.5 h-3.5 text-gray-300 dark:text-gray-600 group-hover:text-blue-400 transition-colors flex-shrink-0" />
    </a>
  );
}
