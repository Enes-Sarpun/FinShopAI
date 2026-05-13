"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import i18n from "./i18n";

type Lang = "tr" | "en";

interface LangContextType {
  lang: Lang;
  setLang: (l: Lang) => void;
}

const LangContext = createContext<LangContextType>({
  lang: "tr",
  setLang: () => {},
});

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("tr");

  useEffect(() => {
    const saved = (localStorage.getItem("finshop_lang") as Lang) || "tr";
    setLangState(saved);
    i18n.changeLanguage(saved);
    document.documentElement.lang = saved;
  }, []);

  function setLang(l: Lang) {
    setLangState(l);
    localStorage.setItem("finshop_lang", l);
    i18n.changeLanguage(l);
    document.documentElement.lang = l;
  }

  return (
    <LangContext.Provider value={{ lang, setLang }}>
      {children}
    </LangContext.Provider>
  );
}

export const useLang = () => useContext(LangContext);
