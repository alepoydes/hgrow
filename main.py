import os
import json
import time
from scholarly import scholarly
from rich.console import Console
from rich.table import Table

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
    Fetch author data from Google Scholar using scholarly. Returns a dict with relevant fields including yearly citations and publications count.
    """
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
    # Yearly citations
    if 'cites_per_year' in author_filled:
        data['citedby_year'] = {str(year): count for year, count in author_filled['cites_per_year'].items()}
    else:
        data['citedby_year'] = {}
    # Current h-index
    data['hindex'] = author_filled.get('hindex', 0)
    data['hindex5y'] = author_filled.get('hindex5y', 0)
    # Publications per year
    pubs_per_year = {}
    pubs = author_filled.get('publications', [])
    for pub in pubs:
        pub_year = pub.get('bib', {}).get('pub_year')
        if pub_year and pub_year.isdigit():
            pubs_per_year[pub_year] = pubs_per_year.get(pub_year, 0) + 1
    data['pubs_per_year'] = pubs_per_year
    # Timestamp
    data['fetched_at'] = time.time()
    return data


def main(author_id, force_reload=False):
    console = Console()
    # Attempt to load from cache unless force_reload is True
    data = None
    if not force_reload:
        cached = load_cache(author_id)
    else:
        cached = None
        print("Force reload enabled; skipping cache.")

    if cached is None:
        print(f"Cache not used for author {author_id}. Fetching new data...")
        data = fetch_author_data(author_id)
        save_cache(author_id, data)
    else:
        print(f"Data loaded from cache for author {author_id}.")
        data = cached

    # Prepare data for table
    citedby = data.get('citedby_year', {})
    pubs = data.get('pubs_per_year', {})
    all_years = set()
    all_years.update(int(y) for y in citedby.keys())
    all_years.update(int(y) for y in pubs.keys())
    sorted_years = sorted(all_years)

    # Create and populate table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Year", style="dim", width=6)
    table.add_column("Citations", justify="right")
    table.add_column("Publications", justify="right")

    for year in sorted_years:
        year_str = str(year)
        citations = str(citedby.get(year_str, 0))
        publications = str(pubs.get(year_str, 0))
        table.add_row(year_str, citations, publications)

    # Print author info and table
    console.print(f"[bold]Author:[/] {data.get('name')} ({data.get('affiliation')})")
    console.print(f"[bold]Current h-index:[/] {data.get('hindex')}  (5y h-index: {data.get('hindex5y')})")
    console.print(table)

if __name__ == "__main__":
    import argparse, sys
    parser = argparse.ArgumentParser(description="Display yearly citations, h-index, and publications count for a Google Scholar author.")
    parser.add_argument('author_id', help="Google Scholar author ID (found in profile URL)")
    parser.add_argument('-f', '--force', action='store_true', help="Force reloading data instead of using cache")
    args = parser.parse_args()
    try:
        main(args.author_id, force_reload=args.force)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
