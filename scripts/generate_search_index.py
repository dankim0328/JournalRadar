import os
import json
import sys

# Ensure UTF-8 output for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DATA_ROOT = "site/public/data"

def generate_search_indexes():
    categories = [d for d in os.listdir(DATA_ROOT) if os.path.isdir(os.path.join(DATA_ROOT, d))]
    
    for cat in categories:
        print(f"Indexing category: {cat}")
        cat_path = os.path.join(DATA_ROOT, cat)
        all_papers = []
        
        years = [d for d in os.listdir(cat_path) if os.path.isdir(os.path.join(cat_path, d)) and d.isdigit()]
        
        for year in years:
            year_path = os.path.join(cat_path, year)
            # Match W01.json, W02.json, etc.
            week_files = [f for f in os.listdir(year_path) if f.startswith("W") and f.endswith(".json") and f != "index.json"]
            
            for wf in week_files:
                week_num = wf.replace("W", "").replace(".json", "")
                with open(os.path.join(year_path, wf), 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        papers = data.get('papers', [])
                        for paper in papers:
                            # Extract essential info for search
                            indexed_paper = {
                                "title": paper.get("title"),
                                "authors": paper.get("authors"),
                                "journal": paper.get("journal"),
                                "date": paper.get("date"),
                                "slug": paper.get("slug"),
                                "year": year,
                                "week": week_num,
                                "week_label": data.get("label_ko") # To show context in search results
                            }
                            all_papers.append(indexed_paper)
                    except Exception as e:
                        print(f"Error reading {wf}: {e}")
        
        # Save search index
        index_file = os.path.join(cat_path, "search_index.json")
        with open(index_file, 'w', encoding='utf-8') as f:
            # Sort papers by date (newest first)
            all_papers.sort(key=lambda x: (x['year'], int(x['week'])), reverse=True)
            json.dump(all_papers, f, ensure_ascii=False, separators=(',', ':'))
        
        print(f"Created search index for {cat} with {len(all_papers)} papers.")

if __name__ == "__main__":
    # Change to root dir if needed
    if os.path.basename(os.getcwd()) == 'scripts':
        os.chdir('..')
    generate_search_indexes()
