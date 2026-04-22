import requests
import json
import time
import os
import datetime
import argparse
from notion_client import Client
import sys
sys.stdout.reconfigure(encoding='utf-8')

from gemini_safe_client import GeminiSafeClient, truncate_text, enrich_abstract, ANTI_HALLUCINATION_INSTRUCTION
import re

# ==================== CONFIGURATION ====================
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID", "")

# 안전장치가 적용된 Gemini 클라이언트 초기화
gemini_client = GeminiSafeClient()

TARGET_JOURNAL_NAMES = [
    "Journal of Marketing",
    "Journal of Marketing Research",
    "Journal of Consumer Research",
    "Marketing Science",
    "Quantitative Marketing and Economics"
]

JOURNAL_ISSNS = [
    "0022-2429", "1547-7185", 
    "0022-2437", "1547-7193", 
    "0093-5301", "1537-5277", 
    "0732-2399", "1526-548X", 
    "1570-7156", "1573-7155"  
]

STATE_FILE = "backfill_custom_state.json"

def get_year_month(date_str):
    if date_str == "Unknown":
        return "0000-Unknown"
    parts = str(date_str).split('-')
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1].zfill(2)}"
    elif len(parts) == 1:
        return f"{parts[0]}-01"
    return "0000-Unknown"

def fetch_period_papers(from_date, until_date):
    print(f"[1/3] Crossref에서 {from_date} ~ {until_date} 기간의 타겟 논문 데이터를 일괄 수집합니다...")
    
    papers = []
    headers = {"User-Agent": "AcademicBotBackfill/1.0 (mailto:your_email@example.com)"}
    
    for issn in JOURNAL_ISSNS:
        # 특정 기간만을 타겟팅하는 필터 적용
        url = f"https://api.crossref.org/works?filter=issn:{issn},from-pub-date:{from_date},until-pub-date:{until_date}&rows=1000"
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"ISSN {issn} 요청 실패: {response.status_code}")
                continue
                
            data = response.json()
            items = data.get("message", {}).get("items", [])
            
            for item in items:
                title = item.get("title", [""])[0] if item.get("title") else "No title"
                authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in item.get("author", [])]
                author_str = ", ".join(authors) if authors else "Unknown"
                
                pub_date_parts = item.get("published-online", item.get("published-print", item.get("published", {}))).get("date-parts", [[None]])[0]
                pub_date = "-".join(map(str, pub_date_parts)) if pub_date_parts and pub_date_parts[0] else "Unknown"
                
                url_link = item.get("URL", "")
                doi = item.get("DOI", "")
                abstract = item.get("abstract", "초록(Abstract) 정보가 제공되지 않았습니다.")
                
                # HTML 태그 제거 + OpenAlex fallback 적용
                abstract = re.sub(r'<[^>]+>', '', abstract)
                abstract = enrich_abstract(abstract, doi)
                
                journal_name = item.get("container-title", ["Unknown Journal"])[0] if item.get("container-title") else "Unknown Journal"
                
                # 타겟 저널 필터링
                is_target = False
                for tj in TARGET_JOURNAL_NAMES:
                    if tj.lower() in journal_name.lower():
                        is_target = True
                        break
                        
                if not is_target:
                    continue
                
                papers.append({
                    "Journal": journal_name,
                    "Title": title,
                    "Authors": author_str,
                    "Date": pub_date,
                    "URL": url_link,
                    "Abstract": abstract,
                    "YearMonth": get_year_month(pub_date),
                    "AI_Analysis": "" # 상태 변수
                })
        except Exception as e:
            print(f"Error fetching {issn}: {e}")
            
    # 제목 기준 중복 제거
    unique_papers = []
    seen = set()
    for p in papers:
        if p["Title"] not in seen and p["Title"] != "No title":
            unique_papers.append(p)
            seen.add(p["Title"])
            
    unique_papers.sort(key=lambda x: (x["YearMonth"], x["Title"]))
            
    print(f"✅ 총 {len(unique_papers)}편의 타겟 논문을 찾아냈습니다!")
    return unique_papers

def analyze_paper_with_gemini(paper):
    safe_abstract = truncate_text(paper.get('Abstract', ''))
    
    prompt = f"""당신은 세계적인 마케팅 학술 연구 보조 AI입니다.
아래 마케팅 탑 저널 논문 정보를 바탕으로 다음 3가지를 분석해 주세요.

[논문 정보]
- 저널명: {paper.get('Journal')}
- 논문 제목: {paper.get('Title')}
- 저자: {paper.get('Authors')}
- 초록(Abstract): {safe_abstract}

[요구사항]
A. 논문 요약 (Summary): 이 논문의 핵심 내용을 요약해 주세요.
B. 연구적 의의 (Academic Significance): 기존 연구나 논리의 반박인지, 새로운 패러다임 제시인지 등 현 시대적 상황과 연관 지어 분석해 주세요.
C. 저자 백그라운드 (Author Background): 저자들의 주요 연구 분야, 학력 등 배경 정보에 대해 당신이 아는 선에서 설명해 주세요.

{ANTI_HALLUCINATION_INSTRUCTION}

[출력 형식 (반드시 아래 구조 유지)]
===KOREAN===
A. 논문 요약:
[내용]

B. 연구적 의의:
[내용]

C. 저자 백그라운드:
[내용]

===ENGLISH===
A. Summary:
[내용]

B. Academic Significance:
[내용]

C. Author Background:
[내용]
"""
    return gemini_client.analyze(prompt, cache_key_title=paper.get('Title', ''))


def clean_markdown(text):
    if not text: return ""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = text.replace('###', '')
    text = text.replace('##', '')
    text = re.sub(r'^-\s+', '• ', text, flags=re.MULTILINE)
    return text.strip()

def append_paper_blocks(blocks, paper, analysis_text, header_title="AI 심층 분석 요약"):
    blocks.append({
        "object": "block", "type": "divider", "divider": {}
    })
    blocks.append({
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": paper.get('Title', 'No Title')}}]}
    })
    
    meta_text = f"저널명: {paper.get('Journal', 'Unknown')}\n저자: {paper.get('Authors', '')}\n출판일: {paper.get('Date', '')}\n링크: {paper.get('URL', '')}"
    blocks.append({
        "object": "block", "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": meta_text}}],
            "icon": {"type": "emoji", "emoji": "🔗"},
            "color": "blue_background"
        }
    })
    
    blocks.append({
        "object": "block", "type": "heading_3",
        "heading_3": {"rich_text": [{"type": "text", "text": {"content": "초록 (Abstract)"}}]}
    })
    
    abs_text = str(paper.get('Abstract', ''))[:1990] + ("..." if len(str(paper.get('Abstract', ''))) > 1990 else "")
    blocks.append({
        "object": "block", "type": "quote",
        "quote": {"rich_text": [{"type": "text", "text": {"content": abs_text}}]}
    })
    
    blocks.append({
        "object": "block", "type": "heading_3",
        "heading_3": {"rich_text": [{"type": "text", "text": {"content": header_title}}]}
    })
    
    if analysis_text:
        for j in range(0, len(analysis_text), 1990):
            chunk = analysis_text[j:j+1990]
            blocks.append({
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}
            })

def upload_month_to_notion(month_label, papers_in_month, custom_title=""):
    print(f"\n🚀 Notion 업로드 시작: {month_label} (총 {len(papers_in_month)}편)")
    notion = Client(auth=NOTION_TOKEN)
    title = f"Top Marketing Journals ({custom_title} {month_label})"

    page_kor = notion.pages.create(
        parent={"page_id": NOTION_PARENT_PAGE_ID},
        properties={"title": [{"text": {"content": title}}]}
    )
    
    page_eng = notion.pages.create(
        parent={"page_id": NOTION_PARENT_PAGE_ID},
        properties={"title": [{"text": {"content": f"[ENG] {title}"}}]}
    )
    
    blocks_kor = []
    blocks_eng = []
    
    blocks_kor.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"총 {len(papers_in_month)}건의 누락된(Missing) 논문 백필 데이터입니다."}}]}})
    blocks_eng.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"A total of {len(papers_in_month)} missing papers backfilled."}}]}})
    
    for paper in papers_in_month:
        analysis = paper.get('AI_Analysis', '')
        parts = analysis.split('===ENGLISH===')
        kor_raw = parts[0].replace('===KOREAN===', '').strip()
        kor_text = clean_markdown(kor_raw)
        
        eng_raw = parts[1].strip() if len(parts) > 1 else kor_raw
        eng_text = clean_markdown(eng_raw)
        
        append_paper_blocks(blocks_kor, paper, kor_text, header_title="AI 심층 분석 요약")
        append_paper_blocks(blocks_eng, paper, eng_text, header_title="AI Insight & Analysis")
        
    blocks_kor.append({"object": "block", "type": "divider", "divider": {}})
    blocks_eng.append({"object": "block", "type": "divider", "divider": {}})

    for i in range(0, len(blocks_kor), 100):
        try:
            notion.blocks.children.append(block_id=page_kor["id"], children=blocks_kor[i:i+100])
        except Exception as e: print("Batch error Kor:", e)
        
    for i in range(0, len(blocks_eng), 100):
        try:
            notion.blocks.children.append(block_id=page_eng["id"], children=blocks_eng[i:i+100])
        except Exception as e: print("Batch error Eng:", e)
        
    print(f"✅ {month_label} 업로드 완료!")

def main():
    parser = argparse.ArgumentParser(description="특정 기간 논문 백필 스크립트")
    parser.add_argument("--from-date", type=str, default="2026-03-01", help="검색 시작일 (YYYY-MM-DD)")
    parser.add_argument("--until-date", type=str, default="2026-04-07", help="검색 종료일 (YYYY-MM-DD)")
    args = parser.parse_args()
    
    print("==================================================")
    print(f" 🛠 누락된 논문 데이터 백필 작업 ({args.from_date} ~ {args.until_date})")
    print("==================================================")
    print("- 대상: 지정된 기간 내 특정 타겟 저널 논문")
    print("- 적용: max_output_tokens=1000 제한 (비용/토큰 최적화)")
    print("--------------------------------------------------\n")
    
    state_papers = []
    # 기간별 분리기위해 파일이름을 동적으로 생성
    current_state_file = f"backfill_{args.from_date}_{args.until_date}_state.json"
    
    if os.path.exists(current_state_file):
        with open(current_state_file, "r", encoding="utf-8") as f:
            state_papers = json.load(f)
            print(f"[안내] 기존에 분석 중단된 내역({len(state_papers)}편)을 불러옵니다.")
    else:
        state_papers = fetch_period_papers(args.from_date, args.until_date)
        with open(current_state_file, "w", encoding="utf-8") as f:
            json.dump(state_papers, f, ensure_ascii=False, indent=2)

    total_count = len(state_papers)
    to_analyze = [p for p in state_papers if not p.get("AI_Analysis", "").strip() or p["AI_Analysis"] == "AI 분석 실패." or p["AI_Analysis"] == "AI Analysis Failed."]
    done_count = total_count - len(to_analyze)

    print(f"\n[2/3] 전체 {total_count}편 중 완료된 {done_count}편 제외, {len(to_analyze)}편 AI 분석 진행.")

    for i, paper in enumerate(state_papers):
        current_status = paper.get("AI_Analysis", "").strip()
        if current_status and current_status not in ["AI 분석 실패.", "AI Analysis Failed."]:
            continue
            
        progress = f"[{done_count + 1} / {total_count}]"
        print(f"분석 중 {progress}: {paper['Title'][:50]}... ({paper['YearMonth']})")
        
        analysis_text = analyze_paper_with_gemini(paper)
        paper["AI_Analysis"] = analysis_text
        done_count += 1
        
        with open(current_state_file, "w", encoding="utf-8") as f:
            json.dump(state_papers, f, ensure_ascii=False, indent=2)
            
        time.sleep(35)
        
    print("\n[3/3] AI 분석 완료. 노션 업로드 시작.")
    
    grouped_papers = {}
    for p in state_papers:
        ym = p["YearMonth"]
        if ym not in grouped_papers:
            grouped_papers[ym] = []
        grouped_papers[ym].append(p)
        
    sorted_months = sorted(list(grouped_papers.keys()))
    
    # 해당 기간 타겟 업로드 전용 로그
    UPLOAD_LOG = f"backfill_upload_{args.from_date}_{args.until_date}_log.txt"
    uploaded_months = set()
    if os.path.exists(UPLOAD_LOG):
        with open(UPLOAD_LOG, "r", encoding="utf-8") as f:
            uploaded_months = set([line.strip() for line in f.readlines() if line.strip()])
            
    custom_title = f"Missed {args.from_date.replace('2026-','')}~[{args.until_date.replace('2026-','')}] "
    for month in sorted_months:
        if month in uploaded_months:
            print(f"- {month} 는 이미 노션에 업로드되어 건너뜁니다.")
            continue
            
        papers_in_month = grouped_papers[month]
        upload_month_to_notion(month, papers_in_month, custom_title=custom_title)
        
        uploaded_months.add(month)
        with open(UPLOAD_LOG, "a", encoding="utf-8") as f:
            f.write(month + "\n")
            
    print("\n==================================================")
    print(" 🎉 누락 구간 백필이 완벽하게 완료되었습니다!")
    print("==================================================")

if __name__ == "__main__":
    main()
