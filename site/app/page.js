"use client";
import Link from "next/link";
import { useLanguage } from "./components/LanguageProvider";
import { useEffect, useState } from "react";

export default function Home() {
  const { lang, t } = useLanguage();
  const [marketingData, setMarketingData] = useState(null);

  useEffect(() => {
    fetch("/JournalRadar/data/marketing/index.json")
      .then((r) => r.json())
      .then(setMarketingData)
      .catch(() => {});
  }, []);

  const totalPapers = marketingData
    ? marketingData.years.reduce((sum, y) => sum + y.totalPapers, 0)
    : 0;
  const totalWeeks = marketingData
    ? marketingData.years.reduce((sum, y) => sum + y.weekCount, 0)
    : 0;

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
            {marketingData && (
              <div className="stats">
                <div>
                  <span className="stat-value">{totalPapers}</span>
                  {t.papers}
                </div>
                <div>
                  <span className="stat-value">{totalWeeks}</span>
                  {t.weeks}
                </div>
                <div>
                  <span className="stat-value">{marketingData.years.length}</span>
                  {t.years}
                </div>
              </div>
            )}
          </div>
        </Link>

        {/* Finance */}
        <div className="category-card finance fade-in stagger-2" id="card-finance" style={{opacity: 0.5, cursor: 'default'}}>
          <div className="category-card-content">
            <span className="emoji">💹</span>
            <h2>{t.finance}</h2>
            <p className="subtitle">{t.financeDesc}</p>
            <span className="coming-soon-badge">{t.comingSoon}</span>
          </div>
        </div>

        {/* Accounting */}
        <div className="category-card accounting fade-in stagger-3" id="card-accounting" style={{opacity: 0.5, cursor: 'default'}}>
          <div className="category-card-content">
            <span className="emoji">📒</span>
            <h2>{t.accounting}</h2>
            <p className="subtitle">{t.accountingDesc}</p>
            <span className="coming-soon-badge">{t.comingSoon}</span>
          </div>
        </div>
      </div>
    </main>
  );
}
