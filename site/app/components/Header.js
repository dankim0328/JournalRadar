"use client";
import Link from "next/link";
import { useLanguage } from "./LanguageProvider";

export default function Header() {
  const { lang, toggleLang, t } = useLanguage();

  return (
    <header className="header">
      <Link href="/" className="header-logo">
        <span className="radar-icon">📡</span>
        <span>{t.siteName}</span>
      </Link>
      <nav className="header-nav">
        <div className="lang-toggle">
          <button
            className={`lang-btn ${lang === "ko" ? "active" : ""}`}
            onClick={() => toggleLang("ko")}
          >
            KO
          </button>
          <button
            className={`lang-btn ${lang === "en" ? "active" : ""}`}
            onClick={() => toggleLang("en")}
          >
            EN
          </button>
        </div>
      </nav>
    </header>
  );
}
