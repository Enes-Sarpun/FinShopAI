"use client";
import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { Send, Sparkles, ShoppingBag, ExternalLink } from "lucide-react";
import { chatApi } from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import type { ChatResponse, Product } from "@/types";

const STORAGE_KEY = "finshop_chat_messages";

const SUGGESTIONS = [
  "Anneme 1500 TL hediye öner 🎁",
  "Uygun fiyatlı laptop arıyorum 💻",
  "Mutfak için pratik ürünler 🍳",
];

type MsgRole = "user" | "bot" | "products";

interface Msg {
  role: MsgRole;
  text?: string;
  products?: Product[];
  advice?: string;
}

const WELCOME: Msg[] = [
  { role: "bot", text: "Merhaba! Bütçene uygun ürünler bulmana yardım edebilirim 🛍️" },
  { role: "bot", text: "Ne aramak istersin?" },
];

function loadMessages(): Msg[] {
  if (typeof window === "undefined") return WELCOME;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return WELCOME;
    const parsed = JSON.parse(raw) as Msg[];
    return parsed.length > 0 ? parsed : WELCOME;
  } catch {
    return WELCOME;
  }
}

function saveMessages(msgs: Msg[]) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(msgs));
  } catch {}
}

export default function ChatPreview() {
  const [messages, setMessages] = useState<Msg[]>(WELCOME);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // sessionStorage'dan yükle (client-side only)
  useEffect(() => {
    setMessages(loadMessages());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated) saveMessages(messages);
  }, [messages, hydrated]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(text: string) {
    if (!text.trim() || loading) return;
    setInput("");
    const userMsg: Msg = { role: "user", text };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const data = await chatApi.send(text) as ChatResponse;

      // Sohbet modu — sadece reply göster
      if (!data.is_product_request) {
        const reply = data.reply || "Başka bir konuda yardımcı olabilir miyim?";
        setMessages((prev) => [...prev, { role: "bot", text: reply }]);
        return;
      }

      // Ürün arama modu
      if (data.affordability_message) {
        setMessages((prev) => [...prev, { role: "bot", text: data.affordability_message! }]);
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
        setMessages((prev) => [...prev, { role: "bot", text: "Ürün bulunamadı, farklı bir arama deneyin." }]);
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
    sessionStorage.removeItem(STORAGE_KEY);
  }

  const isWelcomeOnly = messages.length === WELCOME.length &&
    messages.every((m, i) => m.text === WELCOME[i]?.text);

  return (
    <div className="card flex flex-col h-[600px] p-0 overflow-hidden">

      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100 bg-white">
        <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center flex-shrink-0">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-gray-900">FinShop Asistanı</p>
          <p className="text-xs text-green-500 font-medium flex items-center gap-1">
            <span className="w-1.5 h-1.5 bg-green-500 rounded-full inline-block" />
            Çevrimiçi
          </p>
        </div>
        <div className="flex items-center gap-3">
          {!isWelcomeOnly && (
            <button
              onClick={clearChat}
              className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
            >
              Temizle
            </button>
          )}
          <Link
            href="/chat"
            className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1 transition-colors"
          >
            Tam ekran <ExternalLink className="w-3 h-3" />
          </Link>
        </div>
      </div>

      {/* Mesajlar */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 bg-gray-50">

        {messages.map((msg, i) => {
          if (msg.role === "user") {
            return (
              <div key={i} className="flex justify-end">
                <div className="bubble-user">{msg.text}</div>
              </div>
            );
          }

          if (msg.role === "bot") {
            return (
              <div key={i} className="flex justify-start">
                <div className="bubble-bot">{msg.text}</div>
              </div>
            );
          }

          if (msg.role === "products") {
            return (
              <div key={i} className="space-y-2">
                {msg.advice && (
                  <div className="flex justify-start">
                    <div className="bubble-bot text-blue-600 font-medium">{msg.advice}</div>
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
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Öneri butonları — sadece ilk açılışta */}
      {isWelcomeOnly && !loading && (
        <div className="px-4 py-2 flex flex-col gap-1.5 bg-gray-50 border-t border-gray-100">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="text-left text-xs text-blue-600 bg-white hover:bg-blue-50 border border-blue-100 rounded-xl px-3 py-2 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="flex gap-2 px-4 py-3 border-t border-gray-100 bg-white"
      >
        <input
          type="text"
          className="input flex-1 text-sm py-2"
          placeholder="Ne arıyorsun?"
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
      className="flex items-center gap-3 bg-white border border-gray-100 rounded-2xl p-3 hover:shadow-md transition-shadow group"
    >
      {product.image_url ? (
        <img
          src={product.image_url}
          alt={product.name}
          className="w-12 h-12 rounded-xl object-cover flex-shrink-0 bg-gray-100"
        />
      ) : (
        <div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
          <ShoppingBag className="w-5 h-5 text-blue-400" />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-gray-800 line-clamp-2 leading-snug">{product.name}</p>
        <p className="text-sm font-bold text-blue-600 mt-0.5">{formatPrice(product.price)}</p>
        {product.rating > 0 && (
          <p className="text-xs text-yellow-500">★ {product.rating}</p>
        )}
      </div>
      <ExternalLink className="w-3.5 h-3.5 text-gray-300 group-hover:text-blue-400 transition-colors flex-shrink-0" />
    </a>
  );
}
