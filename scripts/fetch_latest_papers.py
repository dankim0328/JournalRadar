import requests
import json
import os
import datetime
import re
import sys
import argparse
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from paper_metadata import enrich_abstract

DATA_ROOT = Path(__file__).resolve().parents[1] / "site/public/data"

def published_titles(category):
    titles = set()
    for path in (DATA_ROOT / category.lower()).glob("*/W*.json"):
        for paper in json.loads(path.read_text(encoding="utf-8")).get("papers", []):
            titles.add(paper.get("title", "").strip().lower())
    return titles


def default_from_date(today):
    # Recover missed runs, ignoring future issue dates in the stored data.
    dates = []
    for path in (DATA_ROOT / "marketing").glob("*/W*.json"):
        for paper in json.loads(path.read_text(encoding="utf-8")).get("papers", []):
            try:
                dt = datetime.date.fromisoformat(paper.get("date", ""))
                if dt <= today:
                    dates.append(dt)
            except ValueError:
                pass
    latest = max(dates) if dates else today
    return (latest - datetime.timedelta(days=21)).isoformat()


sys.stdout.reconfigure(encoding='utf-8')

BACKFILL_FILE = os.path.join(os.path.dirname(__file__), "..", ".weekly_batch.json")

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

def fetch_domain_papers(category, config, from_date, until_date=None):
    print(f"\n[{category}] {from_date} 이후 최신 논문 수집 중...")
    papers = []
    headers = {"User-Agent": "JournalRadar/1.0 (https://github.com/dankim0328/JournalRadar)"}
    seen = set()
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=Retry(
        total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])))
    until_date = until_date or datetime.date.today().isoformat()
    
    for issn in config["issns"]:
        url = f"https://api.crossref.org/works?filter=issn:{issn},from-pub-date:{from_date},until-pub-date:{until_date},type:journal-article&rows=1000"
        try:
            response = session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            message = data["message"]
            items = message["items"]
            if message.get("total-results", len(items)) > len(items):
                raise RuntimeError(f"ISSN {issn}: more than 1000 results; use a shorter date range")
            
            for item in items:
                title = item.get("title", [""])[0] if item.get("title") else "No title"
                if title == "No title" or title.strip().lower() in seen: continue
                
                authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in item.get("author", [])]
                author_str = ", ".join(authors) if authors else "Unknown"
                
                pub_date_parts = item.get("published-online", item.get("published-print", item.get("published", {}))).get("date-parts", [[None]])[0]
                if not pub_date_parts or not pub_date_parts[0]:
                    raise ValueError(f"Missing publication date for {title}")
                # Month-only dates are assigned to the first day, as in the converter.
                pub_date = datetime.date(*((pub_date_parts + [1, 1])[:3])).isoformat()
                if pub_date > until_date:
                    continue
                
                url_link = item.get("URL", "")
                doi = item.get("DOI", "")
                
                abstract = item.get("abstract", "초록(Abstract) 정보가 제공되지 않았습니다.")
                abstract = re.sub(r'<[^>]+>', '', abstract or "")
                
                journal_name = item.get("container-title", ["Unknown Journal"])[0] if item.get("container-title") else "Unknown Journal"
                
                # 타겟 저널 필터링
                is_target = any(tj.lower() in journal_name.lower() for tj in config["journals"])
                if not is_target: continue
                
                # 워킹페이퍼 등 필터 (주로 Finance)
                is_working_paper = any(b in journal_name.lower() or b in title.lower() for b in ["working paper", "nber", "ssrn", "preprint"])
                if is_working_paper: continue
                
                abstract = enrich_abstract(abstract, doi)
                seen.add(title.strip().lower())
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
            raise RuntimeError(f"Crossref fetch failed for {issn}") from e
            
    return papers

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-date", default=os.environ.get("FROM_DATE") or None)
    parser.add_argument("--until-date", default=os.environ.get("UNTIL_DATE") or None)
    args = parser.parse_args()
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
    until_date = args.until_date or today.isoformat()
    datetime.date.fromisoformat(until_date)
    if until_date > today.isoformat():
        raise ValueError("until-date cannot be in the future")
    from_date = args.from_date or default_from_date(today)
    datetime.date.fromisoformat(from_date)  # Reject malformed manual input.
    if from_date > until_date:
        raise ValueError("from-date cannot be in the future")
    # Weekly JSON is the durable source of truth. Never reuse a stale local batch.
    all_papers = []
    existing_titles = set()

    new_papers_count = 0
    
    for category, config in DOMAINS.items():
        fetched = fetch_domain_papers(category, config, from_date, until_date)
        for p in fetched:
            if p["Title"].lower() not in existing_titles:
                all_papers.append(p)
                existing_titles.add(p["Title"].lower())
                new_papers_count += 1
                
    print(f"\n수집한 논문 수 (기존 논문 초록 갱신 포함): {new_papers_count}편")
    
    # 정렬 및 저장
    all_papers.sort(key=lambda x: (x.get("YearMonth", ""), x.get("Title", "")))
    
    with open(BACKFILL_FILE, "w", encoding="utf-8") as f:
        json.dump(all_papers, f, ensure_ascii=False, indent=2)
        
    status = {"fromDate": from_date, "throughDate": until_date,
              "collectedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "fetchedPapers": len(all_papers), "aiEnabled": False}
    Path(BACKFILL_FILE).with_name(".weekly_collection_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✅ 논문 및 초록 수집 완료 (AI 호출 없음)")

if __name__ == "__main__":
    main()
