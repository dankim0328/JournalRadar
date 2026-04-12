import json
import csv
import re
import os
from datetime import datetime

def clean_text(text):
    if not text:
        return ""
    # Remove ** bolding
    text = text.replace("**", "")
    # Remove leading AI prefixes like "알겠습니다. ... 제공해 드립니다." or "물론입니다. ... 분석해 드리겠습니다."
    text = re.sub(r"^(알겠습니다|물론입니다|네|반갑습니다|안녕하세요)[^.]*AI로서,[^.]*(제공해 드립니다|분석해 드리겠습니다|분석해 보겠습니다|분석해 드립니다)\.?\n*", "", text, flags=re.MULTILINE)
    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def parse_markdown_papers(file_path, category):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Robust split: Paper titles start with ## at the beginning of a line
    # We add a newline at start to ensure the first one matches
    sections = re.split(r'\n##\s+', '\n' + content.strip())[1:]
    papers = []
    
    for section in sections:
        lines = section.strip().split('\n')
        title = lines[0].strip()
        
        journal = ""
        authors = ""
        date = ""
        url = ""
        
        # Look for metadata in <aside> or bullet points
        # Use flexible regex to ignore bold markers like **저널명**:
        journal_match = re.search(r'저널명[*\s:]+(.+)', section)
        authors_match = re.search(r'저자[*\s:]+(.+)', section)
        date_match = re.search(r'출판일[*\s:]+(.+)', section)
        url_match = re.search(r'링크[*\s:]+(https?://\S+)', section)
        
        if journal_match: journal = journal_match.group(1).replace("**", "").strip()
        if authors_match: authors = authors_match.group(1).replace("**", "").strip()
        if date_match: date = date_match.group(1).replace("**", "").strip()
        if url_match: url = url_match.group(1).replace("**", "").strip()
        
        # Extract abstract
        abstract_match = re.search(r'###\s*논문\s*초록\s*\(Abstract\)\s*([\s\S]+?)(?=###|$)', section)
        abstract = ""
        if abstract_match:
            abstract = abstract_match.group(1).replace('<jats:p>', '').replace('</jats:p>', '').replace('>', '').replace('ABSTRACT', '').strip()
        
        # Extract AI analysis
        # Look for the header and capture until the end of the section
        analysis_match = re.search(r'###\s*AI\s*심층\s*분석\s*요약\s*(?:.*)\n+([\s\S]+)', section)
        analysis = ""
        if analysis_match:
            analysis = analysis_match.group(1).strip()
        
        papers.append({
            "Journal": journal,
            "Title": title,
            "Authors": authors,
            "Date": date,
            "URL": url,
            "Abstract": abstract,
            "AI_Analysis": clean_text(analysis),
            "Category": category,
            "YearMonth": datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m") if re.match(r'\d{4}-\d{1,2}-\d{1,2}', date) else "2026-04"
        })
    return papers

ALLOWED_FINANCE_JOURNALS = [
    "the journal of finance",
    "journal of financial economics",
    "the review of financial studies",
    "journal of financial and quantitative analysis",
    "review of finance"
]

FINANCE_BLACKLIST = ["working paper", "nber", "ssrn", "preprint"]

def merge_all():
    base_file = "backfill_state.json"
    if os.path.exists(base_file):
        with open(base_file, "r", encoding="utf-8") as f:
            all_papers = json.load(f)
    else:
        all_papers = []

    # Map URLs to existing paper objects for easy access/update
    existing_map = {p["URL"]: p for p in all_papers if "URL" in p}

    def add_or_update(new_paper):
        url = new_paper.get("URL")
        if not url: return
        
        if url in existing_map:
            # Overwrite if current analysis is a failure or empty
            current_analysis = existing_map[url].get("AI_Analysis", "")
            if "분석 실패" in current_analysis or not current_analysis.strip():
                existing_map[url].update(new_paper)
        else:
            all_papers.append(new_paper)
            existing_map[url] = new_paper

    # Filter out existing working papers from previous runs
    all_papers = [
        p for p in all_papers 
        if not (p.get("Category") == "Finance" and any(b in p.get("Journal", "").lower() or b in p.get("Title", "").lower() for b in FINANCE_BLACKLIST))
    ]

    # 1. Finance CSV (Purge and Re-import)
    # Clear existing Finance entries to remove "Unknown Journal" leftovers
    all_papers = [p for p in all_papers if p.get("Category") != "Finance"]
    # Re-build existing_map after purge to allow fresh import
    existing_map = {p["URL"]: p for p in all_papers if "URL" in p}

    finance_file = "finance_papers_20260411.csv"
    if os.path.exists(finance_file):
        # Use utf-8-sig to automatically remove BOM if present
        with open(finance_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Row keys are now clean (no BOM)
                # Map to standard keys if necessary, but DictReader uses headers directly
                journal = row.get("Journal", "").strip()
                title = row.get("Title", "").strip()
                url = row.get("URL", "").strip()
                
                # Strict White-List Check for 5 Top Journals
                is_top_5 = any(tj in journal.lower() for tj in ALLOWED_FINANCE_JOURNALS)
                # Black-list for working papers
                is_working_paper = any(b in journal.lower() or b in title.lower() or b in url.lower() for b in ["working paper", "nber", "ssrn", "preprint"])
                
                if is_top_5 and not is_working_paper:
                    date_val = row.get("Date", "2026-04-11")
                    year_month = "2026-04"
                    try:
                        # Normalize date format if it's 2026-4-8
                        dt_obj = datetime.strptime(date_val, "%Y-%m-%d")
                        year_month = dt_obj.strftime("%Y-%m")
                    except: 
                        try:
                            # Try 2026-4-8 format
                            dt_obj = datetime.strptime(date_val, "%Y-%n-%j") # Incorrect pattern, just fallback
                        except: pass
                    
                    paper_obj = {
                        "Journal": journal,
                        "Title": title,
                        "Authors": row.get("Authors", "Unknown"),
                        "Date": date_val,
                        "URL": url,
                        "Abstract": clean_text(row.get("Abstract", "")),
                        "AI_Analysis": clean_text(row.get("AI_Analysis", "")),
                        "Category": "Finance",
                        "YearMonth": year_month
                    }
                    add_or_update(paper_obj)

    # 2. Marketing MD
    marketing_file = "marketing_papers_20260411.md"
    if os.path.exists(marketing_file):
        m_papers = parse_markdown_papers(marketing_file, "Marketing")
        for p in m_papers:
            add_or_update(p)

    # 3. Accounting Manual JSON
    accounting_file = "scripts/accounting_manual_20260411.json"
    if os.path.exists(accounting_file):
        with open(accounting_file, "r", encoding="utf-8") as f:
            a_papers = json.load(f)
            for p in a_papers:
                date_val = p["Date"]
                p["YearMonth"] = datetime.strptime(date_val, "%Y-%m-%d").strftime("%Y-%m")
                p["AI_Analysis"] = clean_text(p["AI_Analysis"])
                add_or_update(p)

    # Final sweep to ensure ALL papers are cleaned and have Category
    for p in all_papers:
        p["AI_Analysis"] = clean_text(p.get("AI_Analysis", ""))
        if "Category" not in p:
            j = p.get("Journal", "").lower()
            if "marketing" in j: p["Category"] = "Marketing"
            elif any(tj in j for tj in ALLOWED_FINANCE_JOURNALS): p["Category"] = "Finance"
            elif "accounting" in j: p["Category"] = "Accounting"
            else: p["Category"] = "Marketing" 

    with open(base_file, "w", encoding="utf-8") as f:
        json.dump(all_papers, f, ensure_ascii=False, indent=2)
    
    print(f"Merged total of {len(all_papers)} papers into {base_file}")

if __name__ == "__main__":
    merge_all()
