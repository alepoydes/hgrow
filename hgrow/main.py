import os
import numpy as np

from .entity import Author
from .batch import AuthorsList
from .mode import ModePubCit, ModeCumPubCit, ModeProduct
from .plot import ComboPlot, TablePlot, SinglePlot

##############################################################################################################

def load_author(author_id, force_reload) -> Author:
    if not force_reload:
        author = Author.load(author_id)
    else:
        author = Author(idx=author_id)
        print("Force reload enabled; skipping cache.")
    return author

##############################################################################################################

def cli():
    import argparse, sys
    # Parse command line.
    parser = argparse.ArgumentParser(description="Extract, process and plot metrics from Google Scholar.")
    parser.add_argument('-f', '--force', action='store_true', help='Force reloading data instead of using cache')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-a', '--author', dest='authors', default=None, nargs='+', help='Google Scholar author ID')
    group.add_argument('-l', '--list', dest='file_path', default=None, help='CSV file containing author ID in 1st column')

    group2 = parser.add_mutually_exclusive_group(required=True)
    group2.add_argument('-t', '--table', action='store_true', help='Print table to console')
    group2.add_argument('-p', '--plot', action='store_true', help='Save separate figure for each author')
    group2.add_argument('-c', '--combo', action='store_true', help='Save single figure containing plots for all authors')

    modes = ['idx','cum','prod']
    parser.add_argument('-m', '--mode',dest='mode', default='idx', help=f'Analysis mode: {" ".join(modes)}', choices=modes)

    args = parser.parse_args()

    # Find authors list.
    if args.file_path is not None:
        authors = AuthorsList.load(args.file_path)
    elif args.authors is not None:
        authors = AuthorsList(authors={author_id:[] for author_id in args.authors})
    else: 
        raise ValueError('No source file is provided')

    # Initialize modes and plotters.
    if args.mode == 'idx':
        mode = ModePubCit()
    elif args.mode == 'cum':
        mode = ModeCumPubCit()
    elif args.mode == 'prod':
        mode = ModeProduct()
    else:
        raise ValueError(f'Unexpected mode "{args.mode}"')

    if args.combo:
        plot = ComboPlot(
            mode=mode,
            nauthors=len(authors), 
            file_path=f"{mode.name}.pdf" if args.file_path is None else f"{args.file_path}.{mode.name}.pdf",
        )
    elif args.plot:
        plot = SinglePlot(mode=mode)
    elif args.table:
        plot = TablePlot(mode=mode)
    else:
        raise ValueError('No plot type specified')


    # Process authors.
    for author_id in authors:
        author = load_author(author_id, force_reload=args.force)
        authors[author_id] = [author.get('name')]
        plot.process(author)
    plot.finish()

    # Save updates authors list.
    if args.file_path is not None:
        authors.save(args.file_path)

