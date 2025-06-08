from dataclasses import dataclass

from rich.table import Table
from rich.console import Console
import matplotlib.ticker as mticker

import numpy as np

##########################################################################################################

class Scale:
    def __init__(self):
        pass

    def forward(self, x):
        return x
    
    def backward(self, y):
        return y

    def get_name(self) -> str:
        return ''
    
class SqrtScale:
    def __init__(self):
        pass

    def forward(self, x):
        return np.sqrt(x)
    
    def backward(self, y):
        return y**2

    def get_name(self) -> str:
        return ' (sqrt)'


##########################################################################################################

@dataclass
class Plotter:
    title: str

##########################################################################################################

@dataclass
class DoublePlotter(Plotter):
    years: np.ndarray
    left_data: np.ndarray
    right_data: np.ndarray
    left_label: str
    right_label: str
    left_scale: Scale
    right_scale: Scale
    left_color = 'tab:blue'
    right_color = 'tab:red'


    def plot(self, ax1):
        color = self.left_color
        ax1.set_xlabel('Year')
        ax1.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax1.set_xlim(self.years[0], self.years[-1])

        ax1.set_ylabel(self.left_label, color=color)
        ax1.plot(self.years, self.left_scale.forward(self.left_data), color=color, marker='o', label=self.left_label)
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{self.left_scale.backward(y):.0f}"))

        ax2 = ax1.twinx()
        color = self.right_color

        ax2.set_ylabel(self.right_label, color=color)
        ax2.plot(self.years, self.right_scale.forward(self.right_data), color=color, marker='s', label=self.right_label)
        ax2.tick_params(axis='y', labelcolor=color)
        ax2.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{self.right_scale.backward(y):.0f}"))
    
        ax1.set_title(self.title)
        return ax1, ax2

    def print(self, console:Console):
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Year", style="dim", width=6)
        table.add_column(self.left_label, justify="right")
        table.add_column(self.right_label, justify="right")

        for year, left, right in zip(self.years, self.left_data, self.right_data):
            table.add_row(str(year), str(left), str(right))

        console.print(f"[bold]{self.title}[/]")
        console.print(table)

##########################################################################################################

@dataclass
class DoubleAsymptotePlotter(DoublePlotter):
    left_years: np.ndarray
    right_years: np.ndarray
    left_prediction: np.ndarray
    right_prediction: np.ndarray
    left_text: str
    right_text: str

    def plot(self, ax1):
        ax1, ax2 = super().plot(ax1)

        color = self.left_color
        ax1.plot(self.left_years, self.left_scale.forward(self.left_prediction), color=color, ls='--')
        ax1.text(0.05, 0.9, self.left_text, ha='left', va='center', transform=ax1.transAxes, color=color)

        color = self.right_color
        ax2.plot(self.right_years, self.right_scale.forward(self.right_prediction), color=color, ls='--')
        ax2.text(0.05, 0.95, self.right_text, ha='left', va='center', transform=ax2.transAxes, color=color)




##########################################################################################################

class Mode:
    def __init__(self):
        pass

    def process(self, author):
        raise NotImplementedError
    
##########################################################################################################

class ModePubCit:
    name = 'idx'

    def process(self, author):
        return DoublePlotter(
            title=author.get('name'),
            years=author.get('years'),
            left_label='Citations',
            left_data=author.get('citations'),
            left_scale=Scale(),
            right_label='Publications',
            right_data=author.get('publications'),
            right_scale=Scale(),
        )
    
##########################################################################################################

def linear_fit(x, y):
    """Fit model y=a*x+b."""
    o = np.ones_like(x)
    A = np.vstack([x, o]).T
    a, b = np.linalg.lstsq(A, y)[0]
    return a, b

class ModeCumPubCit:
    name = 'cum'

    def __init__(self, nfit:int = 5, **kwargs):
        super().__init__(**kwargs)
        self.nfit = nfit

    def process(self, author):
        # compute cumulative sums
        years = author.get('years')
        cum_citations = np.cumsum(author.get('citations'))
        cum_publications = np.cumsum(author.get('publications'))
        sqrt_cum_citations = np.sqrt(cum_citations) # Scaled data.
        pa, pb = linear_fit(years[-self.nfit:], cum_publications[-self.nfit:])
        py = np.ceil(-pb/pa)
        ca, cb = linear_fit(years[-self.nfit:], sqrt_cum_citations[-self.nfit:])
        cy = np.ceil(-cb/ca)
        # Prediction.
        predicted_publications_years = np.linspace(py, years[-1], 10)
        predicted_cum_publications = pa*predicted_publications_years+pb
        predicted_citations_years = np.linspace(cy, years[-1], 10)
        predicted_sqrt_cum_citations = ca*predicted_citations_years+cb

        return DoubleAsymptotePlotter(
            title=author.get('name'),
            years=author.get('years'),

            left_label='Cumulative citations',
            left_data=cum_citations,
            left_scale=SqrtScale(),
            left_years=predicted_citations_years,
            left_prediction=predicted_sqrt_cum_citations**2,
            left_text=f"{ca:0.2f}",

            right_label='Cumulative publications',
            right_data=cum_publications,
            right_scale=Scale(),
            right_years=predicted_publications_years,
            right_prediction=predicted_cum_publications,
            right_text=f"{pa:0.2f}",
        )

##########################################################################################################
