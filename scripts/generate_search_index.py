import os
import json
import sys

# Ensure UTF-8 output for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DATA_ROOT = "site/public/data"

def generate_search_indexes():
    current_dir = os.getcwd()
    abs_data_root = os.path.abspath(DATA_ROOT)
    print(f"Current Working Directory: {current_dir}")
    print(f"Resolved DATA_ROOT: {abs_data_root}")
    
    if not os.path.exists(abs_data_root):
        print(f"CRITICAL ERROR: {abs_data_root} does not exist!")
        sys.exit(1)

    categories = [d.lower() for d in os.listdir(abs_data_root) if os.path.isdir(os.path.join(abs_data_root, d))]
    # Remove duplicates if any
    categories = sorted(list(set(categories)))
    
    if not categories:
        print(f"WARNING: No category directories found in {abs_data_root}")
        return

    for cat in categories:
        print(f"Indexing category: {cat}")
        cat_path = os.path.join(abs_data_root, cat)
        all_papers = []
        
        years = [d for d in os.listdir(cat_path) if os.path.isdir(os.path.join(cat_path, d)) and d.isdigit()]
        
        for year in years:
            year_path = os.path.join(cat_path, year)
            # Match W01.json, W02.json, etc.
            week_files = [f for f in os.listdir(year_path) if f.startswith("W") and f.endswith(".json") and f != "index.json"]
            print(f"  Found {len(week_files)} week files in {year}")
            
            for wf in week_files:
                week_num = wf.replace("W", "").replace(".json", "")
                full_wf_path = os.path.join(year_path, wf)
                with open(full_wf_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        papers = data.get('papers', [])
                        for paper in papers:
                            indexed_paper = {
                                "title": paper.get("title"),
                                "authors": paper.get("authors"),
                                "journal": paper.get("journal"),
                                "date": paper.get("date"),
                                "slug": paper.get("slug"),
                                "year": year,
                                "week": week_num,
                                "week_label": data.get("label_ko")
                            }
                            all_papers.append(indexed_paper)
                    except Exception as e:
                        print(f"  Error reading {wf}: {e}")
        
        if not all_papers:
            print(f"  WARNING: No papers found for category {cat}")
            continue

        # Save search index
        index_file = os.path.join(cat_path, "search_index.json")
        with open(index_file, 'w', encoding='utf-8') as f:
            all_papers.sort(key=lambda x: (x['year'], x['week']), reverse=True)
            json.dump(all_papers, f, ensure_ascii=False, separators=(',', ':'))
        
        print(f"  Success: Created search index for {cat} with {len(all_papers)} papers.")

if __name__ == "__main__":
    # Change to root dir if needed
    if os.path.basename(os.getcwd()) == 'scripts':
        os.chdir('..')
    generate_search_indexes()
