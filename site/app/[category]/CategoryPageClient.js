"use client";
import Link from "next/link";
import { useState, useEffect, useMemo } from "react";
import { useLanguage } from "../components/LanguageProvider";
import { TRACKED_JOURNALS } from "../lib/journals";

export default function CategoryPageClient({ category, data }) {
  const { lang, t } = useLanguage();
  const [searchIndex, setSearchIndex] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [isLoadingIndex, setIsLoadingIndex] = useState(false);

  // Load search index for this category
  useEffect(() => {
    async function loadIndex() {
      setIsLoadingIndex(true);
      try {
        const res = await fetch(`/JournalRadar/data/${category}/search_index.json`);
        if (res.ok) {
          const indexData = await res.json();
          setSearchIndex(indexData);
        }
      } catch (e) {
        console.error("Failed to load search index:", e);
      } finally {
        setIsLoadingIndex(false);
      }
    }
    loadIndex();
  }, [category]);

  const filteredResults = useMemo(() => {
    if (!searchTerm.trim()) return [];
    const term = searchTerm.toLowerCase();
    return searchIndex.filter(item => 
      item.title.toLowerCase().includes(term) || 
      item.authors.toLowerCase().includes(term) ||
      item.journal.toLowerCase().includes(term)
    ).slice(0, 50); // Limit to top 50 results for performance
  }, [searchTerm, searchIndex]);

  if (!data) return <div className="page-container"><p>Loading...</p></div>;

  const categoryName = lang === "ko" ? data.categoryName_ko : data.categoryName_en;
  const journals = TRACKED_JOURNALS[category.toLowerCase()] || [];
  const catClass = category.toLowerCase();

  return (
    <main className="page-container">
      <nav className="breadcrumb fade-in">
        <Link href="/">{t.home}</Link>
        <span className="separator">/</span>
        <span className="current">{categoryName}</span>
      </nav>

      <div className="category-header fade-in stagger-1">
        <h1 className="section-title">
          {categoryName}
        </h1>
        <p className="subtitle">
          {lang === "ko" 
            ? `${categoryName} 분야의 모든 과거 논문과 최신 트렌드를 검색해 보세요.` 
            : `Search through all past and current research in ${categoryName}.`}
        </p>
      </div>

      <div className="controls-area" style={{ maxWidth: '600px' }}>
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
      </div>

      {searchTerm.trim() ? (
        <div className="search-results-area fade-in">
          <h2 className="section-title" style={{ fontSize: '1.2rem', marginBottom: '1.5rem' }}>
            {t.papers} ({filteredResults.length})
          </h2>
          {filteredResults.length > 0 ? (
            <div className="paper-list">
              {filteredResults.map((paper, i) => (
                <Link
                  key={paper.slug || i}
                  href={`/${category}/${paper.year}/${paper.week}?paper=${paper.slug}`}
                  className={`paper-card fade-in stagger-${Math.min(i + 1, 4)}`}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <span className={`journal-badge ${catClass}`}>{paper.journal}</span>
                    <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: '600' }}>
                      {paper.year} {paper.week_label}
                    </span>
                  </div>
                  <h3>{paper.title}</h3>
                  <p className="paper-authors">{paper.authors}</p>
                  <p className="paper-date">{paper.date}</p>
                </Link>
              ))}
            </div>
          ) : (
            <div className="no-results">
              <p>{t.noSearchResults}</p>
            </div>
          )}
          <hr style={{ margin: '3rem 0', border: 'none', borderTop: '1px solid var(--border-subtle)' }} />
          <h2 className="section-title" style={{ fontSize: '1.2rem' }}>{t.years}</h2>
        </div>
      ) : null}

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
