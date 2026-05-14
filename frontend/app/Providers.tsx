"use client";
import { ThemeProvider } from "@/lib/ThemeContext";
import { LangProvider } from "@/lib/LangContext";
import { Toaster } from "react-hot-toast";
import "@/lib/i18n";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <LangProvider>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              borderRadius: "14px",
              padding: "14px 18px",
              fontSize: "14px",
              boxShadow: "0 10px 40px rgba(0,0,0,0.12)",
            },
          }}
        />
      </LangProvider>
    </ThemeProvider>
  );
}
