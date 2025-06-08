import os
import json
from pathlib import Path


def get_storage_root():
    home = Path.home()
    folder = home / '.hgrow'
    os.makedirs(folder, exist_ok=True)
    return folder

def get_cache_path(author_id, cache_dir="cache"):
    folder = get_storage_root() / cache_dir
    os.makedirs(folder, exist_ok=True)
    return folder / f"{author_id}.json"

def load_cache(author_id):
    cache_path = get_cache_path(author_id)
    if os.path.exists(cache_path):
        print(f"Loading cache from {cache_path}...")
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_cache(author_id, data):
    cache_path = get_cache_path(author_id)
    print(f"Saving data to cache at {cache_path}...")
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


