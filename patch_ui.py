import glob
import re

new_func = """
import re

def clean_markdown(text):
    if not text: return ""
    text = re.sub(r'\\*\\*(.*?)\\*\\*', r'\\1', text)
    text = re.sub(r'\\*(.*?)\\*', r'\\1', text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = text.replace('###', '')
    text = text.replace('##', '')
    # Convert bullet points to standard bullets
    text = re.sub(r'^-\\s+', '• ', text, flags=re.MULTILINE)
    return text.strip()

def append_paper_blocks(blocks, paper, analysis_text):
    blocks.append({
        "object": "block", "type": "divider", "divider": {}
    })
    blocks.append({
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": paper.get('Title', 'No Title')}}]}
    })
    
    meta_text = f"저널명: {paper.get('Journal', 'Unknown')}\\n저자: {paper.get('Authors', '')}\\n출판일: {paper.get('Date', '')}\\n링크: {paper.get('URL', '')}"
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
"""

for script in glob.glob("*_research_assistant.py") + ["backfill_2025_to_now.py"]:
    with open(script, 'r', encoding='utf-8') as f:
        content = f.read()

    if "clean_markdown" not in content:
        if "def upload_month_to_notion" in content:
            content = content.replace("def upload_month_to_notion", new_func + "\ndef upload_month_to_notion")
        elif "def save_to_notion" in content:
            content = content.replace("def save_to_notion", new_func + "\ndef save_to_notion")

    # Replace the loop entirely using Regex dotall
    if "papers_in_month" in content:
        loop_pattern = r'for paper in papers_in_month:.*?divider": \{\}\}\}\n'
        new_loop = """for paper in papers_in_month:
        analysis_text = clean_markdown(paper.get('AI_Analysis', ''))
        append_paper_blocks(blocks, paper, analysis_text)
        
        paragraphs = analysis_text.split('\\n\\n')
        for p in paragraphs:
            if not p.strip(): continue
            chunks = [p[i:i+1900] for i in range(0, len(p), 1900)]
            for idx, chunk in enumerate(chunks):
                if re.match(r'^[A-C]\\.', chunk.strip()):
                    blocks.append({
                        "object": "block", "type": "heading_3",
                        "heading_3": {"rich_text": [{"type": "text", "text": {"content": chunk.strip()}}]}
                    })
                else:
                    blocks.append({
                        "object": "block", "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk.strip()}}]}
                    })
"""
        content = re.sub(loop_pattern, new_loop, content, flags=re.DOTALL)
    else:
        loop_pattern = r'for paper, analysis in zip\(papers, analyzed_results\):.*?divider": \{\}\}\}\n'
        new_loop = """for paper, analysis in zip(papers, analyzed_results):
        analysis_text = clean_markdown(analysis)
        append_paper_blocks(blocks, paper, analysis_text)
        
        paragraphs = analysis_text.split('\\n\\n')
        for p in paragraphs:
            if not p.strip(): continue
            chunks = [p[i:i+1900] for i in range(0, len(p), 1900)]
            for idx, chunk in enumerate(chunks):
                if re.match(r'^[A-C]\\.', chunk.strip()):
                    blocks.append({
                        "object": "block", "type": "heading_3",
                        "heading_3": {"rich_text": [{"type": "text", "text": {"content": chunk.strip()}}]}
                    })
                else:
                    blocks.append({
                        "object": "block", "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk.strip()}}]}
                    })
"""
        content = re.sub(loop_pattern, new_loop, content, flags=re.DOTALL)

    with open(script, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Patched {script}")
