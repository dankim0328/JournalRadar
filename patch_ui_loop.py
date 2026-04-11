import glob

new_backfill_loop = """for paper in papers_in_month:
        analysis_text = clean_markdown(paper.get('AI_Analysis', ''))
        append_paper_blocks(blocks, paper, analysis_text)
        
        paragraphs = analysis_text.split('\\n\\n')
        for p in paragraphs:
            if not p.strip(): continue
            chunks = [p[i:i+1900] for i in range(0, len(p), 1900)]
            for idx, chunk in enumerate(chunks):
                if chunk.strip().startswith("A.") or chunk.strip().startswith("B.") or chunk.strip().startswith("C."):
                    blocks.append({
                        "object": "block", "type": "heading_3",
                        "heading_3": {"rich_text": [{"type": "text", "text": {"content": chunk.strip()}}]}
                    })
                else:
                    blocks.append({
                        "object": "block", "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk.strip()}}]}
                    })
        
        blocks.append({"object": "block", "type": "divider", "divider": {}})"""

new_weekly_loop = """for paper, analysis in zip(papers, analyzed_results):
            analysis_text = clean_markdown(analysis)
            append_paper_blocks(blocks, paper, analysis_text)
            
            paragraphs = analysis_text.split('\\n\\n')
            for p in paragraphs:
                if not p.strip(): continue
                chunks = [p[i:i+1900] for i in range(0, len(p), 1900)]
                for idx, chunk in enumerate(chunks):
                    if chunk.strip().startswith("A.") or chunk.strip().startswith("B.") or chunk.strip().startswith("C."):
                        blocks.append({
                            "object": "block", "type": "heading_3",
                            "heading_3": {"rich_text": [{"type": "text", "text": {"content": chunk.strip()}}]}
                        })
                    else:
                        blocks.append({
                            "object": "block", "type": "paragraph",
                            "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk.strip()}}]}
                        })
            blocks.append({"object": "block", "type": "divider", "divider": {}})"""


def replace_loop(filepath, is_backfill):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find where the old loop starts
    start_str = "for paper in papers_in_month:" if is_backfill else "for paper, analysis in zip(papers, analyzed_results):"
    
    start_idx = content.find(start_str)
    if start_idx == -1:
        print(f"Loop start not found in {filepath}")
        return
        
    div_str = 'blocks.append({"object": "block", "type": "divider", "divider": {}})'
    end_idx = content.find(div_str, start_idx) + len(div_str)
    
    if end_idx < len(div_str):
        print(f"Loop end not found in {filepath}")
        return
        
    old_loop = content[start_idx:end_idx]
    
    if is_backfill:
        # Check indentation level (backfill loop is usually indented 4 spaces)
        prefix = "    "
        replacement = "\\n".join([prefix + line if line.strip() else line for line in new_backfill_loop.split("\\n")])
        replacement = replacement.replace("    for paper in", "for paper in") # first line is already prefixed logically when slicing
    else:
        # Weekly loop is usually indented 8 spaces
        prefix = "        "
        replacement = "\\n".join([prefix + line if line.strip() else line for line in new_weekly_loop.split("\\n")])
        replacement = replacement.replace("        for paper,", "for paper,")
        
    # simple replace (using literal strings, avoiding regex completely)
    content = content[:start_idx] + (new_backfill_loop if is_backfill else new_weekly_loop) + content[end_idx:]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Success replacing {filepath}")

for script in glob.glob("*_research_assistant.py"):
    replace_loop(script, False)

replace_loop("backfill_2025_to_now.py", True)
