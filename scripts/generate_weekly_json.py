"""
Generate weekly JSON data for the Journal Radar website.
Called by GitHub Actions after the weekly research scripts run.

This script reads the latest weekly Notion upload data and creates/updates
the corresponding JSON files in site/public/data/.
"""

import json
import os
import re
import datetime
import sys
sys.stdout.reconfigure(encoding='utf-8')
from collections import defaultdict

SITE_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "site", "public", "data")

CATEGORIES = {
    "marketing": {
        "name_ko": "마케팅",
        "name_en": "Marketing",
    },
    "finance": {
        "name_ko": "재무",
        "name_en": "Finance",
    },
    "accounting": {
        "name_ko": "회계",
        "name_en": "Accounting",
    },
}


def clean_html(text):
    if not text:
        return ""
    return re.sub(r'<[^>]+>', '', text).strip()


def slugify(title):
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug[:80]


def get_iso_week():
    """Get current ISO year and week."""
    today = datetime.date.today()
    iso_year, iso_week, _ = today.isocalendar()
    return iso_year, iso_week


def get_week_dates(iso_year, week_num):
    jan4 = datetime.date(iso_year, 1, 4)
    start_of_week1 = jan4 - datetime.timedelta(days=jan4.weekday())
    monday = start_of_week1 + datetime.timedelta(weeks=week_num - 1)
    sunday = monday + datetime.timedelta(days=6)
    return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")


def save_weekly_data(category, year, week_num, papers):
    """Save or merge papers into the weekly JSON file."""
    cat_dir = os.path.join(SITE_DATA_DIR, category) 
    year_dir = os.path.join(cat_dir, str(year))
    os.makedirs(year_dir, exist_ok=True)

    week_label = f"W{week_num:02d}"
    week_file = os.path.join(year_dir, f"{week_label}.json")
    start_date, end_date = get_week_dates(year, week_num)

    # Load existing data if file exists
    existing_papers = []
    existing_slugs = set()
    if os.path.exists(week_file):
        with open(week_file, "r", encoding="utf-8") as f:
            existing = json.load(f)
            existing_papers = existing.get("papers", [])
            existing_slugs = {p["slug"] for p in existing_papers}

    # Add new papers (avoid duplicates)
    for paper in papers:
        slug = slugify(paper.get("title", ""))
        if slug not in existing_slugs:
            existing_papers.append(paper)
            existing_slugs.add(slug)

    # Sort by date
    existing_papers.sort(key=lambda p: p.get("date", ""))

    # 4-day rule for fallback label
    dt_monday = datetime.date(*[int(x) for x in start_date.split('-')])
    dt_thursday = dt_monday + datetime.timedelta(days=3)
    dt_first = dt_thursday.replace(day=1)
    label_month = dt_thursday.month
    label_week = (dt_thursday.day + dt_first.weekday() - 1) // 7 + 1
    
    week_data = {
        "category": category,
        "year": year,
        "week": week_label,
        "startDate": start_date,
        "endDate": end_date,
        "label_ko": f"{label_month}월 {label_week}주차",
        "paperCount": len(existing_papers),
        "papers": existing_papers,
    }

    with open(week_file, "w", encoding="utf-8") as f:
        json.dump(week_data, f, ensure_ascii=False, separators=(',', ':'))

    print(f"  ✅ {category}/{year}/{week_label}.json — {len(existing_papers)} papers")
    return week_label


def update_indexes(category):
    """Rebuild index.json files for the category."""
    cat_dir = os.path.join(SITE_DATA_DIR, category)
    if not os.path.exists(cat_dir):
        return

    years_data = []
    for year_name in sorted(os.listdir(cat_dir)):
        year_path = os.path.join(cat_dir, year_name)
        if not os.path.isdir(year_path):
            continue

        try:
            year_num = int(year_name)
        except ValueError:
            continue

        weeks = []
        total_papers = 0
        for fname in sorted(os.listdir(year_path)):
            if fname.startswith("W") and fname.endswith(".json"):
                fpath = os.path.join(year_path, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    wdata = json.load(f)
                
                # Capture label_ko and label_en if they exist, or build fallback
                label_ko = wdata.get("label_ko", "")
                label_en = wdata.get("label_en", "")
                
                # If missing, try to generate one (e.g., "1월 1주차") using 4-day rule
                if not label_ko:
                    dt_m = datetime.date(*[int(x) for x in wdata["startDate"].split("-")])
                    dt_t = dt_m + datetime.timedelta(days=3)
                    dt_f = dt_t.replace(day=1)
                    label_ko = f"{dt_t.month}월 {(dt_t.day + dt_f.weekday() - 1) // 7 + 1}주차"
                if not label_en:
                    # Generic fallback
                    label_en = f"Week {wdata['week'].replace('W', '')}"

                weeks.append({
                    "week": wdata["week"],
                    "startDate": wdata.get("startDate", ""),
                    "endDate": wdata.get("endDate", ""),
                    "label_ko": label_ko,
                    "label_en": label_en,
                    "paperCount": wdata.get("paperCount", 0),
                })
                total_papers += wdata.get("paperCount", 0)

        # Write year index
        year_index = {
            "category": category,
            "year": year_num,
            "totalPapers": total_papers,
            "weeks": weeks,
        }
        with open(os.path.join(year_path, "index.json"), "w", encoding="utf-8") as f:
            json.dump(year_index, f, ensure_ascii=False, separators=(',', ':'))

        years_data.append({
            "year": year_num,
            "totalPapers": total_papers,
            "weekCount": len(weeks),
        })

    # Write root index
    cat_info = CATEGORIES.get(category, {})
    root_index = {
        "category": category,
        "categoryName_ko": cat_info.get("name_ko", category),
        "categoryName_en": cat_info.get("name_en", category.title()),
        "years": years_data,
    }
    with open(os.path.join(cat_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(root_index, f, ensure_ascii=False, separators=(',', ':'))

    print(f"  📋 {category} indexes updated ({len(years_data)} years, {sum(y['totalPapers'] for y in years_data)} total papers)")


def main():
    print("📊 Generating weekly JSON data for Journal Radar...")

    # For now, this script just rebuilds indexes from existing weekly files.
    # The actual paper data injection happens when the research scripts
    # are modified to also output JSON (future enhancement).
    
    for category in CATEGORIES:
        cat_dir = os.path.join(SITE_DATA_DIR, category)
        if os.path.exists(cat_dir):
            update_indexes(category)
        else:
            print(f"  ⚠️ No data for {category} yet")

    print("✅ Done!")


if __name__ == "__main__":
    main()
