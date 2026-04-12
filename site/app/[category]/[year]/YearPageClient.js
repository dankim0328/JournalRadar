"use client";
import Link from "next/link";
import { useLanguage } from "../../components/LanguageProvider";
import { useParams } from "next/navigation";

function getMonthFromWeek(year, weekStr) {
  const weekNum = parseInt(weekStr.replace("W", ""), 10);
  const jan4 = new Date(parseInt(year), 0, 4);
  const startOfWeek1 = new Date(jan4);
  // ISO 8601: Week 1 is the week with Jan 4.
  // Calculate the Monday of that week.
  const dayOffset = jan4.getDay() === 0 ? 6 : jan4.getDay() - 1;
  startOfWeek1.setDate(jan4.getDate() - dayOffset);
  
  const monday = new Date(startOfWeek1);
  monday.setDate(startOfWeek1.getDate() + (weekNum - 1) * 7);
  
  // 4-day rule: Group by the month that contains the majority of the week (Thursday).
  const thursday = new Date(monday);
  thursday.setDate(monday.getDate() + 3);
  return thursday.getMonth();
}


export default function YearPageClient({ year, data }) {
  const { lang, t } = useLanguage();
  const params = useParams();
  const category = params.category;

  if (!data || !data.weeks) {
    return <div className="page-container"><p>Loading...</p></div>;
  }

  const categoryName = lang === "ko" ? t[category] || category : t[category] || category;
  // If t[category] is missing, use capital first
  const displayCategory = t[category] || (category.charAt(0).toUpperCase() + category.slice(1));

  const monthGroups = {};
  data.weeks.forEach((w) => {
    const monthIdx = getMonthFromWeek(year, w.week);
    if (!monthGroups[monthIdx]) monthGroups[monthIdx] = [];
    monthGroups[monthIdx].push(w);
  });

  const sortedMonths = Object.keys(monthGroups)
    .map(Number)
    .sort((a, b) => b - a);

  return (
    <main className="page-container">
      <nav className="breadcrumb fade-in">
        <Link href="/">{t.home}</Link>
        <span className="separator">/</span>
        <Link href={`/${category}`}>{displayCategory}</Link>
        <span className="separator">/</span>
        <span className="current">{year}</span>
      </nav>

      <h1 className="section-title fade-in stagger-1">
        📊 {displayCategory} {year} — {t.selectWeek}
      </h1>

      {sortedMonths.map((monthIdx, gi) => (
        <div key={monthIdx} className={`month-group fade-in stagger-${Math.min(gi + 1, 4)}`}>
          <div className="month-label">
            <span className="month-icon">📅</span>
            {t.monthNames[monthIdx]} {year}
          </div>
          <div className="week-grid">
            {monthGroups[monthIdx]
              .sort((a, b) => a.week.localeCompare(b.week)) // Sort ascending to assign W1-W5 correctly
              .map((w, idx) => (
                <Link
                  href={`/${category}/${year}/${w.week}`}
                  key={w.week}
                  className="week-card"
                  id={`week-${w.week}`}
                >
                  <div className="week-number-badge">
                    W{idx + 1}
                  </div>
                  <div className="week-info">
                    <div className="week-label-sub">
                      {(lang === "ko" ? w.label_ko : w.label_en) || 
                        (lang === "ko" 
                          ? `${parseInt(w.startDate.split('-')[1])}월 ${Math.floor((parseInt(w.startDate.split('-')[2]) - 1) / 7) + 1}주차`
                          : `Week ${w.week.replace('W', '')}`)}
                    </div>
                    <div className="week-date">
                      {w.startDate} ~ {w.endDate}
                    </div>
                    <div className="week-count">
                      {w.paperCount} {t.paperCount}
                    </div>
                  </div>
                </Link>
              ))}
          </div>
        </div>
      ))}
    </main>
  );
}
