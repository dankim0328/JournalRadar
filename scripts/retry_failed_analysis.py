import os
import json
import time
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')
import google.generativeai as genai
from google.api_core import exceptions

# --- Configuration ---
# Set your API key here or via environment variable
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)

# Use a stable model
MODEL_NAME = "gemini-2.5-pro"
model = genai.GenerativeModel(model_name=MODEL_NAME)

DATA_ROOT = "site/public/data"
FAILURE_MARKERS = ["AI 분석 실패", "AI Analysis Failed"]
DELAY_SECONDS = 36  # Respect rate limits (slightly over 35s for safety)

# --- Prompts ---
PROMPT_TEMPLATES = {
    "marketing": "마케팅",
    "finance": "재무(Finance)",
    "accounting": "회계(Accounting)"
}

def get_analysis_prompt(field_name, paper):
    return f"""당신은 세계적인 {field_name} 학술 연구 보조 AI입니다.
아래 {field_name} 탑 저널 논문 정보를 바탕으로 다음 3가지를 분석해 주세요.

[논문 정보]
- 저널명: {paper.get('journal', 'Unknown')}
- 논문 제목: {paper.get('title', 'No Title')}
- 저자: {paper.get('authors', 'Unknown')}
- 초록(Abstract): {paper.get('abstract', '초록 정보가 없습니다.')}

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

def analyze_paper(field_name, paper):
    prompt = get_analysis_prompt(field_name, paper)
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
        print(f"   [Error] API Failure: {e}")
        return None

def process_file(file_path, field_name, dry_run=False):
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error reading {file_path}")
            return 0

    papers = data.get("papers", [])
    updated_count = 0
    
    for i, paper in enumerate(papers):
        analysis_ko = paper.get("analysis_ko", "")
        analysis_en = paper.get("analysis_en", "")
        
        is_failure = any(marker in (analysis_ko or "") for marker in FAILURE_MARKERS) or not analysis_ko
        
        if is_failure:
            print(f"Found failed analysis in {file_path}: {paper.get('title')[:50]}...")
            if dry_run:
                updated_count += 1
                continue
                
            print(f"   [Retrying] analysis for {field_name}...")
            new_analysis = analyze_paper(field_name, paper)
            
            if new_analysis:
                # Split analysis into KO and EN if needed
                parts = new_analysis.split('===ENGLISH===')
                ko_part = parts[0].replace('===KOREAN===', '').strip()
                en_part = parts[1].strip() if len(parts) > 1 else ""
                
                data["papers"][i]["analysis_ko"] = ko_part
                data["papers"][i]["analysis_en"] = en_part
                updated_count += 1
                
                # Save immediately after each success to prevent data loss
                with open(file_path, 'w', encoding='utf-8') as wf:
                    json.dump(data, wf, ensure_ascii=False, indent=2)
                
                print(f"   [Fixed] Waiting {DELAY_SECONDS}s for next...")
                time.sleep(DELAY_SECONDS)
            else:
                print(f"   [Skipped] skipping due to API failure.")

    return updated_count

def main(dry_run=False):
    total_fixed = 0
    total_to_fix = 0
    
    for cat in ["marketing", "finance", "accounting"]:
        cat_path = os.path.join(DATA_ROOT, cat)
        if not os.path.exists(cat_path): continue
        
        field_name = PROMPT_TEMPLATES.get(cat, cat)
        
        for root, dirs, files in os.walk(cat_path):
            for file in files:
                if file.startswith("W") and file.endswith(".json") and file != "index.json":
                    file_path = os.path.join(root, file)
                    count = process_file(file_path, field_name, dry_run=dry_run)
                    if dry_run:
                        total_to_fix += count
                    else:
                        total_fixed += count

    if dry_run:
        print(f"\n[Dry Run Summary] Found {total_to_fix} papers needing AI analysis restoration.")
    else:
        print(f"\n[Run Summary] Successfully restored {total_fixed} papers.")

if __name__ == "__main__":
    import sys
    is_dry = "--dry-run" in sys.argv
    main(dry_run=is_dry)
