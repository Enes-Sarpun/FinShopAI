"use client";
import Link from "next/link";
import { authApi } from "@/lib/api";

// GÖREV: SEN
// Bu component sayfanın üst navigasyon çubuğu.
// Yapılabilecekler:
//   - Logo/ikon ekle
//   - Kullanıcı adını göster (props olarak al)
//   - Mobil hamburger menü ekle
//   - Aktif sayfayı highlight et

interface NavbarProps {
  userName?: string;
}

export default function Navbar({ userName }: NavbarProps) {
  return (
    <nav className="bg-white border-b border-gray-100 px-6 py-4 flex justify-between items-center">
      <h1 className="font-bold text-gray-900 text-lg">FinShop AI</h1>
      <div className="flex items-center gap-4">
        {userName && <span className="text-sm text-gray-500">Merhaba, {userName}</span>}
        <Link href="/chat" className="btn-primary text-sm py-2 px-4">Alışverişe Başla</Link>
        <button onClick={authApi.logout} className="text-sm text-gray-500 hover:text-gray-700">Çıkış</button>
      </div>
    </nav>
  );
}
