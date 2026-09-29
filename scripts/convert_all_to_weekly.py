import json
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict
try:
    from . import generate_weekly_json as weekly
except ImportError:
    import generate_weekly_json as weekly

BACKFILL_FILE = os.path.join(os.path.dirname(__file__), "..", "backfill_state.json")
SITE_PUBLIC_DATA = os.path.join(os.path.dirname(__file__), "..", "site", "public", "data")

MONTH_NAMES_EN = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

def clean_html(text):
    if not text: return ""
    return re.sub(r'<[^>]+>', '', text).strip()

def parse_date(date_str):
    if not date_str or date_str == "Unknown": return None
    try:
        # Standardize YYYY-M-D to YYYY-MM-DD
        parts = date_str.split("-")
        if len(parts) < 2: return None
        y, m = int(parts[0]), int(parts[1])
        d = int(parts[2]) if len(parts) >= 3 else 1
        return datetime(y, m, d)
    except: return None

def get_iso_week(dt):
    iso_year, iso_week, _ = dt.isocalendar()
    return iso_year, iso_week

def get_week_start_end(iso_year, week_num):
    jan4 = datetime(iso_year, 1, 4)
    start_of_week1 = jan4 - timedelta(days=jan4.weekday())
    monday = start_of_week1 + timedelta(weeks=week_num - 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday

def get_bilingual_labels(monday):
    # 4-day rule: A week belongs to the month that contains its Thursday.
    thursday = monday + timedelta(days=3)
    first_day = thursday.replace(day=1)
    
    # Week of the month: which N-th Thursday of the month is this?
    dom = thursday.day
    week_of_month = (dom - 1) // 7 + 1
    
    month_en = MONTH_NAMES_EN[thursday.month - 1]
    
    label_ko = f"{thursday.month}월 {week_of_month}주차"
    label_en = f"{month_en} Week {week_of_month}"
    
    return label_ko, label_en


def slugify(title):
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug[:80]

def process_category(all_papers, category_id, category_name_ko, category_name_en):
    print(f"Processing {category_name_en}...")
    papers = [p for p in all_papers if p.get("Category") == category_id]
    
    output_base = os.path.join(SITE_PUBLIC_DATA, category_id.lower())
    os.makedirs(output_base, exist_ok=True)
    
    weekly_groups = defaultdict(list)
    for paper in papers:
        # Standardize keys (handling BOM \ufeffJournal or lowercase journal)
        # We lowercase all keys and remove \ufeff
        paper = {k.lstrip('\ufeff').lower(): v for k, v in paper.items()}
        
        dt = parse_date(paper.get("date"))
        if not dt: continue
        
        iso_year, iso_week = get_iso_week(dt)
        # Use simple WXX as keys for filename/URL stability
        week_label = f"W{iso_week:02d}"
        
        analysis = paper.get("ai_analysis", "")
        # Remove AI conversational prefixes if they slipped through
        analysis = re.sub(r"^(알겠습니다|물론입니다|네|반갑습니다|안녕하세요)[^.]*AI로서,[^.]*(제공해 드립니다|분석해 드리겠습니다|분석해 보겠습니다|분석해 드립니다)\.?\n*", "", analysis, flags=re.MULTILINE).strip()
        
        # Split by marker, fallback to full text if missing
        parts = analysis.split("===ENGLISH===")
        ko = parts[0].replace("===KOREAN===", "").strip()
        
        if len(parts) > 1:
            en = parts[1].strip()
        else:
            # User requested: English analysis should be empty if not provided
            en = ""

        weekly_groups[(iso_year, week_label)].append({
            "slug": slugify(paper.get("title", "")),
            "title": paper.get("title", "No Title"),
            "authors": paper.get("authors", "Unknown"),
            "journal": paper.get("journal", "Unknown Journal"),
            "date": paper.get("date", "Unknown"),
            "url": paper.get("url", ""),
            "abstract": clean_html(paper.get("abstract", "")),
            "analysis_ko": ko,
            "analysis_en": en,
        })

    # A fresh Actions runner only has this batch, not the ignored backfill state.
    # Merge into tracked weekly files, then index ALL historical weeks.
    weekly.SITE_DATA_DIR = SITE_PUBLIC_DATA
    for (year, week_label), week_papers in sorted(weekly_groups.items()):
        weekly.save_weekly_data(category_id.lower(), year, int(week_label[1:]), week_papers)
    weekly.update_indexes(category_id.lower())


def main():
    if not os.path.exists(BACKFILL_FILE):
        print("❌ backfill_state.json not found!")
        raise SystemExit(1)
        
    with open(BACKFILL_FILE, "r", encoding="utf-8") as f:
        all_papers = json.load(f)
        
    categories = [
        ("Marketing", "마케팅", "Marketing")
    ]
    
    for cat_id, name_ko, name_en in categories:
        process_category(all_papers, cat_id, name_ko, name_en)
        
    print("\nAll categories processed and indices generated!")

if __name__ == "__main__":
    main()
