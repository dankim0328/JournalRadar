import requests
import json
import os
import datetime
import re
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from gemini_safe_client import enrich_abstract

sys.stdout.reconfigure(encoding='utf-8')

BACKFILL_FILE = os.path.join(os.path.dirname(__file__), "..", "backfill_state.json")

DOMAINS = {
    "Marketing": {
        "journals": ["Journal of Marketing", "Journal of Marketing Research", "Journal of Consumer Research", "Marketing Science", "Quantitative Marketing and Economics"],
        "issns": ["0022-2429", "1547-7185", "0022-2437", "1547-7193", "0093-5301", "1537-5277", "0732-2399", "1526-548X", "1570-7156", "1573-7155"]
    }
}

def get_year_month(date_str):
    if not date_str or date_str == "Unknown": return "0000-Unknown"
    parts = str(date_str).split('-')
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1].zfill(2)}"
    elif len(parts) == 1:
        return f"{parts[0]}-01"
    return "0000-Unknown"

def fetch_domain_papers(category, config, from_date):
    print(f"\n[{category}] {from_date} 이후 최신 논문 수집 중...")
    papers = []
    headers = {"User-Agent": "AcademicBotBackfill/1.0 (mailto:your_email@example.com)"}
    
    for issn in config["issns"]:
        url = f"https://api.crossref.org/works?filter=issn:{issn},from-pub-date:{from_date}&rows=1000"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200: continue
            data = response.json()
            items = data.get("message", {}).get("items", [])
            
            for item in items:
                title = item.get("title", [""])[0] if item.get("title") else "No title"
                if title == "No title": continue
                
                authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in item.get("author", [])]
                author_str = ", ".join(authors) if authors else "Unknown"
                
                pub_date_parts = item.get("published-online", item.get("published-print", item.get("published", {}))).get("date-parts", [[None]])[0]
                pub_date = "-".join(map(str, pub_date_parts)) if pub_date_parts and pub_date_parts[0] else "Unknown"
                
                url_link = item.get("URL", "")
                doi = item.get("DOI", "")
                
                abstract = item.get("abstract", "초록(Abstract) 정보가 제공되지 않았습니다.")
                abstract = re.sub(r'<[^>]+>', '', abstract)
                abstract = enrich_abstract(abstract, doi)
                
                journal_name = item.get("container-title", ["Unknown Journal"])[0] if item.get("container-title") else "Unknown Journal"
                
                # 타겟 저널 필터링
                is_target = any(tj.lower() in journal_name.lower() for tj in config["journals"])
                if not is_target: continue
                
                # 워킹페이퍼 등 필터 (주로 Finance)
                is_working_paper = any(b in journal_name.lower() or b in title.lower() for b in ["working paper", "nber", "ssrn", "preprint"])
                if is_working_paper: continue
                
                papers.append({
                    "Journal": journal_name,
                    "Title": title,
                    "Authors": author_str,
                    "Date": pub_date,
                    "URL": url_link,
                    "Abstract": abstract,
                    "YearMonth": get_year_month(pub_date),
                    "Category": category,
                    "AI_Analysis": ""
                })
        except Exception as e:
            print(f"Error fetching {issn}: {e}")
            
    return papers

def main():
    if os.path.exists(BACKFILL_FILE):
        with open(BACKFILL_FILE, "r", encoding="utf-8") as f:
            all_papers = json.load(f)
    else:
        all_papers = []

    print(f"기존 저장된 논문 수: {len(all_papers)}편")
    existing_titles = {p["Title"].lower() for p in all_papers if "Title" in p}
    
    # 3주 전 논문부터 수집 (누락 방지)
    last_week = datetime.date.today() - datetime.timedelta(days=21)
    from_date = last_week.strftime("%Y-%m-%d")
    
    new_papers_count = 0
    
    for category, config in DOMAINS.items():
        fetched = fetch_domain_papers(category, config, from_date)
        for p in fetched:
            if p["Title"].lower() not in existing_titles:
                all_papers.append(p)
                existing_titles.add(p["Title"].lower())
                new_papers_count += 1
                
    print(f"\n새로 추가된 논문 수: {new_papers_count}편")
    
    # 정렬 및 저장
    all_papers.sort(key=lambda x: (x.get("YearMonth", ""), x.get("Title", "")))
    
    with open(BACKFILL_FILE, "w", encoding="utf-8") as f:
        json.dump(all_papers, f, ensure_ascii=False, indent=2)
        
    print("✅ 데이터 업데이트 완료!")

if __name__ == "__main__":
    main()
