"""
Convert backfill_state.json → weekly JSON files for Journal Radar website.

Input:  ../backfill_state.json  (424 marketing papers, monthly grouping)
Output: ../site/public/data/marketing/YYYY/WNN.json  (weekly grouping)
        ../site/public/data/marketing/YYYY/index.json (year index)
        ../site/public/data/marketing/index.json      (root index)
"""

import json
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict


BACKFILL_FILE = os.path.join(os.path.dirname(__file__), "..", "backfill_state.json")
OUTPUT_BASE = os.path.join(os.path.dirname(__file__), "..", "site", "public", "data", "marketing")


def clean_html(text):
    """Remove HTML/XML tags like <jats:p>."""
    if not text:
        return ""
    return re.sub(r'<[^>]+>', '', text).strip()


def parse_date(date_str):
    """Parse date string like '2025-1', '2025-01-15', 'Unknown' → datetime or None."""
    if not date_str or date_str == "Unknown":
        return None
    parts = date_str.split("-")
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) >= 2 else 1
        day = int(parts[2]) if len(parts) >= 3 else 1
        # Clamp day to valid range
        if month < 1: month = 1
        if month > 12: month = 12
        if day < 1: day = 1
        if day > 28: day = 28  # Safe default
        return datetime(year, month, day)
    except (ValueError, IndexError):
        return None


def get_iso_week_label(dt):
    """Return ISO week label like 'W01', 'W52'."""
    iso_year, iso_week, _ = dt.isocalendar()
    return iso_year, f"W{iso_week:02d}"


def get_week_start_end(iso_year, week_num):
    """Get Monday and Sunday dates for a given ISO week."""
    # Jan 4 is always in ISO week 1
    jan4 = datetime(iso_year, 1, 4)
    start_of_week1 = jan4 - timedelta(days=jan4.weekday())
    monday = start_of_week1 + timedelta(weeks=week_num - 1)
    sunday = monday + timedelta(days=6)
    return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")


def split_analysis(analysis_text):
    """Split '===KOREAN===...===ENGLISH===...' into (ko, en) strings."""
    if not analysis_text:
        return "", ""

    parts = analysis_text.split("===ENGLISH===")
    ko_raw = parts[0].replace("===KOREAN===", "").strip()
    en_raw = parts[1].strip() if len(parts) > 1 else ""

    return ko_raw, en_raw


def slugify(title):
    """Create a URL-safe slug from a paper title."""
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug[:80]


def main():
    print("📂 Loading backfill_state.json...")
    with open(BACKFILL_FILE, "r", encoding="utf-8") as f:
        papers = json.load(f)

    print(f"   Loaded {len(papers)} papers")

    # Group papers by ISO week
    weekly_groups = defaultdict(list)  # key: (iso_year, "W01")
    skipped = 0

    for paper in papers:
        # Skip papers without analysis
        analysis = paper.get("AI_Analysis", "").strip()
        if not analysis or analysis == "AI 백필 분석 실패.":
            skipped += 1
            continue

        dt = parse_date(paper.get("Date", "Unknown"))
        if dt is None:
            # Try to infer from YearMonth
            ym = paper.get("YearMonth", "")
            if ym and ym != "0000-Unknown":
                parts = ym.split("-")
                try:
                    dt = datetime(int(parts[0]), int(parts[1]), 1)
                except (ValueError, IndexError):
                    skipped += 1
                    continue
            else:
                skipped += 1
                continue

        iso_year, week_label = get_iso_week_label(dt)
        ko_analysis, en_analysis = split_analysis(analysis)

        weekly_groups[(iso_year, week_label)].append({
            "slug": slugify(paper.get("Title", "")),
            "title": paper.get("Title", "No Title"),
            "authors": paper.get("Authors", "Unknown"),
            "journal": paper.get("Journal", "Unknown Journal"),
            "date": paper.get("Date", "Unknown"),
            "url": paper.get("URL", ""),
            "abstract": clean_html(paper.get("Abstract", "")),
            "analysis_ko": ko_analysis,
            "analysis_en": en_analysis,
        })

    print(f"   Skipped {skipped} papers (no analysis or no date)")
    print(f"   Grouped into {len(weekly_groups)} weeks")

    # Create output directory
    os.makedirs(OUTPUT_BASE, exist_ok=True)

    # Organize by year
    years_data = defaultdict(list)  # year → [week_info, ...]

    for (iso_year, week_label), week_papers in sorted(weekly_groups.items()):
        # Create year directory
        year_dir = os.path.join(OUTPUT_BASE, str(iso_year))
        os.makedirs(year_dir, exist_ok=True)

        # Sort papers by date
        week_papers.sort(key=lambda p: p["date"])

        # Write weekly JSON
        week_file = os.path.join(year_dir, f"{week_label}.json")
        week_num = int(week_label[1:])
        start_date, end_date = get_week_start_end(iso_year, week_num)

        week_data = {
            "category": "marketing",
            "year": iso_year,
            "week": week_label,
            "startDate": start_date,
            "endDate": end_date,
            "paperCount": len(week_papers),
            "papers": week_papers,
        }

        with open(week_file, "w", encoding="utf-8") as f:
            json.dump(week_data, f, ensure_ascii=False, indent=2)

        years_data[iso_year].append({
            "week": week_label,
            "startDate": start_date,
            "endDate": end_date,
            "paperCount": len(week_papers),
        })

        print(f"   ✅ {iso_year}/{week_label}.json — {len(week_papers)} papers")

    # Write year index files
    all_years = []
    for year, weeks in sorted(years_data.items()):
        weeks.sort(key=lambda w: w["week"])
        year_index = {
            "category": "marketing",
            "year": year,
            "totalPapers": sum(w["paperCount"] for w in weeks),
            "weeks": weeks,
        }
        year_index_file = os.path.join(OUTPUT_BASE, str(year), "index.json")
        with open(year_index_file, "w", encoding="utf-8") as f:
            json.dump(year_index, f, ensure_ascii=False, indent=2)

        all_years.append({
            "year": year,
            "totalPapers": year_index["totalPapers"],
            "weekCount": len(weeks),
        })

    # Write root index
    root_index = {
        "category": "marketing",
        "categoryName_ko": "마케팅",
        "categoryName_en": "Marketing",
        "years": all_years,
    }
    root_index_file = os.path.join(OUTPUT_BASE, "index.json")
    with open(root_index_file, "w", encoding="utf-8") as f:
        json.dump(root_index, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Done! Created {len(weekly_groups)} weekly files across {len(all_years)} years.")
    print(f"   Output: {os.path.abspath(OUTPUT_BASE)}")


if __name__ == "__main__":
    main()
