import os
from rich.console import Console
from rich.table import Table
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from .entity import Author
from .batch import AuthorsList

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


def plot_data(author, force_plot):
    os.makedirs("plots", exist_ok=True)
    # index plot
    author_name = author.get('name')
    idx_filename = f"plots/idx_{author_name.replace(' ', '_')}.pdf"
    if not os.path.exists(idx_filename) or force_plot:
        fig, ax1 = plt.subplots()
        panel_idx(ax1, author.get('years'), author.get('citations'), author.get('publications'))
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
        panel_cum(ax1, author.get('years'), author.get('citations'), author.get('publications'))
        ax1.set_title(f"{author_name}")
        fig.tight_layout()
        plt.savefig(cum_filename)
        print(f"Cumulative plot saved to {cum_filename}")
        plt.close()
    else:
        print(f"Cumulative plot already exists at {cum_filename}; skipping (use --force-plot to overwrite).")


def print_table(author):
    sorted_years = author.get('years_str')
    citedby = author.get('citedby_year')
    pubs = author.get('pubs_per_year')

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
    console.print(f"[bold]Author:[/] {author.get('name')} ({author.get('affiliation')})")
    console.print(f"[bold]Current h-index:[/] {author.get('hindex')}  (5y h-index: {author.get('hindex5y')})")
    console.print(table)

def load_author(author_id, force_reload) -> Author:
    if not force_reload:
        author = Author.load(author_id)
    else:
        author = Author(idx=author_id)
        print("Force reload enabled; skipping cache.")
    return author


def process_author(author_id, force_reload, do_plot, show_table, force_plot):
    author = load_author(author_id, force_reload)
    author_name = author.get('name')

    if show_table:
        print_table(author)

    if do_plot:
        plot_data(author, force_plot)

    author.save()
    return author_name

def process_author_axis(ax1, author_id, force_reload, min_year=1960):
    author = load_author(author_id, force_reload)
    author_name = author.get('name')

    panel_cum(ax1, author.get('years'), author.get('citations'), author.get('publications'))
    ax1.set_title(f"{author_name}")

    author.save()
    return author_name


def cli():
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
        for k in range(len(authors),ncols*nrows):
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
    