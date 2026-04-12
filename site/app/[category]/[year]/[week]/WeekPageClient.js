"use client";
import Link from "next/link";
import { useLanguage } from "../../../components/LanguageProvider";
import { useState, useMemo, useEffect } from "react";
import { useSearchParams } from "next/navigation";

export default function WeekPageClient({ category, year, week, data }) {
  const { lang, t } = useLanguage();
  const searchParams = useSearchParams();
  const [selectedPaper, setSelectedPaper] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedJournal, setSelectedJournal] = useState("all");

  // Handle deep-linking to a specific paper
  useEffect(() => {
    const paperSlug = searchParams.get("paper");
    if (paperSlug && data && data.papers) {
      const paper = data.papers.find(p => p.slug === paperSlug);
      if (paper) setSelectedPaper(paper);
    }
  }, [searchParams, data]);

  const uniqueJournals = useMemo(() => {
    if (!data || !data.papers) return [];
    const journals = new Set(data.papers.map(p => p.journal));
    return Array.from(journals).sort();
  }, [data]);

  const filteredPapers = useMemo(() => {
    if (!data || !data.papers) return [];
    return data.papers.filter(paper => {
      const matchesJournal = selectedJournal === "all" || paper.journal === selectedJournal;
      const matchesSearch = 
        paper.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
        paper.authors.toLowerCase().includes(searchTerm.toLowerCase());
      return matchesJournal && matchesSearch;
    });
  }, [data, searchTerm, selectedJournal]);

  if (!data) return <div className="page-container"><p>{t.noPapers}</p></div>;

  const displayCategory = t[category] || (category.charAt(0).toUpperCase() + category.slice(1));
  const weekLabel = lang === "ko" ? data.label_ko : data.label_en;
  const catClass = category.toLowerCase();

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
            <span className={`journal-badge ${catClass}`}>{paper.journal}</span>
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
                  <a href={paper.url} target="_blank" rel="noopener noreferrer" style={{ color: `var(--color-${catClass})` }}>
                    {t.link} ↗
                  </a>
                ) : (
                  "—"
                )}
              </div>
            </div>
          </div>

          <section className="paper-section">
            <h2 style={{ borderLeft: `3px solid var(--color-${catClass})`, paddingLeft: '12px' }}>
              <span className="section-icon">📄</span>
              {t.abstract}
            </h2>
            <div className="abstract-box" style={{ borderLeft: `3px solid var(--color-${catClass})` }}>{paper.abstract}</div>
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
        <Link href={`/${category}`}>{displayCategory}</Link>
        <span className="separator">/</span>
        <Link href={`/${category}/${year}`}>{year}</Link>
        <span className="separator">/</span>
        <span className="current">{weekLabel}</span>
      </nav>

      <div className="papers-header fade-in stagger-1">
        <h1>
          📊 {displayCategory} — {year} {weekLabel}
        </h1>
        <p className="date-range">
          {data.startDate} ~ {data.endDate} · {data.paperCount} {t.paperCount}
        </p>
      </div>

      <div className="controls-area">
        <div className="search-container">
          <span className="search-icon">🔍</span>
          <input 
            type="text" 
            className="search-input" 
            placeholder={t.searchPlaceholder}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filter-container">
          <span className="filter-label">{t.filterByJournal}:</span>
          <button 
            className={`filter-chip ${selectedJournal === "all" ? "active" : ""}`}
            onClick={() => setSelectedJournal("all")}
          >
            {t.allJournals}
          </button>
          {uniqueJournals.map(journal => (
            <button 
              key={journal}
              className={`filter-chip ${selectedJournal === journal ? "active" : ""}`}
              onClick={() => setSelectedJournal(journal)}
            >
              {journal}
            </button>
          ))}
        </div>
      </div>

      <div className="paper-list">
        {filteredPapers.length > 0 ? (
          filteredPapers.map((paper, i) => (
            <div
              key={paper.slug || i}
              className={`paper-card fade-in stagger-${Math.min(i + 1, 4)}`}
              onClick={() => setSelectedPaper(paper)}
              id={`paper-${paper.slug || i}`}
            >
              <span className={`journal-badge ${catClass}`}>{paper.journal}</span>
              <h3>{paper.title}</h3>
              <p className="paper-authors">{paper.authors}</p>
              <p className="paper-date">{paper.date}</p>
            </div>
          ))
        ) : (
          <div className="no-results fade-in">
            <p>{t.noSearchResults}</p>
          </div>
        )}
      </div>
    </main>
  );
}
