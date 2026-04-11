import json
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

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
        return datetime(y, m, min(d, 28))
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
    # Week of the month logic: (day + weekday_of_1st - 1) // 7 + 1
    first_day = monday.replace(day=1)
    dom = monday.day
    adjusted_dom = dom + first_day.weekday()
    week_of_month = (adjusted_dom - 1) // 7 + 1
    
    month_en = MONTH_NAMES_EN[monday.month - 1]
    
    label_ko = f"{monday.month}월 {week_of_month}주차"
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
        dt = parse_date(paper.get("Date"))
        if not dt: continue
        
        iso_year, iso_week = get_iso_week(dt)
        # Use simple WXX as keys for filename/URL stability
        week_label = f"W{iso_week:02d}"
        
        analysis = paper.get("AI_Analysis", "")
        # Remove AI conversational prefixes if they slipped through
        analysis = re.sub(r"^(알겠습니다|물론입니다|네|반갑습니다|안녕하세요)[^.]*AI로서,[^.]*(제공해 드립니다|분석해 드리겠습니다|분석해 보겠습니다|분석해 드립니다)\.?\n*", "", analysis, flags=re.MULTILINE).strip()
        
        # Split by marker, fallback to full text if missing
        parts = analysis.split("===ENGLISH===")
        ko = parts[0].replace("===KOREAN===", "").strip()
        
        if len(parts) > 1:
            en = parts[1].strip()
        else:
            # Fallback for English: Use Korean if no English provided
            # (User said "English later", so for now we show what we have)
            en = ko

        weekly_groups[(iso_year, week_label)].append({
            "slug": slugify(paper.get("Title", "")),
            "title": paper.get("Title", "No Title"),
            "authors": paper.get("Authors", "Unknown"),
            "journal": paper.get("Journal", "Unknown Journal"),
            "date": paper.get("Date", "Unknown"),
            "url": paper.get("URL", ""),
            "abstract": clean_html(paper.get("Abstract", "")),
            "analysis_ko": ko,
            "analysis_en": en,
        })

    years_data = defaultdict(list)
    for (year, week_label), week_papers in sorted(weekly_groups.items()):
        year_dir = os.path.join(output_base, str(year))
        os.makedirs(year_dir, exist_ok=True)
        
        week_num = int(week_label[1:])
        monday, sunday = get_week_start_end(year, week_num)
        label_ko, label_en = get_bilingual_labels(monday)
        
        week_data = {
            "category": category_id.lower(),
            "year": year,
            "week": week_label,
            "label_ko": label_ko,
            "label_en": label_en,
            "startDate": monday.strftime("%Y-%m-%d"),
            "endDate": sunday.strftime("%Y-%m-%d"),
            "paperCount": len(week_papers),
            "papers": week_papers,
        }
        
        with open(os.path.join(year_dir, f"{week_label}.json"), "w", encoding="utf-8") as f:
            json.dump(week_data, f, ensure_ascii=False, indent=2)
            
        years_data[year].append({
            "week": week_label,
            "label_ko": label_ko,
            "label_en": label_en,
            "startDate": week_data["startDate"],
            "endDate": week_data["endDate"],
            "paperCount": len(week_papers),
        })

    all_years_summary = []
    for year, weeks in sorted(years_data.items()):
        weeks.sort(key=lambda w: w["week"])
        year_index = {
            "category": category_id.lower(),
            "year": year,
            "totalPapers": sum(w["paperCount"] for w in weeks),
            "weeks": weeks,
        }
        with open(os.path.join(output_base, str(year), "index.json"), "w", encoding="utf-8") as f:
            json.dump(year_index, f, ensure_ascii=False, indent=2)
            
        all_years_summary.append({
            "year": year,
            "totalPapers": year_index["totalPapers"],
            "weekCount": len(weeks),
        })

    root_index = {
        "category": category_id.lower(),
        "categoryName_ko": category_name_ko,
        "categoryName_en": category_name_en,
        "years": all_years_summary,
    }
    with open(os.path.join(output_base, "index.json"), "w", encoding="utf-8") as f:
        json.dump(root_index, f, ensure_ascii=False, indent=2)

def main():
    if not os.path.exists(BACKFILL_FILE):
        print("❌ backfill_state.json not found!")
        return
        
    with open(BACKFILL_FILE, "r", encoding="utf-8") as f:
        all_papers = json.load(f)
        
    categories = [
        ("Marketing", "마케팅", "Marketing"),
        ("Finance", "재무", "Finance"),
        ("Accounting", "회계", "Accounting")
    ]
    
    for cat_id, name_ko, name_en in categories:
        process_category(all_papers, cat_id, name_ko, name_en)
        
    print("\nAll categories processed and indices generated!")

if __name__ == "__main__":
    main()
