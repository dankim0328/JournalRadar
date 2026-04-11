"use client";
import Link from "next/link";
import { useLanguage } from "../../../components/LanguageProvider";
import { useState } from "react";

export default function WeekPageClient({ year, week, data }) {
  const { lang, t } = useLanguage();
  const [selectedPaper, setSelectedPaper] = useState(null);

  if (!data) return <div className="page-container"><p>{t.noPapers}</p></div>;

  // Paper detail view
  if (selectedPaper) {
    const paper = selectedPaper;
    const analysis = lang === "ko" ? paper.analysis_ko : paper.analysis_en;

    return (
      <main className="page-container">
        <button className="back-btn" onClick={() => setSelectedPaper(null)} id="back-to-list">
          ← {t.backToPapers}
        </button>

        <div className="paper-detail">
          <div className="paper-detail-header">
            <span className="journal-badge">{paper.journal}</span>
            <h1>{paper.title}</h1>
          </div>

          <div className="paper-meta-grid">
            <div className="meta-item">
              <div className="meta-label">{t.authors}</div>
              <div className="meta-value">{paper.authors}</div>
            </div>
            <div className="meta-item">
              <div className="meta-label">{t.journal}</div>
              <div className="meta-value">{paper.journal}</div>
            </div>
            <div className="meta-item">
              <div className="meta-label">{t.published}</div>
              <div className="meta-value">{paper.date}</div>
            </div>
            <div className="meta-item">
              <div className="meta-label">{t.link}</div>
              <div className="meta-value">
                {paper.url ? (
                  <a href={paper.url} target="_blank" rel="noopener noreferrer">
                    {t.link} ↗
                  </a>
                ) : (
                  "—"
                )}
              </div>
            </div>
          </div>

          <section className="paper-section">
            <h2>
              <span className="section-icon">📄</span>
              {t.abstract}
            </h2>
            <div className="abstract-box">{paper.abstract}</div>
          </section>

          <section className="paper-section">
            <h2>
              <span className="section-icon">🤖</span>
              {t.aiAnalysis}
            </h2>
            <div className="analysis-box">{analysis || t.noPapers}</div>
          </section>
        </div>
      </main>
    );
  }

  // Paper list view
  return (
    <main className="page-container">
      <nav className="breadcrumb fade-in">
        <Link href="/">{t.home}</Link>
        <span className="separator">/</span>
        <Link href="/marketing">{t.marketing}</Link>
        <span className="separator">/</span>
        <Link href={`/marketing/${year}`}>{year}</Link>
        <span className="separator">/</span>
        <span className="current">{week}</span>
      </nav>

      <div className="papers-header fade-in stagger-1">
        <h1>
          📊 {t.marketing} — {year} {week}
        </h1>
        <p className="date-range">
          {data.startDate} ~ {data.endDate} · {data.paperCount} {t.paperCount}
        </p>
      </div>

      <div className="paper-list">
        {data.papers.map((paper, i) => (
          <div
            key={paper.slug || i}
            className={`paper-card fade-in stagger-${Math.min(i + 1, 4)}`}
            onClick={() => setSelectedPaper(paper)}
            id={`paper-${paper.slug || i}`}
          >
            <span className="journal-badge">{paper.journal}</span>
            <h3>{paper.title}</h3>
            <p className="paper-authors">{paper.authors}</p>
            <p className="paper-date">{paper.date}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
