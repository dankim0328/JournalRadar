import re
import json
import os

def clean_text(text):
    if not text: return ""
    text = text.replace("**", "")
    text = re.sub(r"^(알겠습니다|물론입니다|네|반갑습니다|안녕하세요)[^.]*AI로서,[^.]*(제공해 드립니다|분석해 드리겠습니다|분석해 보겠습니다|분석해 드립니다)\.?\n*", "", text, flags=re.MULTILINE).strip()
    return text

def parse_markdown_papers(content, category):
    sections = re.split(r'\n##\s+', '\n' + content.strip())[1:]
    papers = []
    for section in sections:
        lines = section.strip().split('\n')
        title = lines[0].strip()
        url_match = re.search(r'링크:\s*(https?://\S+)', section)
        url = url_match.group(1).replace("- **", "").replace("**", "").strip() if url_match else ""
        analysis_match = re.search(r'###\s*AI\s*심층\s*분석\s*요약\s*(?:.*)\n+([\s\S]+)', section)
        analysis = clean_text(analysis_match.group(1).strip()) if analysis_match else ""
        papers.append({"Title": title, "URL": url, "AI_Analysis": analysis, "Category": category})
    return papers

# 1. Load initial state
all_papers = [
    {"Title": "EXPRESS: Does Puffery Sell? Evidence from Airbnb", 
     "URL": "https://doi.org/10.1177/00222437261444259", 
     "AI_Analysis": "===KOREAN===\nAI 분석 실패.\n===ENGLISH===\nAI Analysis Failed."}
]
existing_map = {p["URL"]: p for p in all_papers}

# 2. Run parser on content
content = open('marketing_papers_20260411.md', 'r', encoding='utf-8').read()
new_papers = parse_markdown_papers(content, "Marketing")

print(f"Total new papers from MD: {len(new_papers)}")

# 3. Simulate Merge
for np in new_papers:
    url = np["URL"]
    if url in existing_map:
        curr = existing_map[url]["AI_Analysis"]
        if "분석 실패" in curr or not curr.strip():
            print(f"UPDATING {np['Title'][:30]}...")
            existing_map[url].update(np)

print(f"Final analysis for Puffery Sell: {all_papers[0]['AI_Analysis'][:50]}")
