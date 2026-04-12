import re

def clean_text(text):
    if not text:
        return ""
    text = text.replace("**", "")
    text = re.sub(r"^(알겠습니다|물론입니다|네|반갑습니다|안녕하세요)[^.]*AI로서,[^.]*(제공해 드립니다|분석해 드리겠습니다|분석해 보겠습니다|분석해 드립니다)\.?\n*", "", text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

content = open('marketing_papers_20260411.md', 'r', encoding='utf-8').read()
sections = re.split(r'##\s+', content)[1:]
print(f"Total sections: {len(sections)}")

for i, section in enumerate(sections):
    lines = section.strip().split('\n')
    title = lines[0].strip()
    print(f"Paper {i+1}: {title[:50]}")
    
    # Try multiple variations
    analysis_match = re.search(r'###\s+AI\s+심층\s+분석\s+요약\s*\n*([\s\S]+)', section)
    if not analysis_match:
        # Try without \s+
        analysis_match = re.search(r'### AI 심층 분석 요약\n*([\s\S]+)', section)
        
    if analysis_match:
        analysis = analysis_match.group(1).strip()
        print(f"  Analysis length: {len(analysis)}")
        cleaned = clean_text(analysis)
        print(f"  Cleaned length: {len(cleaned)}")
    else:
        print("  WARNING: Analysis header NOT FOUND!")
        # Print a bit of the section to see what's there
        print(f"  Section snippet: {section[:200]}")
