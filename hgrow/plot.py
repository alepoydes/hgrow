from rich.console import Console
import matplotlib.pyplot as plt

from .entity import Author
from .mode import Mode

###############################################################################################

class ProtoPlot:
    def __init__(self, mode:Mode):
        self._mode = mode

    def process(self, author:Author):
        pass

    def finish(self):
        pass

###############################################################################################

class TablePlot(ProtoPlot):
    def process(self, author:Author):
        plotter = self._mode.process(author)
        console = Console()
        plotter.print(console)

###############################################################################################

class SinglePlot(ProtoPlot):
    def process(self, author:Author):
        plotter = self._mode.process(author)
        fig, ax = plt.subplots(figsize=(5,3), layout='compressed', squeeze=True)
        plotter.plot(ax)

        author_name = author.get('name')
        file_path = f"{self._mode.name}_{author_name.replace(' ', '_')}.pdf"
        fig.savefig(file_path)
        print(f"Plot is saved to {file_path}")

###############################################################################################

class ComboPlot(ProtoPlot):
    def __init__(self, nauthors:int, file_path:str, ncols:int=4, **kwargs):
        super().__init__(**kwargs)
        self._nauthors =  nauthors
        self._file_path = file_path
        self._ncols = ncols
        self._nrows = (self._nauthors-1)//ncols+1
        self._fig, self._axes = plt.subplots(ncols=self._ncols,nrows=self._nrows, figsize=(5*self._ncols,3*self._nrows), layout='compressed', squeeze=False)
        self._next = 0

    def process(self, author:Author):
        n = self._next 
        if n>=self._nauthors:
            raise ValueError(f'Number of authors {self._nauthors} is smaller than  number of plots.')
        self._next += 1
        ax = self._axes[n//self._ncols,n%self._ncols]
        plotter = self._mode.process(author)
        plotter.plot(ax)
        
    def finish(self):
        # Turn off unused axis.
        for k in range(self._next, self._ncols*self._nrows):
            self._axes[k//self._ncols,k%self._ncols].set_axis_off()
        
        # Save
        self._fig.savefig(self._file_path)
        print(f"Plot is saved to {self._file_path}")
