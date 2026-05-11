"use client";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { authApi } from "@/lib/api";
import { useEffect, useState } from "react";
import Sidebar from "@/app/dashboard/components/Sidebar";
import { User, Wallet, Brain, Bell, Shield, ChevronRight, LogOut, LucideIcon } from "lucide-react";

interface UserInfo { full_name?: string; email?: string; }
interface SettingsItem { href: string; icon: LucideIcon; label: string; desc: string; disabled?: boolean; }

const SETTINGS_SECTIONS: { title: string; items: SettingsItem[] }[] = [
  {
    title: "Hesap",
    items: [
      { href: "/settings/account", icon: User, label: "Hesap Bilgileri", desc: "İsim, e-posta ve şifre" },
    ],
  },
  {
    title: "Finansal Profil",
    items: [
      { href: "/onboarding/budget", icon: Wallet, label: "Bütçe Ayarları", desc: "Gelir, gider ve tasarruf hedefini güncelle" },
      { href: "/onboarding/personality", icon: Brain, label: "Kişilik Testi", desc: "Harcama profilini yenile" },
    ],
  },
  {
    title: "Uygulama",
    items: [
      { href: "#", icon: Bell, label: "Bildirimler", desc: "Yakında", disabled: true },
      { href: "#", icon: Shield, label: "Gizlilik", desc: "Yakında", disabled: true },
    ],
  },
];

export default function SettingsPage() {
  const { loading } = useAuth();
  const [user, setUser] = useState<UserInfo | null>(null);

  useEffect(() => {
    authApi.me().then((d) => setUser(d as UserInfo)).catch(() => {});
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar userName={user?.full_name} userEmail={user?.email} />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-6 py-8">
          <h1 className="text-xl font-bold text-gray-900 mb-6">Ayarlar</h1>

          {loading ? (
            <div className="flex justify-center py-20">
              <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="space-y-6">
              {SETTINGS_SECTIONS.map((section) => (
                <div key={section.title}>
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 px-1">
                    {section.title}
                  </p>
                  <div className="card p-0 overflow-hidden">
                    {section.items.map((item, i) => {
                      const Icon = item.icon;
                      const isLast = i === section.items.length - 1;
                      return (
                        <Link key={item.href} href={item.href}
                          className={`flex items-center gap-4 px-5 py-4 hover:bg-gray-50 transition-colors group ${
                            item.disabled ? "pointer-events-none opacity-50" : ""
                          } ${!isLast ? "border-b border-gray-100" : ""}`}>
                          <div className="w-9 h-9 bg-gray-100 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:bg-blue-50 transition-colors">
                            <Icon className="w-4 h-4 text-gray-500 group-hover:text-blue-600 transition-colors" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-800">{item.label}</p>
                            <p className="text-xs text-gray-400 mt-0.5">{item.desc}</p>
                          </div>
                          <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-gray-400 flex-shrink-0" />
                        </Link>
                      );
                    })}
                  </div>
                </div>
              ))}

              <div>
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 px-1">Oturum</p>
                <div className="card p-0 overflow-hidden">
                  <button onClick={authApi.logout}
                    className="w-full flex items-center gap-4 px-5 py-4 hover:bg-red-50 transition-colors group">
                    <div className="w-9 h-9 bg-gray-100 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:bg-red-100 transition-colors">
                      <LogOut className="w-4 h-4 text-gray-500 group-hover:text-red-500 transition-colors" />
                    </div>
                    <div className="flex-1 text-left">
                      <p className="text-sm font-medium text-gray-800 group-hover:text-red-500 transition-colors">Çıkış Yap</p>
                      <p className="text-xs text-gray-400 mt-0.5">Oturumu sonlandır</p>
                    </div>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
