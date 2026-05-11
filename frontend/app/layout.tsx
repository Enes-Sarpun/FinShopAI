import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Space_Grotesk } from "next/font/google";
import "./globals.css";

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-plus-jakarta",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-space-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: "FinShop AI — Cüzdanını Bilen Alışveriş Asistanı",
  description: "Finansal profiline göre kişiselleştirilmiş alışveriş önerileri",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" className={`${plusJakarta.variable} ${spaceGrotesk.variable}`}>
      <body className={plusJakarta.className}>
        {/* ── Pastel Blob + Şerit Arka Planı ── */}
        <div
          aria-hidden="true"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 0,
            overflow: "hidden",
            pointerEvents: "none",
          }}
        >
          {/* Kayan FinShop AI şeritleri */}
          <div className="global-stripe-bg">
            {Array.from({ length: 20 }).map((_, r) => (
              <div key={r} className="global-stripe-row">
                {Array.from({ length: 16 }).map((_, c) => (
                  <span key={c}>FinShop AI</span>
                ))}
              </div>
            ))}
          </div>

          {/* Blob 1 — indigo */}
          <div
            style={{
              position: "absolute",
              width: 400,
              height: 400,
              top: "10%",
              left: "5%",
              background: "radial-gradient(circle, rgba(99,102,241,0.25), transparent 70%)",
              filter: "blur(60px)",
              animation: "float1 40s infinite ease-in-out",
              willChange: "transform",
            }}
          />
          {/* Blob 2 — pembe */}
          <div
            style={{
              position: "absolute",
              width: 350,
              height: 350,
              bottom: "15%",
              right: "8%",
              background: "radial-gradient(circle, rgba(236,72,153,0.20), transparent 70%)",
              filter: "blur(60px)",
              animation: "float2 45s infinite ease-in-out reverse",
              willChange: "transform",
            }}
          />
          {/* Blob 3 — mor, ortalanmış dönen */}
          <div
            style={{
              position: "absolute",
              width: 300,
              height: 300,
              top: "50%",
              left: "50%",
              background: "radial-gradient(circle, rgba(168,85,247,0.15), transparent 70%)",
              filter: "blur(80px)",
              animation: "float3 50s infinite linear",
              willChange: "transform",
            }}
          />
        </div>

        {/* ── Ana İçerik ── */}
        <div style={{ position: "relative", zIndex: 1 }}>
          {children}
        </div>
      </body>
    </html>
  );
}
