"use client";
import Link from "next/link";
import { useLanguage } from "../components/LanguageProvider";
import { TRACKED_JOURNALS } from "../lib/journals";

export default function CategoryPageClient({ category, data }) {
  const { lang, t } = useLanguage();

  if (!data) return <div className="page-container"><p>Loading...</p></div>;

  const categoryName = lang === "ko" ? data.categoryName_ko : data.categoryName_en;
  const journals = TRACKED_JOURNALS[category.toLowerCase()] || [];

  return (
    <main className="page-container">
      <nav className="breadcrumb fade-in">
        <Link href="/">{t.home}</Link>
        <span className="separator">/</span>
        <span className="current">{categoryName}</span>
      </nav>

      <div className="category-header fade-in stagger-1">
        <h1 className="section-title">
          {categoryName} — {t.selectYear}
        </h1>
        <p className="subtitle">
          {lang === "ko" 
            ? `${categoryName} 분야의 최신 세계 최고 권위 학술지 논문을 탐색하세요.` 
            : `Explore the latest research from top ${categoryName} journals.`}
        </p>
      </div>

      <div className="year-grid">
        {data.years
          .sort((a, b) => b.year - a.year)
          .map((yearInfo, i) => (
            <Link
              href={`/${category}/${yearInfo.year}`}
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

      {/* Tracked Journals Section */}
      <section className="journal-list-section fade-in stagger-4">
        <h2 className="journal-title">
          {lang === "ko" ? "추적 대상 학술지 (Tracked Journals)" : "Tracked Journals"}
        </h2>
        <div className="journal-grid">
          {journals.map((journal, idx) => (
            <div key={idx} className="journal-item">
              {journal}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
