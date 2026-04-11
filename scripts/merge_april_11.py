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
    
    # Split by paper (double delimiter)
    sections = re.split(r'##\s+', content)[1:]
    papers = []
    
    for section in sections:
        lines = section.strip().split('\n')
        title = lines[0].strip()
        
        journal = ""
        authors = ""
        date = ""
        url = ""
        
        # Look for metadata in <aside> or bullet points
        journal_match = re.search(r'저널명:\s*(.+)', section)
        authors_match = re.search(r'저자:\s*(.+)', section)
        date_match = re.search(r'출판일:\s*(.+)', section)
        url_match = re.search(r'링크:\s*(https?://\S+)', section)
        
        if journal_match: journal = journal_match.group(1).strip()
        if authors_match: authors = authors_match.group(1).strip()
        if date_match: date = date_match.group(1).strip()
        if url_match: url = url_match.group(1).strip()
        
        # Extract abstract
        abstract_match = re.search(r'### 논문 초록 \(Abstract\)\n*(?:>.*(?:\n>.*)*)', section)
        abstract = ""
        if abstract_match:
            abstract = abstract_match.group(0).replace('### 논문 초록 (Abstract)\n', '').replace('> ', '').replace('>', '').strip()
        
        # Extract AI analysis
        analysis_match = re.search(r'### AI 심층 분석 요약\n*([\s\S]+)', section)
        analysis = ""
        if analysis_match:
            analysis = analysis_match.group(1).strip()
            # If it has subheadings A, B, C, include them
        
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

def merge_all():
    base_file = "backfill_state.json"
    if os.path.exists(base_file):
        with open(base_file, "r", encoding="utf-8") as f:
            all_papers = json.load(f)
    else:
        all_papers = []

    # Clean existing papers
    for p in all_papers:
        p["AI_Analysis"] = clean_text(p.get("AI_Analysis", ""))

    existing_urls = {p["URL"] for p in all_papers if "URL" in p}

    # 1. Finance CSV
    finance_file = "finance_papers_20260411.csv"
    if os.path.exists(finance_file):
        with open(finance_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["URL"] not in existing_urls:
                    date_val = row["Date"]
                    year_month = "2026-04"
                    try:
                        year_month = datetime.strptime(date_val, "%Y-%m-%d").strftime("%Y-%m")
                    except: pass
                    
                    row["AI_Analysis"] = clean_text(row["AI_Analysis"])
                    row["Category"] = "Finance"
                    row["YearMonth"] = year_month
                    all_papers.append(row)
                    existing_urls.add(row["URL"])

    # 2. Marketing MD
    marketing_file = "marketing_papers_20260411.md"
    if os.path.exists(marketing_file):
        m_papers = parse_markdown_papers(marketing_file, "Marketing")
        for p in m_papers:
            if p["URL"] not in existing_urls:
                all_papers.append(p)
                existing_urls.add(p["URL"])

    # 3. Accounting Manual JSON
    accounting_file = "scripts/accounting_manual_20260411.json"
    if os.path.exists(accounting_file):
        with open(accounting_file, "r", encoding="utf-8") as f:
            a_papers = json.load(f)
            for p in a_papers:
                if p["URL"] not in existing_urls:
                    date_val = p["Date"]
                    p["YearMonth"] = datetime.strptime(date_val, "%Y-%m-%d").strftime("%Y-%m")
                    p["AI_Analysis"] = clean_text(p["AI_Analysis"])
                    all_papers.append(p)
                    existing_urls.add(p["URL"])

    # Final sweep to ensure ALL papers are cleaned and have Category
    for p in all_papers:
        p["AI_Analysis"] = clean_text(p.get("AI_Analysis", ""))
        # Assign Category if missing based on patterns if possible, or just leave as is if old
        if "Category" not in p:
            j = p.get("Journal", "").lower()
            if "marketing" in j: p["Category"] = "Marketing"
            elif "finance" in j or "financial" in j: p["Category"] = "Finance"
            elif "accounting" in j: p["Category"] = "Accounting"
            else: p["Category"] = "Marketing" # Default for old backfill

    with open(base_file, "w", encoding="utf-8") as f:
        json.dump(all_papers, f, ensure_ascii=False, indent=2)
    
    print(f"Merged total of {len(all_papers)} papers into {base_file}")

if __name__ == "__main__":
    merge_all()
