import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinShop AI — Cüzdanını Bilen Alışveriş Asistanı",
  description: "Finansal profiline göre kişiselleştirilmiş alışveriş önerileri",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body>{children}</body>
    </html>
  );
}
