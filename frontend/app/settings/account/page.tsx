"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { authApi } from "@/lib/api";
import Navbar from "@/app/dashboard/components/Navbar";
import { User, Mail, ArrowLeft } from "lucide-react";
import Link from "next/link";

interface UserInfo {
  full_name?: string;
  email?: string;
}

export default function AccountPage() {
  const { loading } = useAuth();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    authApi.me()
      .then((data) => setUser(data as UserInfo))
      .catch(() => setUser(null))
      .finally(() => setFetching(false));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-2xl mx-auto px-4 py-8">

        {/* Geri */}
        <Link href="/settings" className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800 transition-colors mb-6">
          <ArrowLeft className="w-4 h-4" />
          Ayarlara Dön
        </Link>

        <h1 className="text-xl font-bold text-gray-900 mb-6">Hesap Bilgileri</h1>

        {loading || fetching ? (
          <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="space-y-4">

            {/* Avatar */}
            <div className="card flex items-center gap-5">
              <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center text-white text-xl font-bold flex-shrink-0">
                {user?.full_name
                  ? user.full_name.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2)
                  : "?"}
              </div>
              <div>
                <p className="font-semibold text-gray-900">{user?.full_name || "—"}</p>
                <p className="text-sm text-gray-400">{user?.email || "—"}</p>
              </div>
            </div>

            {/* Bilgiler */}
            <div className="card p-0 overflow-hidden">
              <div className="flex items-center gap-4 px-5 py-4 border-b border-gray-100">
                <div className="w-9 h-9 bg-gray-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-gray-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-400">Ad Soyad</p>
                  <p className="text-sm font-medium text-gray-800 mt-0.5">{user?.full_name || "—"}</p>
                </div>
              </div>

              <div className="flex items-center gap-4 px-5 py-4">
                <div className="w-9 h-9 bg-gray-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Mail className="w-4 h-4 text-gray-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-400">E-posta</p>
                  <p className="text-sm font-medium text-gray-800 mt-0.5">{user?.email || "—"}</p>
                </div>
              </div>
            </div>

            {/* Finansal profil kısayolları */}
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1 pt-2">
              Finansal Profilim
            </p>
            <div className="card p-0 overflow-hidden">
              <Link href="/onboarding/budget"
                className="flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors border-b border-gray-100 text-sm">
                <span className="font-medium text-gray-700">Bütçemi Güncelle</span>
                <span className="text-xs text-blue-600">Düzenle →</span>
              </Link>
              <Link href="/onboarding/personality"
                className="flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors text-sm">
                <span className="font-medium text-gray-700">Kişilik Testini Yenile</span>
                <span className="text-xs text-blue-600">Düzenle →</span>
              </Link>
            </div>

            {/* Bilgi notu */}
            <p className="text-xs text-gray-400 text-center px-4">
              Ad, e-posta ve şifre değiştirme özelliği yakında eklenecek.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
