import requests
import pandas as pd
import schedule
import time
import datetime
import os
import sys
import re
sys.stdout.reconfigure(encoding='utf-8')

import google.generativeai as genai
from notion_client import Client

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID", "")
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(model_name="gemini-2.5-pro")

TARGET_JOURNAL_NAMES = ["Journal of Marketing", "Journal of Marketing Research", "Journal of Consumer Research", "Marketing Science", "Quantitative Marketing and Economics"]
JOURNAL_ISSNS = ["0022-2429", "1547-7185", "0022-2437", "1547-7193", "0093-5301", "1537-5277", "0732-2399", "1526-548X", "1570-7156", "1573-7155"]

def fetch_recent_papers():
    print(f"[{datetime.datetime.now()}] Crossref에서 최근 논문을 수집합니다...")
    today = datetime.date.today()
    last_week = today - datetime.timedelta(days=7)
    from_date = last_week.strftime("%Y-%m-%d")
    papers = []
    headers = {"User-Agent": "AcademicResearchBot/1.0 (mailto:your_email@example.com)"}
    
    for issn in JOURNAL_ISSNS:
        url = f"https://api.crossref.org/works?filter=issn:{issn},from-pub-date:{from_date}"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200: continue
            data = response.json()
            items = data.get("message", {}).get("items", [])
            for item in items:
                title = item.get("title", [""])[0] if item.get("title") else "No title"
                authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in item.get("author", [])]
                author_str = ", ".join(authors) if authors else "Unknown"
                pub_date_parts = item.get("published-online", item.get("published-print", item.get("published", {}))).get("date-parts", [[None]])[0]
                pub_date = "-".join(map(str, pub_date_parts)) if pub_date_parts and pub_date_parts[0] else "Unknown"
                url_link = item.get("URL", "")
                
                # HTML 태그 완전 제거
                abstract = item.get("abstract", "초록(Abstract) 정보가 제공되지 않았습니다.")
                abstract = re.sub(r'<[^>]+>', '', abstract)
                
                journal_name = item.get("container-title", ["Unknown Journal"])[0] if item.get("container-title") else "Unknown Journal"
                
                is_target = False
                for tj in TARGET_JOURNAL_NAMES:
                    if tj.lower() in journal_name.lower():
                        is_target = True
                        break
                if not is_target: continue
                
                papers.append({
                    "Journal": journal_name,
                    "Title": title,
                    "Authors": author_str,
                    "Date": pub_date,
                    "URL": url_link,
                    "Abstract": abstract
                })
        except Exception: pass
            
    unique_papers = []
    seen_titles = set()
    for p in papers:
        if p["Title"] not in seen_titles and p["Title"] != "No title":
            unique_papers.append(p)
            seen_titles.add(p["Title"])
            
    return unique_papers

def analyze_paper_with_gemini(paper):
    prompt = f"""당신은 세계적인 마케팅 학술 연구 보조 AI입니다.
아래 마케팅 탑 저널 논문 정보를 바탕으로 다음 3가지를 분석해 주세요.

[논문 정보]
- 저널명: {paper.get('Journal', 'Unknown')}
- 논문 제목: {paper['Title']}
- 저자: {paper['Authors']}
- 초록(Abstract): {paper['Abstract']}

A. 논문 요약 (Summary): 이 논문의 핵심 내용을 요약해 주세요.
B. 연구적 의의 (Academic Significance): 기존 연구나 논리의 반박인지, 새로운 패러다임 제시인지 등 현 시대적 상황과 연관 지어 분석해 주세요.
C. 저자 백그라운드 (Author Background): 저자들의 주요 연구 분야, 학력 등 배경 정보에 대해 당신이 아는 선에서 설명해 주세요.

[중요 제약 조건]
- 마크다운 강조 표시(**)를 절대 사용하지 마세요. 
- 전문적이고 자연스러운 문장으로 작성해 주세요.

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
    try:
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text
    except Exception as e:
        return "===KOREAN===
AI 분석 실패.
===ENGLISH===
AI Analysis Failed."

def save_to_local(papers, analyzed_results):
    today_str = datetime.date.today().strftime("%Y%m%d")
    csv_filename = f"marketing_papers_{today_str}.csv"
    
    merged_data = []
    for paper, analysis in zip(papers, analyzed_results):
        paper_copy = paper.copy()
        paper_copy["AI_Analysis"] = analysis
        merged_data.append(paper_copy)
        
    df = pd.DataFrame(merged_data)
    df.to_csv(csv_filename, index=False, encoding="utf-8-sig")

def clean_markdown(text):
    if not text: return ""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = text.replace('###', '')
    text = text.replace('##', '')
    text = re.sub(r'^-\s+', '• ', text, flags=re.MULTILINE)
    return text.strip()

def append_paper_blocks(blocks, paper, analysis_text, header_title):
    blocks.append({"object": "block", "type": "divider", "divider": {}})
    blocks.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": paper.get('Title', 'No Title')}}]}})
    
    journal_str = "저널명" if "한국어" in header_title or "심층" in header_title else "Journal"
    author_str = "저자" if "한국어" in header_title or "심층" in header_title else "Authors"
    date_str = "출판일" if "한국어" in header_title or "심층" in header_title else "Published"
    link_str = "링크" if "한국어" in header_title or "심층" in header_title else "Link"
    abs_title = "초록 (Abstract)" if "한국어" in header_title or "심층" in header_title else "Abstract"
    
    meta_text = f"{journal_str}: {paper.get('Journal', 'Unknown')}\n{author_str}: {paper.get('Authors', '')}\n{date_str}: {paper.get('Date', '')}\n{link_str}: {paper.get('URL', '')}"
    blocks.append({"object": "block", "type": "callout", "callout": {"rich_text": [{"type": "text", "text": {"content": meta_text}}], "icon": {"type": "emoji", "emoji": "🔗"}, "color": "blue_background"}})
    
    blocks.append({"object": "block", "type": "heading_3", "heading_3": {"rich_text": [{"type": "text", "text": {"content": abs_title}}]}})
    abs_text = str(paper.get('Abstract', ''))[:1990] + ("..." if len(str(paper.get('Abstract', ''))) > 1990 else "")
    blocks.append({"object": "block", "type": "quote", "quote": {"rich_text": [{"type": "text", "text": {"content": abs_text}}]}})
    
    blocks.append({"object": "block", "type": "heading_3", "heading_3": {"rich_text": [{"type": "text", "text": {"content": header_title}}]}})
    
    paragraphs = analysis_text.split('\n\n')
    for p in paragraphs:
        if not p.strip(): continue
        chunks = [p[i:i+1900] for i in range(0, len(p), 1900)]
        for chunk in chunks:
            if chunk.strip().startswith("A.") or chunk.strip().startswith("B.") or chunk.strip().startswith("C."):
                blocks.append({"object": "block", "type": "heading_3", "heading_3": {"rich_text": [{"type": "text", "text": {"content": chunk.strip()}}]}})
            else:
                blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk.strip()}}]}})

def save_to_notion(papers, analyzed_results):
    if NOTION_TOKEN == "여기에_노션_통합토큰_입력" or NOTION_PAGE_ID == "":
        return

    print("🚀 Notion 페이지 2개(한국어/영어)를 생성하여 업로드합니다...")
    try:
        notion = Client(auth=NOTION_TOKEN)
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        
        # 1. KOR Page
        page_kor = notion.pages.create(
            parent={"page_id": NOTION_PAGE_ID},
            properties={"title": [{"text": {"content": f"Top Marketing Journals Weekly Report ({today_str})"}}]}
        )
        
        # 2. ENG Page
        page_eng = notion.pages.create(
            parent={"page_id": NOTION_PAGE_ID},
            properties={"title": [{"text": {"content": f"[ENG] Top Marketing Journals Weekly Report ({today_str})"}}]}
        )
        
        blocks_kor = []
        blocks_eng = []
        
        for paper, analysis in zip(papers, analyzed_results):
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
            notion.blocks.children.append(block_id=page_kor["id"], children=blocks_kor[i:i+100])
            
        for i in range(0, len(blocks_eng), 100):
            notion.blocks.children.append(block_id=page_eng["id"], children=blocks_eng[i:i+100])
                
        print(f"✅ 노션 업로드 성공!")
    except Exception as e:
        print(f"노션 업로드 실패 (에러: {e})")

def weekly_job():
    papers = fetch_recent_papers()
    if not papers: return
        
    analyzed_results = []
    for i, paper in enumerate(papers):
        analysis = analyze_paper_with_gemini(paper)
        analyzed_results.append(analysis)
        time.sleep(35) 
        
    # CSV/MD 파일 생성 생략
    save_to_notion(papers, analyzed_results)

if __name__ == "__main__":
    weekly_job()
