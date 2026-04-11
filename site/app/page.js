"use client";
import Link from "next/link";
import { useLanguage } from "./components/LanguageProvider";
import { useEffect, useState } from "react";

export default function Home() {
  const { lang, t } = useLanguage();
  const [stats, setStats] = useState({
    marketing: null,
    finance: null,
    accounting: null
  });

  useEffect(() => {
    const categories = ["marketing", "finance", "accounting"];
    categories.forEach(cat => {
      fetch(`/JournalRadar/data/${cat}/index.json`)
        .then((r) => r.json())
        .then(data => {
          setStats(prev => ({ ...prev, [cat]: data }));
        })
        .catch(() => {});
    });
  }, []);

  const getStats = (catData) => {
    if (!catData) return null;
    return {
      totalPapers: catData.years.reduce((sum, y) => sum + y.totalPapers, 0),
      totalWeeks: catData.years.reduce((sum, y) => sum + y.weekCount, 0),
      yearsCount: catData.years.length
    };
  };

  const renderStats = (catData) => {
    const s = getStats(catData);
    if (!s) return null;
    return (
      <div className="stats">
        <div>
          <span className="stat-value">{s.totalPapers}</span>
          {t.papers}
        </div>
        <div>
          <span className="stat-value">{s.totalWeeks}</span>
          {t.weeks}
        </div>
        <div>
          <span className="stat-value">{s.yearsCount}</span>
          {t.years}
        </div>
      </div>
    );
  };

  return (
    <main className="page-container">
      <section className="hero fade-in">
        <h1>Journal Radar</h1>
        <p>{t.siteTagline}</p>
      </section>

      <div className="category-grid">
        {/* Marketing */}
        <Link href="/marketing" className="category-card marketing fade-in stagger-1" id="card-marketing">
          <div className="category-card-content">
            <span className="emoji">📊</span>
            <h2>{t.marketing}</h2>
            <p className="subtitle">{t.marketingDesc}</p>
            {renderStats(stats.marketing)}
          </div>
        </Link>

        {/* Finance */}
        <Link href="/finance" className="category-card finance fade-in stagger-2" id="card-finance">
          <div className="category-card-content">
            <span className="emoji">💹</span>
            <h2>{t.finance}</h2>
            <p className="subtitle">{t.financeDesc}</p>
            {renderStats(stats.finance)}
          </div>
        </Link>

        {/* Accounting */}
        <Link href="/accounting" className="category-card accounting fade-in stagger-3" id="card-accounting">
          <div className="category-card-content">
            <span className="emoji">📒</span>
            <h2>{t.accounting}</h2>
            <p className="subtitle">{t.accountingDesc}</p>
            {renderStats(stats.accounting)}
          </div>
        </Link>
      </div>
    </main>
  );
}
