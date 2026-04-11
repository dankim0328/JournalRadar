"use client";
import { createContext, useContext, useState, useEffect } from "react";
import translations from "../lib/i18n";

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState("ko");

  useEffect(() => {
    const saved = localStorage.getItem("jr-lang");
    if (saved && (saved === "ko" || saved === "en")) {
      setLang(saved);
    }
  }, []);

  const toggleLang = (newLang) => {
    setLang(newLang);
    localStorage.setItem("jr-lang", newLang);
  };

  const t = translations[lang] || translations.ko;

  return (
    <LanguageContext.Provider value={{ lang, toggleLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
}
