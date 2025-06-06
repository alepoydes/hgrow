import os
import json
import time
import sys
from scholarly import scholarly
from rich.console import Console
from rich.table import Table
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np


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

def linear_fit(x, y):
    """Fit model y=a*x+b."""
    o = np.ones_like(x)
    A = np.vstack([x, o]).T
    a, b = np.linalg.lstsq(A, y)[0]
    return a, b

def panel_idx(ax1, years, citations, publications):
    color = 'tab:blue'
    ax1.set_xlabel('Year')
    ax1.set_ylabel('Citations', color=color)
    ax1.plot(years, citations, color=color, marker='o', label='Citations')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Publications', color=color)
    ax2.plot(years, publications, color=color, marker='s', label='Publications')
    ax2.tick_params(axis='y', labelcolor=color)

def panel_cum(ax1, years, citations, publications, nfit=5):
    # compute cumulative sums
    cum_citations = np.cumsum(citations)
    cum_publications = np.cumsum(publications)
    sqrt_cum_citations = np.sqrt(cum_citations) # Scaled data.
    pa, pb = linear_fit(years[-nfit:], cum_publications[-nfit:])
    py = np.ceil(-pb/pa)
    ca, cb = linear_fit(years[-nfit:], sqrt_cum_citations[-nfit:])
    cy = np.ceil(-cb/ca)
    # Prediction.
    predicted_publications_years = np.linspace(py, years[-1], 10)
    predicted_cum_publications = pa*predicted_publications_years+pb
    predicted_citations_years = np.linspace(cy, years[-1], 10)
    predicted_sqrt_cum_citations = ca*predicted_citations_years+cb

    color = 'tab:blue'
    ax1.set_xlabel('Year')
    ax1.set_ylabel('Cumulative Citations', color=color)
    # apply sqrt scaling on y data
    ax1.plot(years, sqrt_cum_citations, color=color, marker='o', label='Cumulative Citations (sqrt)')
    ax1.plot(predicted_citations_years, predicted_sqrt_cum_citations, color=color, ls='--')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    # custom formatter to square the tick label
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{int(y**2)}"))
    ax1.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax1.axvline(cy, ls=':', color=color)
    ax1.set_xlim(years[0], years[-1])
    ax1.text(0.05, 0.9, f'{ca:.2f}', ha='left', va='center', transform=ax1.transAxes, color=color)

    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Cumulative Publications', color=color)
    ax2.plot(years, cum_publications, color=color, marker='s', label='Cumulative Publications')
    ax2.plot(predicted_publications_years, predicted_cum_publications, color=color, ls='--')
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax2.axvline(py, ls=':', color=color)
    ax2.set_xlim(years[0], years[-1])
    ax2.text(0.05, 0.95, f'{pa:.2f}', ha='left', va='center', transform=ax2.transAxes, color=color)


def plot_data(author_name, citedby, pubs, force_plot):
    years = sorted(set(int(y) for y in citedby.keys()) | set(int(y) for y in pubs.keys()))
    years = np.asarray(years)
    years_str = [str(y) for y in years]
    citations = [citedby.get(year, 0) for year in years_str]
    publications = [pubs.get(year, 0) for year in years_str]

    os.makedirs("plots", exist_ok=True)
    # index plot
    idx_filename = f"plots/idx_{author_name.replace(' ', '_')}.pdf"
    if not os.path.exists(idx_filename) or force_plot:
        fig, ax1 = plt.subplots()
        panel_idx(ax1, years, citations, publications)
        ax1.set_title(f"{author_name}")
        fig.tight_layout()
        plt.savefig(idx_filename)
        print(f"Index plot saved to {idx_filename}")
        plt.close()
    else:
        print(f"Index plot already exists at {idx_filename}; skipping (use --force-plot to overwrite).")

    # cumulative plot with sqrt scale for citations
    cum_filename = f"plots/cum_{author_name.replace(' ', '_')}.pdf"
    if not os.path.exists(cum_filename) or force_plot:
        fig, ax1 = plt.subplots()
        panel_cum(ax1, years, citations, publications)
        ax1.set_title(f"{author_name}")
        fig.tight_layout()
        plt.savefig(cum_filename)
        print(f"Cumulative plot saved to {cum_filename}")
        plt.close()
    else:
        print(f"Cumulative plot already exists at {cum_filename}; skipping (use --force-plot to overwrite).")


def print_table(data, author_name, citedby, pubs):
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
        citations_str = str(citedby.get(year_str, 0))
        pubs_str = str(pubs.get(year_str, 0))
        table.add_row(year_str, citations_str, pubs_str)

    console = Console()
    console.print(f"[bold]Author:[/] {author_name} ({data.get('affiliation')})")
    console.print(f"[bold]Current h-index:[/] {data.get('hindex')}  (5y h-index: {data.get('hindex5y')})")
    console.print(table)

def load_author(author_id, force_reload):
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
    return data


def process_author(author_id, force_reload, do_plot, show_table, force_plot):
    data = load_author(author_id, force_reload)
    author_name = data.get('name')
    citedby = data.get('citedby_year', {})
    pubs = data.get('pubs_per_year', {})

    if show_table:
        print_table(data, author_name, citedby, pubs)

    if do_plot:
        plot_data(author_name, citedby, pubs, force_plot)

    return author_name

def process_author_axis(ax1, author_id, force_reload):
    data = load_author(author_id, force_reload)
    author_name = data.get('name')
    citedby = data.get('citedby_year', {})
    pubs = data.get('pubs_per_year', {})

    years = sorted(set(int(y) for y in citedby.keys()) | set(int(y) for y in pubs.keys()))
    years = np.asarray(years)
    years_str = [str(y) for y in years]
    citations = [citedby.get(year, 0) for year in years_str]
    publications = [pubs.get(year, 0) for year in years_str]

    panel_cum(ax1, years, citations, publications)
    ax1.set_title(f"{author_name}")

    return author_name


class AuthorsList:
    def __init__(self, authors):
        self.authors = authors

    def __iter__(self):
        return iter(self.authors.keys())
    
    def __getitem__(self, key):
        return self.authors[key]
    
    def __setitem__(self, key, value):
        self.authors[key] = value

    def __len__(self):
        return len(self.authors)

    @classmethod
    def load(cls, file_path):
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            sys.exit(1)
        # Read IDs, process, and update file
        authors = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                lst = stripped.split()
                author_id = lst[0]
                authors[author_id] = lst[1:]
        return cls(authors)
    
    def save(self, file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            for author_id, data in self.authors.items():
                author_name, *_ = data
                f.write(f"{author_id}\t{author_name}\n")
        print(f"Updated file with author names: {file_path}")


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

    # Subcommand: list
    combo_parser = subparsers.add_parser('combo', help='Plot multiple authors metric in single figure')
    combo_parser.add_argument('file_path', help='File with author IDs in first column')
    combo_parser.add_argument('-f', '--force', action='store_true', help='Force reloading data instead of using cache')

    args = parser.parse_args()

    if args.command == 'author':
        process_author(args.author_id, args.force, args.plot, args.table, args.force_plot)
    elif args.command == 'list':
        file_path = args.file_path
        authors = AuthorsList.load(file_path)
        for author_id in authors:
            author_name = process_author(author_id, args.force, args.plot, args.table, args.force_plot)
            authors[author_id] = [author_name]
        authors.save(file_path)
    elif args.command == 'combo':
        file_path = args.file_path
        authors = AuthorsList.load(file_path)
        ncols = 4
        nrows = (len(authors)-1)//ncols+1
        fig, axes = plt.subplots(ncols=ncols,nrows=nrows, figsize=(5*ncols,3*nrows), layout='compressed', squeeze=False)
        
        for n, author_id in enumerate(authors):
            # print(f"{n=} {author_id=}")
            author_name = process_author_axis(axes[n//ncols,n%ncols], author_id, args.force)
            authors[author_id] = [author_name]
        for k in range(n,ncols*nrows):
            axes[k//ncols,k%ncols].set_axis_off()
        
        # Save
        os.makedirs("plots", exist_ok=True)
        plot_filename = f"{file_path}.cum.pdf"
        fig.savefig(plot_filename)
        print(f"Index plot saved to {plot_filename}")
        plt.close()
        # Update authors.
        authors.save(file_path)
    else:
        print(f"Unknown command {args.command}")
        sys.exit(1)
    


if __name__ == "__main__":
    main()
