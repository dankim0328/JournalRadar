import os

template = """import requests
import pandas as pd
import schedule
import time
import datetime
import os
import sys
import re
sys.stdout.reconfigure(encoding='utf-8')

from notion_client import Client
from gemini_safe_client import GeminiSafeClient, truncate_text, enrich_abstract, ANTI_HALLUCINATION_INSTRUCTION

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_PAGE_ID = os.environ.get("{PAGE_VAR}", "")

# 안전장치가 적용된 Gemini 클라이언트 초기화
gemini_client = GeminiSafeClient()

TARGET_JOURNAL_NAMES = {TARGET_JOURNAL_NAMES}

JOURNAL_ISSNS = {JOURNAL_ISSNS}

def fetch_recent_papers():
    print(f"[{{datetime.datetime.now()}}] Crossref에서 최근 논문을 수집합니다...")
    today = datetime.date.today()
    last_week = today - datetime.timedelta(days=7)
    from_date = last_week.strftime("%Y-%m-%d")
    papers = []
    headers = {{"User-Agent": "AcademicResearchBot/1.0 (mailto:your_email@example.com)"}}
    
    for issn in JOURNAL_ISSNS:
        url = f"https://api.crossref.org/works?filter=issn:{{issn}},from-pub-date:{{from_date}}"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200: continue
            data = response.json()
            items = data.get("message", {{}}).get("items", [])
            for item in items:
                title = item.get("title", [""])[0] if item.get("title") else "No title"
                authors = [f"{{a.get('given', '')}} {{a.get('family', '')}}".strip() for a in item.get("author", [])]
                author_str = ", ".join(authors) if authors else "Unknown"
                pub_date_parts = item.get("published-online", item.get("published-print", item.get("published", {{}}))).get("date-parts", [[None]])[0]
                pub_date = "-".join(map(str, pub_date_parts)) if pub_date_parts and pub_date_parts[0] else "Unknown"
                url_link = item.get("URL", "")
                doi = item.get("DOI", "")
                abstract = item.get("abstract", "초록(Abstract) 정보가 제공되지 않았습니다.")
                abstract = re.sub(r'<[^>]+>', '', abstract)
                abstract = enrich_abstract(abstract, doi)
                journal_name = item.get("container-title", ["Unknown Journal"])[0] if item.get("container-title") else "Unknown Journal"
                
                is_target = False
                for tj in TARGET_JOURNAL_NAMES:
                    if tj.lower() in journal_name.lower():
                        is_target = True
                        break
                if not is_target: continue
                
                papers.append({{
                    "Journal": journal_name,
                    "Title": title,
                    "Authors": author_str,
                    "Date": pub_date,
                    "URL": url_link,
                    "Abstract": abstract
                }})
        except Exception: pass
            
    unique_papers = []
    seen_titles = set()
    for p in papers:
        if p["Title"] not in seen_titles and p["Title"] != "No title":
            unique_papers.append(p)
            seen_titles.add(p["Title"])
            
    return unique_papers

def analyze_paper_with_gemini(paper):
    # 매 호출마다 프롬프트를 새로 생성 (컨텍스트 누적 방지)
    safe_abstract = truncate_text(paper.get('Abstract', ''))
    
    prompt = f\\\"\\\"\\\"당신은 세계적인 {FIELD_NAME} 학술 연구 보조 AI입니다.
아래 {FIELD_NAME} 탑 저널 논문 정보를 바탕으로 다음 3가지를 한국어로 심층 분석해 주세요.

[논문 정보]
- 저널명: {{paper.get('Journal', 'Unknown Journal')}}
- 논문 제목: {{paper['Title']}}
- 저자: {{paper['Authors']}}
- 초록(Abstract): {{safe_abstract}}

[요구사항]
A. 논문 요약: 이 논문의 핵심 내용을 요약해 주세요.
B. 연구적 의의: 기존 연구나 논리의 반박인지, 새로운 패러다임 제시인지 등 현 시대적 상황(비즈니스 트렌드 등)과 연관 지어 분석해 주세요.
C. 저자 백그라운드: 저자들의 주요 연구 분야, 학력, 지도교수 등 배경 정보에 대해 당신이 아는 선에서 설명해 주세요. (특정 저자에 대한 정보가 부족하다면, 이름에서 유추되는 일반적인 성향이나 학계 내 추정 정보를 유연하게 작성해 주세요).

{{ANTI_HALLUCINATION_INSTRUCTION}}

[출력 형식]
A. 논문 요약:
[내용]

B. 연구적 의의:
[내용]

C. 저자 백그라운드:
[내용]
\\\"\\\"\\\"
    return gemini_client.analyze(prompt, cache_key_title=paper['Title'])

def save_to_files(papers, analyzed_results):
    today_str = datetime.date.today().strftime("%Y%m%d")
    csv_filename = f"{PREFIX}_papers_{{today_str}}.csv"
    md_filename = f"{PREFIX}_papers_{{today_str}}.md"
    
    merged_data = []
    for paper, analysis in zip(papers, analyzed_results):
        paper_copy = paper.copy()
        paper_copy["AI_Analysis"] = analysis
        merged_data.append(paper_copy)
        
    df = pd.DataFrame(merged_data)
    df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
    
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(f"# Top {CAP_FIELD} Journals Weekly Report ({{datetime.date.today().strftime('%Y-%m-%d')}})\\\\n\\\\n---\\\\n\\\\n")
        for paper, analysis in zip(papers, analyzed_results):
            f.write(f"## {{paper['Title']}}\\\\n\\\\n")
            f.write(f"- **저널명**: {{paper.get('Journal', 'Unknown Journal')}}\\\\n")
            f.write(f"- **저자**: {{paper['Authors']}}\\\\n")
            f.write(f"- **출판일**: {{paper['Date']}}\\\\n")
            f.write(f"- **링크**: {{paper['URL']}}\\\\n\\\\n")
            f.write(f"### 논문 초록 (Abstract)\\\\n{{paper['Abstract']}}\\\\n\\\\n")
            f.write(f"### AI 심층 분석 요약\\\\n{{analysis}}\\\\n\\\\n---\\\\n\\\\n")

def clean_markdown(text):
    if not text: return ""
    text = re.sub(r'\\\\*\\\\*(.*?)\\\\*\\\\*', r'\\\\1', text)
    text = re.sub(r'\\\\*(.*?)\\\\*', r'\\\\1', text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = text.replace('###', '')
    text = text.replace('##', '')
    # Convert bullet points to standard bullets
    text = re.sub(r'^-\\\\s+', '• ', text, flags=re.MULTILINE)
    return text.strip()

def append_paper_blocks(blocks, paper, analysis_text):
    blocks.append({{"object": "block", "type": "divider", "divider": {{}}}})
    blocks.append({{"object": "block", "type": "heading_2", "heading_2": {{"rich_text": [{{"type": "text", "text": {{"content": paper.get('Title', 'No Title')}}}}]}}}})
    
    meta_text = f"저널명: {{paper.get('Journal', 'Unknown')}}\\\\n저자: {{paper.get('Authors', '')}}\\\\n출판일: {{paper.get('Date', '')}}\\\\n링크: {{paper.get('URL', '')}}"
    blocks.append({{"object": "block", "type": "callout", "callout": {{"rich_text": [{{"type": "text", "text": {{"content": meta_text}}}}], "icon": {{"type": "emoji", "emoji": "🔗"}}, "color": "blue_background"}}}})
    
    blocks.append({{"object": "block", "type": "heading_3", "heading_3": {{"rich_text": [{{"type": "text", "text": {{"content": "논문 초록 (Abstract)"}}}}]}}}})
    abs_text = str(paper.get('Abstract', ''))[:1990] + ("..." if len(str(paper.get('Abstract', ''))) > 1990 else "")
    blocks.append({{"object": "block", "type": "quote", "quote": {{"rich_text": [{{"type": "text", "text": {{"content": abs_text}}}}]}}}})

def save_to_notion(papers, analyzed_results):
    if NOTION_TOKEN == "여기에_노션_통합토큰_입력" or NOTION_PAGE_ID == "":
        print("💡 [안내] Notion 연동 토큰이 입력되지 않아 노션 업로드는 생략되었습니다.")
        return

    print("🚀 Notion 페이지를 생성하여 결과를 업로드합니다...")
    try:
        notion = Client(auth=NOTION_TOKEN)
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        title = f"Top {CAP_FIELD} Journals Weekly Report ({{today_str}})"
        
        new_page = notion.pages.create(
            parent={{"page_id": NOTION_PAGE_ID}},
            properties={{"title": [{{"text": {{"content": title}}}}]}}
        )
        page_id = new_page["id"]
        
        blocks = []
        for paper, analysis in zip(papers, analyzed_results):
            analysis_text = clean_markdown(analysis)
            append_paper_blocks(blocks, paper, analysis_text)
            
            blocks.append({{"object": "block", "type": "heading_3", "heading_3": {{"rich_text": [{{"type": "text", "text": {{"content": "AI 심층 분석 요약"}}}}]}}}})
            
            paragraphs = analysis_text.split('\\\\n\\\\n')
            for p in paragraphs:
                if not p.strip(): continue
                chunks = [p[i:i+1900] for i in range(0, len(p), 1900)]
                for idx, chunk in enumerate(chunks):
                    if chunk.strip().startswith("A.") or chunk.strip().startswith("B.") or chunk.strip().startswith("C."):
                        blocks.append({{"object": "block", "type": "heading_3", "heading_3": {{"rich_text": [{{"type": "text", "text": {{"content": chunk.strip()}}}}]}}}})
                    else:
                        blocks.append({{"object": "block", "type": "paragraph", "paragraph": {{"rich_text": [{{"type": "text", "text": {{"content": chunk.strip()}}}}]}}}})
        
        blocks.append({{"object": "block", "type": "divider", "divider": {{}}}})
        
        for i in range(0, len(blocks), 100):
            batch = blocks[i:i+100]
            notion.blocks.children.append(block_id=page_id, children=batch)
                
        print(f"✅ 노션 업로드 성공! 페이지 링크: {{new_page.get('url')}}")
    except Exception as e:
        print(f"노션 업로드 실패 (에러: {{e}})")

def weekly_job():
    papers = fetch_recent_papers()
    if not papers: return
        
    analyzed_results = []
    for i, paper in enumerate(papers):
        print(f"📝 [{{i+1}}/{{len(papers)}}] 분석 중: {{paper['Title'][:60]}}...")
        analysis = analyze_paper_with_gemini(paper)
        analyzed_results.append(analysis)
        # Free Tier 2 RPM 제한 준수
        time.sleep(35) 
        
    save_to_files(papers, analyzed_results)
    save_to_notion(papers, analyzed_results)

if __name__ == "__main__":
    weekly_job()
"""

# 1. Marketing
m_code = template.format(
    PAGE_VAR="NOTION_PARENT_PAGE_ID",
    TARGET_JOURNAL_NAMES='["Journal of Marketing", "Journal of Marketing Research", "Journal of Consumer Research", "Marketing Science", "Quantitative Marketing and Economics"]',
    JOURNAL_ISSNS='["0022-2429", "1547-7185", "0022-2437", "1547-7193", "0093-5301", "1537-5277", "0732-2399", "1526-548X", "1570-7156", "1573-7155"]',
    FIELD_NAME="마케팅",
    PREFIX="marketing",
    CAP_FIELD="Marketing"
)
with open("marketing_research_assistant.py", "w", encoding="utf-8") as f: f.write(m_code)

# 2. Finance
f_code = template.format(
    PAGE_VAR="NOTION_FINANCE_PAGE_ID",
    TARGET_JOURNAL_NAMES='["The Journal of Finance", "Journal of Financial Economics", "The Review of Financial Studies", "Journal of Financial and Quantitative Analysis", "Review of Finance"]',
    JOURNAL_ISSNS='["0022-1082", "1540-6261", "0304-405X", "0893-9454", "1465-7368", "0022-1090", "1756-6916", "1572-3097", "1573-692X"]',
    FIELD_NAME="재무(Finance)",
    PREFIX="finance",
    CAP_FIELD="Finance"
)
with open("finance_research_assistant.py", "w", encoding="utf-8") as f: f.write(f_code)

# 3. Accounting
a_code = template.format(
    PAGE_VAR="NOTION_ACCOUNTING_PAGE_ID",
    TARGET_JOURNAL_NAMES='["The Accounting Review", "Journal of Accounting Research", "Journal of Accounting and Economics", "Contemporary Accounting Research", "Review of Accounting Studies"]',
    JOURNAL_ISSNS='["0001-4826", "1558-7967", "0021-8456", "1475-679X", "0165-4101", "0823-9150", "1911-3846", "1380-6653", "1573-7136"]',
    FIELD_NAME="회계(Accounting)",
    PREFIX="accounting",
    CAP_FIELD="Accounting"
)
with open("accounting_research_assistant.py", "w", encoding="utf-8") as f: f.write(a_code)
