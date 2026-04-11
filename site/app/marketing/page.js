"use client";
import Link from "next/link";
import { useLanguage } from "../components/LanguageProvider";
import { useEffect, useState } from "react";

export default function MarketingPage() {
  const { t } = useLanguage();
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch("/JournalRadar/data/marketing/index.json")
      .then((r) => r.json())
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data) return <div className="page-container"><p>Loading...</p></div>;

  return (
    <main className="page-container">
      <nav className="breadcrumb fade-in">
        <Link href="/">{t.home}</Link>
        <span className="separator">/</span>
        <span className="current">{t.marketing}</span>
      </nav>

      <h1 className="section-title fade-in stagger-1">
        📊 {t.marketing} — {t.selectYear}
      </h1>

      <div className="year-grid">
        {data.years
          .sort((a, b) => b.year - a.year)
          .map((yearInfo, i) => (
            <Link
              href={`/marketing/${yearInfo.year}`}
              key={yearInfo.year}
              className={`year-card fade-in stagger-${Math.min(i + 1, 4)}`}
              id={`year-${yearInfo.year}`}
            >
              <div className="year-number">{yearInfo.year}</div>
              <div className="year-meta">
                {yearInfo.totalPapers} {t.papers} · {yearInfo.weekCount} {t.weeks}
              </div>
            </Link>
          ))}
      </div>
    </main>
  );
}
