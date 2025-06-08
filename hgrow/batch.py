from typing import List, Dict
import sys
import os

class AuthorsList:
    def __init__(self, authors:Dict[str,List[str]]):
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
                txt = '\t'.join(data)
                f.write(f"{author_id}\t{txt}\n")
        print(f"Updated file with author names: {file_path}")
