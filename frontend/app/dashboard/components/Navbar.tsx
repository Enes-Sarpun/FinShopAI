"use client";
import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShoppingBag, Menu, X, LogOut, User, Settings, ChevronDown } from "lucide-react";
import { authApi } from "@/lib/api";

interface NavbarProps {
  userName?: string;
  userEmail?: string;
}

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/chat", label: "Asistan" },
  { href: "/chat/history", label: "Geçmiş" },
];

export default function Navbar({ userName, userEmail }: NavbarProps) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Dropdown dışına tıklayınca kapat
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const initials = userName
    ? userName.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2)
    : "?";

  return (
    <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur-sm border-b border-gray-100 px-6 py-3 transition-shadow">
      <div className="max-w-6xl mx-auto flex justify-between items-center">

        {/* Logo */}
        <Link href="/dashboard" className="flex items-center gap-2">
          <ShoppingBag className="w-5 h-5 text-blue-600" />
          <span className="font-bold text-gray-900">FinShop AI</span>
        </Link>

        {/* Desktop Nav */}
        <div className="hidden md:flex items-center gap-6">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`text-sm font-medium transition-colors ${
                pathname === link.href
                  ? "text-blue-600 border-b-2 border-blue-600 pb-0.5"
                  : "text-gray-500 hover:text-gray-900"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>

        {/* Sağ: Alışverişe Başla + Avatar Dropdown */}
        <div className="hidden md:flex items-center gap-3">
          <Link href="/chat" className="btn-primary text-sm py-2 px-4">
            Alışverişe Başla
          </Link>

          {/* Avatar dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen((p) => !p)}
              className="flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-xl hover:bg-gray-100 transition-colors"
            >
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-xs font-bold">
                {initials}
              </div>
              <ChevronDown className={`w-3.5 h-3.5 text-gray-400 transition-transform ${dropdownOpen ? "rotate-180" : ""}`} />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden z-50">
                {/* Kullanıcı bilgisi */}
                <div className="px-4 py-3 border-b border-gray-100">
                  <p className="text-sm font-semibold text-gray-800 truncate">{userName || "Kullanıcı"}</p>
                  <p className="text-xs text-gray-400 truncate mt-0.5">{userEmail || ""}</p>
                </div>

                {/* Menü öğeleri */}
                <div className="py-1.5">
                  <Link
                    href="/settings"
                    onClick={() => setDropdownOpen(false)}
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    <Settings className="w-4 h-4 text-gray-400" />
                    Ayarlar
                  </Link>
                  <Link
                    href="/settings/account"
                    onClick={() => setDropdownOpen(false)}
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    <User className="w-4 h-4 text-gray-400" />
                    Hesabım
                  </Link>
                </div>

                <div className="border-t border-gray-100 py-1.5">
                  <button
                    onClick={authApi.logout}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-500 hover:bg-red-50 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                    Çıkış Yap
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Mobil hamburger */}
        <button
          className="md:hidden text-gray-600 hover:text-gray-900"
          onClick={() => setMenuOpen((prev) => !prev)}
        >
          {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobil menü */}
      {menuOpen && (
        <div className="md:hidden mt-3 border-t border-gray-100 pt-3 flex flex-col gap-1 px-2">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setMenuOpen(false)}
              className={`text-sm font-medium px-3 py-2 rounded-xl transition-colors ${
                pathname === link.href ? "bg-blue-50 text-blue-600" : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              {link.label}
            </Link>
          ))}
          <div className="border-t border-gray-100 mt-2 pt-2 flex flex-col gap-1">
            <Link href="/settings" onClick={() => setMenuOpen(false)}
              className="flex items-center gap-3 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 rounded-xl">
              <Settings className="w-4 h-4 text-gray-400" /> Ayarlar
            </Link>
            <Link href="/settings/account" onClick={() => setMenuOpen(false)}
              className="flex items-center gap-3 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 rounded-xl">
              <User className="w-4 h-4 text-gray-400" /> Hesabım
            </Link>
            <button onClick={authApi.logout}
              className="flex items-center gap-3 px-3 py-2 text-sm text-red-500 hover:bg-red-50 rounded-xl">
              <LogOut className="w-4 h-4" /> Çıkış Yap
            </button>
          </div>
        </div>
      )}
    </nav>
  );
}
