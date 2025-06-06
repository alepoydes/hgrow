import os
import json
import time
from scholarly import scholarly
from rich.console import Console
from rich.table import Table
import matplotlib.pyplot as plt


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
    data['fetched_at'] = time.time()
    return data


def plot_data(author_name, citedby, pubs, force_plot):
    os.makedirs("plots", exist_ok=True)
    filename = f"plots/{author_name.replace(' ', '_')}.pdf"
    if os.path.exists(filename) and not force_plot:
        print(f"Plot already exists at {filename}; skipping (use --force to overwrite).")
        return

    years = sorted(set(int(y) for y in citedby.keys()) | set(int(y) for y in pubs.keys()))
    years_str = [str(y) for y in years]
    citations = [citedby.get(year, 0) for year in years_str]
    publications = [pubs.get(year, 0) for year in years_str]

    fig, ax1 = plt.subplots()
    color = 'tab:blue'
    ax1.set_xlabel('Year')
    ax1.set_ylabel('Citations', color=color)
    ax1.plot(years, citations, color=color, marker='o', label='Citations')
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Publications', color=color)
    ax2.plot(years, publications, color=color, marker='s', label='Publications')
    ax2.tick_params(axis='y', labelcolor=color)

    plt.title(f"{author_name} - Citations and Publications Over Time")
    fig.tight_layout()
    plt.savefig(filename)
    print(f"Plot saved to {filename}")
    plt.close()


def process_author(author_id, force_reload, do_plot, show_table, force_plot):
    console = Console()
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

    author_name = data.get('name')
    citedby = data.get('citedby_year', {})
    pubs = data.get('pubs_per_year', {})

    if show_table:
        all_years = set()
        all_years.update(int(y) for y in citedby.keys())
        all_years.update(int(y) for y in pubs.keys())
        sorted_years = sorted(all_years)

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Year", style="dim", width=6)
        table.add_column("Citations", justify="right")
        table.add_column("Publications", justify="right")

        for year in sorted_years:
            year_str = str(year)
            citations = str(citedby.get(year_str, 0))
            publications = str(pubs.get(year_str, 0))
            table.add_row(year_str, citations, publications)

        console.print(f"[bold]Author:[/] {author_name} ({data.get('affiliation')})")
        console.print(f"[bold]Current h-index:[/] {data.get('hindex')}  (5y h-index: {data.get('hindex5y')})")
        console.print(table)

    if do_plot:
        plot_data(author_name, citedby, pubs, force_plot)

    return author_name


def main():
    import argparse, sys
    parser = argparse.ArgumentParser(description="Google Scholar author data utility.")
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Subcommand: author
    author_parser = subparsers.add_parser('author', help='Process a single author by ID')
    author_parser.add_argument('author_id', help='Google Scholar author ID')
    author_parser.add_argument('-f', '--force', action='store_true', help='Force reloading data instead of using cache')
    author_parser.add_argument('-p', '--plot', action='store_true', help='Generate and save plot as PDF')
    author_parser.add_argument('-t', '--table', action='store_true', help='Print table to console')
    author_parser.add_argument('--force-plot', action='store_true', help='Force regenerating plot even if it exists')

    # Subcommand: list
    list_parser = subparsers.add_parser('list', help='Process multiple authors from a file')
    list_parser.add_argument('file_path', help='File with author IDs in first column')
    list_parser.add_argument('-f', '--force', action='store_true', help='Force reloading data instead of using cache')
    list_parser.add_argument('-p', '--plot', action='store_true', help='Generate and save plots as PDF')
    list_parser.add_argument('-t', '--table', action='store_true', help='Print tables to console')
    list_parser.add_argument('--force-plot', action='store_true', help='Force regenerating plots even if they exist')

    args = parser.parse_args()

    if args.command == 'author':
        process_author(args.author_id, args.force, args.plot, args.table, args.force_plot)
    elif args.command == 'list':
        file_path = args.file_path
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            sys.exit(1)
        # Read IDs, process, and update file
        ids = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                ids.append(stripped.split()[0])

        updated_lines = []
        for author_id in ids:
            author_name = process_author(author_id, args.force, args.plot, args.table, args.force_plot)
            updated_lines.append((author_id, author_name))

        with open(file_path, 'w', encoding='utf-8') as f:
            for author_id, author_name in updated_lines:
                f.write(f"{author_id}\t{author_name}\n")
        print(f"Updated file with author names: {file_path}")

if __name__ == "__main__":
    main()
