"use client";
import { useState } from "react";
import Link from "next/link";
import { chatApi, authApi } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { formatPrice } from "@/lib/utils";
import type { ChatResponse, Product } from "@/types";
import Image from "next/image";

export default function ChatPage() {
  const { loading } = useAuth();
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<ChatResponse | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
    setError("");
    setSending(true);
    setResult(null);
    try {
      const data = await chatApi.send(message) as ChatResponse;
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Bir hata oluştu");
    } finally {
      setSending(false);
    }
  }

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <nav className="bg-white border-b border-gray-100 px-6 py-4 flex justify-between items-center">
        <Link href="/dashboard" className="font-bold text-gray-900 text-lg">FinShop AI</Link>
        <div className="flex items-center gap-4">
          <Link href="/chat/history" className="text-sm text-gray-500 hover:text-gray-700">Geçmiş</Link>
          <button onClick={authApi.logout} className="text-sm text-gray-500 hover:text-gray-700">Çıkış</button>
        </div>
      </nav>

      <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        {/* Arama Kutusu */}
        <div className="card">
          <h1 className="text-lg font-semibold text-gray-800 mb-4">Alışveriş Asistanı</h1>
          <form onSubmit={handleSend} className="flex gap-3">
            <input
              type="text"
              className="input flex-1"
              placeholder="Örn: Anneme 1500 TL mutfak hediyesi öner"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              disabled={sending}
            />
            <button type="submit" className="btn-primary px-6" disabled={sending || !message.trim()}>
              {sending ? "..." : "Ara"}
            </button>
          </form>
        </div>

        {/* Yükleniyor */}
        {sending && (
          <div className="card text-center py-10">
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-gray-500 text-sm">Ürünler aranıyor, analiz yapılıyor...</p>
          </div>
        )}

        {error && <div className="card border-red-200 bg-red-50"><p className="text-red-600 text-sm">{error}</p></div>}

        {/* Sonuçlar */}
        {result && !sending && (
          <div className="space-y-4">
            {/* Affordability */}
            {result.affordability_message && (
              <div className={`card border-l-4 ${
                result.budget_status === "healthy" ? "border-green-500 bg-green-50" :
                result.budget_status === "warning" ? "border-yellow-500 bg-yellow-50" :
                "border-red-500 bg-red-50"
              }`}>
                <p className="text-sm font-medium">{result.affordability_message}</p>
              </div>
            )}

            {/* Recommendation Summary */}
            {result.recommendation?.summary && (
              <div className="card">
                <p className="text-sm text-gray-700">{result.recommendation.summary}</p>
                {result.recommendation.financial_advice && (
                  <p className="text-sm text-blue-600 mt-2 font-medium">{result.recommendation.financial_advice}</p>
                )}
              </div>
            )}

            {/* Top Pick */}
            {result.recommendation?.top_pick && (
              <div className="card border-2 border-blue-200 bg-blue-50">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-bold text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full">EN İYİ SEÇİM</span>
                </div>
                <p className="font-semibold text-gray-800">{result.recommendation.top_pick.product_name}</p>
                <p className="text-sm text-gray-600 mt-1">{result.recommendation.top_pick.reason}</p>
                <p className="text-xs text-blue-500 mt-2">Değer puanı: {result.recommendation.top_pick.value_score}/10</p>
              </div>
            )}

            {/* Ürün Listesi */}
            {result.products.length > 0 ? (
              <div className="space-y-3">
                <h2 className="font-semibold text-gray-800">Bulunan Ürünler ({result.products.length})</h2>
                {result.products.map((product, i) => (
                  <ProductCard key={i} product={product} />
                ))}
              </div>
            ) : (
              <div className="card text-center py-8">
                <p className="text-gray-500">Ürün bulunamadı. Farklı bir arama deneyin.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ProductCard({ product }: { product: Product }) {
  return (
    <div className="card flex gap-4">
      {product.image_url && (
        <div className="relative w-20 h-20 flex-shrink-0 rounded-lg overflow-hidden bg-gray-100">
          <Image
            src={product.image_url}
            alt={product.name}
            fill
            className="object-cover"
            unoptimized
          />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-800 text-sm leading-snug">{product.name}</p>
        <p className="text-blue-600 font-bold mt-1">{formatPrice(product.price)}</p>
        <p className="text-xs text-gray-500">{product.seller}</p>
        {product.rating > 0 && (
          <p className="text-xs text-yellow-600 mt-0.5">★ {product.rating}</p>
        )}
        {product.recommendation_reason && (
          <p className="text-xs text-gray-500 mt-2 line-clamp-2">{product.recommendation_reason}</p>
        )}
        <a
          href={product.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block mt-2 text-xs text-blue-600 hover:underline"
        >
          Ürüne Git →
        </a>
      </div>
    </div>
  );
}
