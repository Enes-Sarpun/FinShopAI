"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { chatApi, authApi } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import type { ChatHistory } from "@/types";
import Sidebar from "@/app/dashboard/components/Sidebar";

interface UserInfo { full_name?: string; email?: string; }

export default function HistoryPage() {
  const { loading } = useAuth();
  const [history, setHistory] = useState<ChatHistory[]>([]);
  const [fetching, setFetching] = useState(true);
  const [user, setUser] = useState<UserInfo | null>(null);

  useEffect(() => {
    authApi.me().then((d) => setUser(d as UserInfo)).catch(() => {});
    chatApi.getHistory(30)
      .then((data: unknown) => {
        const d = data as { history: ChatHistory[] };
        setHistory(d.history || []);
      })
      .finally(() => setFetching(false));
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar userName={user?.full_name} userEmail={user?.email} />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-6 py-8">
          {loading || fetching ? (
            <div className="flex justify-center py-20">
              <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <>
              <h1 className="font-bold text-gray-900 text-xl mb-6">Geçmiş Aramalar</h1>

              {history.length === 0 ? (
                <div className="card text-center py-10">
                  <p className="text-gray-500 mb-4">Henüz arama yapılmamış.</p>
                  <Link href="/chat" className="btn-primary">İlk Aramayı Yap</Link>
                </div>
              ) : (
                <div className="space-y-2">
                  {history.map((item) => (
                    <div key={item.id} className="card flex items-start justify-between gap-4 py-3.5">
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
                      <div className="flex items-center gap-3 flex-shrink-0">
                        <Link href={`/chat?load=${item.id}`}
                          className="text-xs text-blue-600 hover:underline">
                          Görüntüle
                        </Link>
                        <Link href={`/chat?q=${encodeURIComponent(item.message)}`}
                          className="text-xs text-gray-400 hover:text-gray-600 hover:underline">
                          Tekrar Ara
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
