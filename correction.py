import json
import os
import re
import os, json, re, difflib

folder1 = "reviews"
folder2 = "multimodal_rag"

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, filepath):
    with open("./logs/" + filepath + ".json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def clean_text(text):
    return re.sub(r'[^A-Za-z0-9 ]+', '', text.replace('\n', ' ').replace('\r', '')).strip()


# Build a map from abstract to title for folder1
abstract_title_map = {}
for f in os.listdir(folder1):
    if f.endswith(".json"):
        data = load_json(os.path.join(folder1, f))
        key = clean_text(data.get("multimodal_rag_review", ""))
        abstract_title_map[key] = data.get("title", "")

abstracts1 = list(abstract_title_map.keys())


# Match and update folder2 titles
for f in os.listdir(folder2):
    if f.endswith(".json"):
        path = os.path.join(folder2, f)
        d = load_json(path)
        abs_clean = clean_text(d.get("rev", ""))
        
        # find closest match with at least 0.8 similarity (adjust if needed)
        match = difflib.get_close_matches(abs_clean, abstracts1, n=1, cutoff=0.6)
        
        if match:
            best_match = match[0]
            d["title"] = abstract_title_map[best_match]
            title_processed = re.sub(r'[^a-z0-9_]+', '', '_'.join(d["title"].lower().split()))
            print(f'Updated: {f} → {title_processed}')
            save_json(d, "log_" + title_processed)
        else:
            print(f"No close match found for {f}")
