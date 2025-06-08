from typing import Dict, Callable, List, Set
import time

from scholarly import scholarly
import numpy as np

from .storage import save_cache, load_cache

class Entity:
    def __init__(self, idx:str, data:dict=None, cacheable:Set[str]=None):
        self._idx = idx 
        self._data = {'fetched_at':None} if data is None else data
        self._requested = set()
        self._rules = self.get_rules()
        self._updated = False
        self._cacheable = set(data.keys()) if cacheable is None else cacheable

    @classmethod
    def load(cls, idx:str):
        data = load_cache(idx)
        return cls(idx=idx, data=data)

    def save(self):
        if self._updated:
            save_cache(self._idx, {k:self._data[k] for k in self._data.keys() if k in self._cacheable})
            self._updated = False

    def get_rules(self) -> Dict[str, Callable]:
        return {}
    
    def __in__(self, key):
        return key in self._data
    
    def get(self, key):
        if key in self._requested:
            raise KeyError(f"Circular dependence for key '{key}'. Stack: {self._requested}")
        if key not in self._data:
            if key in self._rules:
                self._requested.add(key)
                cacheable, noncacheable = self._rules[key]()
                self._requested.remove(key)
                self.append(cacheable, cacheable=True)
                self.append(noncacheable, cacheable=False)
            else:
                raise KeyError(f"No rule to generate '{key}'")
        return self._data[key]

    def set(self, key, value, cacheable:bool=False):
        self._data[key] = value
        if cacheable:
            self._cacheable.add(key)
            self._updated = True

    def append(self, pairs, cacheable:bool=False):
        for key, value in pairs.items():
            self.set(key, value, cacheable)

###############################################################################################

class Author(Entity):
    def pause(self):
        time.sleep(5)

    def get_rules(self):
        return {
            **super().get_rules(),
            'name': self._rule_author,
            'affiliation': self._rule_author,
            'citedby_year': self._rule_author,
            'pubs_per_year': self._rule_author,
            'hindex': self._rule_author,
            'hindex5y': self._rule_author,
            'years': self._rule_years, 
            'years_str': self._rule_years, 
            'citations': self._rule_years, 
            'publications': self._rule_years,
        }

    ###

    def _rule_author(self):
        """
        Fetch author data from Google Scholar using scholarly. Returns a dict with relevant fields including yearly citations and publications count.
        """
        author_id = self._idx
        print(f"Searching for author ID: {author_id}...")
        author = scholarly.search_author_id(author_id)
        print(f"Author found ({author_id=}, {author=}). Pausing briefly before filling profile...")
        self.pause()

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
        return data, {}

    ###

    def _rule_years(self, min_year=1960):
        citedby = self.get('citedby_year')
        pubs = self.get('pubs_per_year')

        years = set(int(y) for y in citedby.keys()) | set(int(y) for y in pubs.keys())
        years = sorted(filter(lambda y:y>min_year, years))
        years_str = [str(y) for y in years]
        citations = [citedby.get(year, 0) for year in years_str]
        publications = [pubs.get(year, 0) for year in years_str]

        return {}, {
            'years':np.asarray(years, dtype=np.int32), 
            'years_str':years_str, 
            'citations':np.asarray(citations, dtype=np.int32), 
            'publications': np.asarray(publications, dtype=np.int32),
            }

