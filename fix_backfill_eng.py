import glob
import re

with open('backfill_2025_to_now.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. replace analyze_paper_with_gemini
old_analyze_pattern = r'def analyze_paper_with_gemini\(paper\):.*?return "AI 백필 분석 실패."\n'
new_analyze = """def analyze_paper_with_gemini(paper):
    prompt = f\"\"\"당신은 세계적인 마케팅 학술 연구 보조 AI입니다.
아래 마케팅 탑 저널 논문 정보를 바탕으로 다음 3가지를 분석해 주세요.

[논문 정보]
- 저널명: {paper.get('Journal')}
- 논문 제목: {paper.get('Title')}
- 저자: {paper.get('Authors')}
- 초록(Abstract): {paper.get('Abstract')}

[요구사항]
A. 논문 요약 (Summary): 이 논문의 핵심 내용을 요약해 주세요.
B. 연구적 의의 (Academic Significance): 기존 연구나 논리의 반박인지, 새로운 패러다임 제시인지 등 현 시대적 상황과 연관 지어 분석해 주세요.
C. 저자 백그라운드 (Author Background): 저자들의 주요 연구 분야, 학력 등 배경 정보에 대해 당신이 아는 선에서 설명해 주세요.

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
\"\"\"
    try:
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text if response.text else "===KOREAN===\nAI 분석 실패.\n===ENGLISH===\nAI Analysis Failed."
    except Exception as e:
        return "===KOREAN===\nAI 분석 실패.\n===ENGLISH===\nAI Analysis Failed."
"""
content = re.sub(old_analyze_pattern, new_analyze, content, flags=re.DOTALL)

# 2. replace upload_month_to_notion
old_upload_pattern = r'def upload_month_to_notion\(month_label, papers_in_month\):.*?print\(f"✅ \{month_label\} 업로드 완료.*?\n'
new_upload = """def upload_month_to_notion(month_label, papers_in_month):
    print(f"\\n🚀 Notion 업로드 시작: {month_label} (총 {len(papers_in_month)}편)")
    notion = Client(auth=NOTION_TOKEN)
    title = f"Top Marketing Journals ({month_label} 모집)"

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
    
    blocks_kor.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"총 {len(papers_in_month)}건의 과거 논문 일괄 백필(Backfill) 데이터입니다."}}]}})
    blocks_eng.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"A total of {len(papers_in_month)} backfilled legacy papers."}}]}})
    
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
"""
content = re.sub(old_upload_pattern, new_upload, content, flags=re.DOTALL)

# 3. fix new_func replacing append_paper_blocks to support header_title logic!
old_append = r'def append_paper_blocks\(blocks, paper, analysis_text\):.*?blocks\.append\(\{"object": "block", "type": "divider", "divider": \{\}\}\)'
new_append = """def append_paper_blocks(blocks, paper, analysis_text, header_title):
    blocks.append({"object": "block", "type": "divider", "divider": {}})
    blocks.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": paper.get('Title', 'No Title')}}]}})
    
    meta_text = f"저널명: {paper.get('Journal', 'Unknown')}\\n저자: {paper.get('Authors', '')}\\n출판일: {paper.get('Date', '')}\\n링크: {paper.get('URL', '')}"
    blocks.append({"object": "block", "type": "callout", "callout": {"rich_text": [{"type": "text", "text": {"content": meta_text}}], "icon": {"type": "emoji", "emoji": "🔗"}, "color": "blue_background"}})
    
    blocks.append({"object": "block", "type": "heading_3", "heading_3": {"rich_text": [{"type": "text", "text": {"content": "초록 (Abstract)" if "한국어" in header_title or "심층" in header_title else "Abstract"}}]}})
    abs_text = str(paper.get('Abstract', ''))[:1990] + ("..." if len(str(paper.get('Abstract', ''))) > 1990 else "")
    blocks.append({"object": "block", "type": "quote", "quote": {"rich_text": [{"type": "text", "text": {"content": abs_text}}]}})
    
    blocks.append({"object": "block", "type": "heading_3", "heading_3": {"rich_text": [{"type": "text", "text": {"content": header_title}}]}})
    
    paragraphs = analysis_text.split('\\n\\n')
    for p in paragraphs:
        if not p.strip(): continue
        chunks = [p[i:i+1900] for i in range(0, len(p), 1900)]
        for chunk in chunks:
            if chunk.strip().startswith("A.") or chunk.strip().startswith("B.") or chunk.strip().startswith("C."):
                blocks.append({"object": "block", "type": "heading_3", "heading_3": {"rich_text": [{"type": "text", "text": {"content": chunk.strip()}}]}})
            else:
                blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk.strip()}}]}})
"""

content = re.sub(old_append, new_append, content, flags=re.DOTALL)

with open('backfill_2025_to_now.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("backfill updated!")
