"use client";
import Sidebar from "@/app/dashboard/components/Sidebar";
import WishlistWidget from "@/app/dashboard/components/WishlistWidget";
import { useAuth } from "@/hooks/useAuth";
import { useEffect, useState } from "react";
import { authApi } from "@/lib/api";

interface UserInfo { full_name?: string; email?: string; }

export default function WatchlistPage() {
  const { loading } = useAuth();
  const [user, setUser] = useState<UserInfo | null>(null);

  useEffect(() => {
    authApi.me().then((u) => setUser(u as UserInfo)).catch(() => {});
  }, []);

  if (loading) return (
    <div className="flex h-screen items-center justify-center" style={{ background: "var(--bg-mesh)" }}>
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg-mesh)" }}>
      <Sidebar userName={user?.full_name} userEmail={user?.email} />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Takip Listesi</h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1 text-sm">
              Fiyatını takip ettiğiniz ürünler burada yer alır.
            </p>
          </div>
          <div className="w-full max-w-2xl">
            <WishlistWidget />
          </div>
        </div>
      </main>
    </div>
  );
}
