"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";

type Theme = "light" | "dark" | "system";

interface ThemeContextType {
  theme: Theme;
  setTheme: (t: Theme) => void;
  resolvedTheme: "light" | "dark";
}

const ThemeContext = createContext<ThemeContextType>({
  theme: "system",
  setTheme: () => {},
  resolvedTheme: "light",
});

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("system");
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("light");

  // localStorage'dan tema oku
  useEffect(() => {
    const saved = (localStorage.getItem("finshop_theme") as Theme) || "system";
    setThemeState(saved);
  }, []);

  // Sistem tercihini takip et
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");

    function applyTheme(t: Theme) {
      const resolved = t === "system" ? (mq.matches ? "dark" : "light") : t;
      setResolvedTheme(resolved);
      const html = document.documentElement;
      if (resolved === "dark") {
        html.classList.add("dark");
      } else {
        html.classList.remove("dark");
      }
    }

    applyTheme(theme);

    const handler = () => {
      if (theme === "system") applyTheme("system");
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [theme]);

  // Diğer sekmelere yansıt
  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === "finshop_theme" && e.newValue) {
        setThemeState(e.newValue as Theme);
      }
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  function setTheme(t: Theme) {
    setThemeState(t);
    localStorage.setItem("finshop_theme", t);
  }

  return (
    <ThemeContext.Provider value={{ theme, setTheme, resolvedTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
