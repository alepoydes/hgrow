import os
import json
import time
from scholarly import scholarly, ProxyGenerator

def init_proxy():
    # Initialize a proxy generator to avoid blocking (e.g., Tor)
    pg = ProxyGenerator()
    try:
        print("Initializing proxy using FreeProxies...")
        pg.FreeProxies()
        scholarly.use_proxy(pg)
        print("Proxy initialized successfully.")
    except Exception as e:
        print(f"Proxy initialization failed ({e}); proceeding without proxy.")


def load_cache(author_id, cache_dir="cache"):
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"{author_id}.json")
    if os.path.exists(cache_path):
        print(f"Loading cache from {cache_path}...")
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_cache(author_id, data, cache_dir="cache"):
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"{author_id}.json")
    print(f"Saving data to cache at {cache_path}...")
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_author_data(author_id):
    """
    Fetch author data from Google Scholar using scholarly. Returns a dict with relevant fields including yearly citations.
    """
    init_proxy()

    print(f"Searching for author ID: {author_id}...")
    author = scholarly.search_author_id(author_id)
    print("Author found. Pausing briefly before filling profile...")
    time.sleep(5)

    print("Filling author profile...")
    author_filled = scholarly.fill(author, sections=["indices", "basics", "publications", "counts"])  
    print("Profile filled. Extracting data...")

    data = {}
    # Basics
    data['name'] = author_filled.get('name')
    data['affiliation'] = author_filled.get('affiliation')
    # Yearly citations: use 'cites_per_year' if present
    if 'cites_per_year' in author_filled:
        data['citedby_year'] = {str(year): count for year, count in author_filled['cites_per_year'].items()}
    else:
        data['citedby_year'] = {}
    # Current h-index (no yearly data available)
    data['hindex'] = author_filled.get('hindex', 0)
    data['hindex5y'] = author_filled.get('hindex5y', 0)
    # Timestamp
    data['fetched_at'] = time.time()
    return data


def main(author_id):
    # Attempt to load from cache
    cached = load_cache(author_id)
    if cached is None:
        print(f"Cache not found for author {author_id}. Fetching new data...")
        data = fetch_author_data(author_id)
        save_cache(author_id, data)
    else:
        print(f"Data loaded from cache for author {author_id}.")
        data = cached

    # Output results: citations per year
    citedby = data.get('citedby_year', {})
    years = sorted(int(y) for y in citedby.keys())

    print(f"Author: {data.get('name')} ({data.get('affiliation')})")
    print(f"Current h-index: {data.get('hindex')}  (5y h-index: {data.get('hindex5y')})")
    print("\nYearly Citations:")
    print(f"{'Year':<6} {'Citations':<10}")
    for year in years:
        print(f"{year:<6} {citedby.get(str(year), 0):<10}")

if __name__ == "__main__":
    import argparse, sys
    parser = argparse.ArgumentParser(description="List yearly citations and h-index for a Google Scholar author.")
    parser.add_argument('author_id', help="Google Scholar author ID (found in profile URL)")
    args = parser.parse_args()
    try:
        main(args.author_id)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
