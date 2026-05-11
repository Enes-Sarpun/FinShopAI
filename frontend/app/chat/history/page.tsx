"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { chatApi, authApi } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import type { ChatHistory } from "@/types";

export default function HistoryPage() {
  const { loading } = useAuth();
  const [history, setHistory] = useState<ChatHistory[]>([]);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    chatApi.getHistory(30)
      .then((data: unknown) => {
        const d = data as { history: ChatHistory[] };
        setHistory(d.history || []);
      })
      .finally(() => setFetching(false));
  }, []);

  if (loading || fetching) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-100 px-6 py-4 flex justify-between items-center">
        <Link href="/dashboard" className="font-bold text-gray-900 text-lg">FinShop AI</Link>
        <div className="flex items-center gap-4">
          <Link href="/chat" className="btn-primary text-sm py-2 px-4">Yeni Arama</Link>
          <button onClick={authApi.logout} className="text-sm text-gray-500 hover:text-gray-700">Çıkış</button>
        </div>
      </nav>

      <div className="max-w-2xl mx-auto px-4 py-8">
        <h1 className="font-bold text-gray-900 text-xl mb-6">Geçmiş Aramalar</h1>

        {history.length === 0 ? (
          <div className="card text-center py-10">
            <p className="text-gray-500 mb-4">Henüz arama yapılmamış.</p>
            <Link href="/chat" className="btn-primary">İlk Aramayı Yap</Link>
          </div>
        ) : (
          <div className="space-y-3">
            {history.map((item) => (
              <div key={item.id} className="card flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-800 font-medium truncate">{item.message}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(item.created_at).toLocaleDateString("tr-TR", {
                      day: "numeric", month: "long", hour: "2-digit", minute: "2-digit"
                    })}
                  </p>
                  {item.metadata && (item.metadata as { product_count?: number }).product_count !== undefined && (
                    <p className="text-xs text-blue-500 mt-1">
                      {(item.metadata as { product_count: number }).product_count} ürün bulundu
                    </p>
                  )}
                </div>
                <Link
                  href={`/chat?q=${encodeURIComponent(item.message)}`}
                  className="text-xs text-blue-600 hover:underline flex-shrink-0"
                >
                  Tekrar Ara
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
