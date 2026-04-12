import os
import json
import datetime

SITE_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "site", "public", "data")

MONTH_NAMES_EN = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

def get_new_labels(start_date_str):
    try:
        dt_m = datetime.date(*[int(x) for x in start_date_str.split("-")])
        dt_t = dt_m + datetime.timedelta(days=3)
        
        week_of_month = (dt_t.day - 1) // 7 + 1
        
        month_en = MONTH_NAMES_EN[dt_t.month - 1]
        
        label_ko = f"{dt_t.month}월 {week_of_month}주차"
        label_en = f"{month_en} Week {week_of_month}"
        return label_ko, label_en
    except Exception as e:
        print(f"Error calculating label for {start_date_str}: {e}")
        return None, None

def patch_data():
    print(f"Patching data in {SITE_DATA_DIR}...")
    
    for category in os.listdir(SITE_DATA_DIR):
        cat_path = os.path.join(SITE_DATA_DIR, category)
        if not os.path.isdir(cat_path):
            continue
            
        for year in os.listdir(cat_path):
            year_path = os.path.join(cat_path, year)
            if not os.path.isdir(year_path) or not year.isdigit():
                continue
                
            print(f"  Processing {category}/{year}...")
            
            # 1. Patch Wxx.json files
            for fname in os.listdir(year_path):
                if fname.startswith("W") and fname.endswith(".json") and fname != "index.json":
                    fpath = os.path.join(year_path, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        wdata = json.load(f)
                    
                    old_ko = wdata.get("label_ko")
                    new_ko, new_en = get_new_labels(wdata["startDate"])
                    
                    if new_ko and (old_ko != new_ko or wdata.get("label_en") != new_en):
                        print(f"    Updating {fname}: {old_ko} -> {new_ko}")
                        wdata["label_ko"] = new_ko
                        wdata["label_en"] = new_en
                        with open(fpath, "w", encoding="utf-8") as f:
                            json.dump(wdata, f, ensure_ascii=False, indent=2)
            
            # 2. Patch year index.json
            year_index_path = os.path.join(year_path, "index.json")
            if os.path.exists(year_index_path):
                with open(year_index_path, "r", encoding="utf-8") as f:
                    yindex = json.load(f)
                
                changed = False
                for w in yindex.get("weeks", []):
                    old_ko = w.get("label_ko")
                    new_ko, new_en = get_new_labels(w["startDate"])
                    if new_ko and (old_ko != new_ko or w.get("label_en") != new_en):
                        w["label_ko"] = new_ko
                        w["label_en"] = new_en
                        changed = True
                
                if changed:
                    print(f"    Updating year index.json")
                    with open(year_index_path, "w", encoding="utf-8") as f:
                        json.dump(yindex, f, ensure_ascii=False, indent=2)

    print("Success: Data patched.")

if __name__ == "__main__":
    patch_data()
