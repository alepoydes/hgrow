from dataclasses import dataclass

from rich.table import Table
from rich.console import Console
import matplotlib.ticker as mticker

import numpy as np
import scipy
import scipy.special

##########################################################################################################

class Scale:
    def __init__(self, digits:int=0):
        self.digits = digits

    def forward(self, x):
        return x
    
    def backward(self, y):
        return y

    def get_name(self) -> str:
        return ''
    
class SqrtScale(Scale):
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
    left_color:str = 'tab:blue'
    right_color:str = 'tab:red'
    left_text: str = None
    right_text: str = None


    def plot(self, ax1):
        color = self.left_color
        ax1.set_xlabel('Year')
        ax1.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        if self.years.shape[0]>0:
            ax1.set_xlim(self.years[0], self.years[-1])

        ax1.set_ylabel(self.left_label, color=color)
        ax1.plot(self.years, self.left_scale.forward(self.left_data), color=color, marker='o', label=self.left_label)
        ax1.tick_params(axis='y', labelcolor=color)
        if self.left_scale.digits==0:
            ax1.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{self.left_scale.backward(y):.{self.right_scale.digits}f}"))
        if self.left_text is not None:
            ax1.text(0.05, 0.9, self.left_text, ha='left', va='center', transform=ax1.transAxes, color=color)

        if self.right_data is not None:
            ax2 = ax1.twinx()
            color = self.right_color

            ax2.set_ylabel(self.right_label, color=color)
            ax2.plot(self.years, self.right_scale.forward(self.right_data), color=color, marker='s', label=self.right_label)
            ax2.tick_params(axis='y', labelcolor=color)
            if self.right_scale.digits==0:
                ax2.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
            ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{self.right_scale.backward(y):.{self.right_scale.digits}f}"))
            if self.right_text is not None:
                ax2.text(0.05, 0.95, self.right_text, ha='left', va='center', transform=ax2.transAxes, color=color)


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
    left_years: np.ndarray = None
    right_years: np.ndarray = None
    left_prediction: np.ndarray = None
    right_prediction: np.ndarray = None

    def plot(self, ax1):
        ax1, ax2 = super().plot(ax1)

        color = self.left_color
        if self.left_prediction is not None:
            ax1.plot(self.left_years, self.left_scale.forward(self.left_prediction), color=color, ls='--')

        color = self.right_color
        if self.right_prediction is not None:        
            ax2.plot(self.right_years, self.right_scale.forward(self.right_prediction), color=color, ls='--')



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
        M = author.get('citations')
        P = author.get('publications')
        return DoublePlotter(
            title=author.get('name'),
            years=author.get('years'),
            left_label='Citations',
            left_data=M,
            left_scale=Scale(),
            left_text=f"{np.sum(M):.0f}",

            right_label='Publications',
            right_data=P,
            right_scale=Scale(),
            right_text=f"{np.sum(P):.0f}",
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

            left_color = 'tab:purple',
            right_color = 'tab:orange',
        )

##########################################################################################################

def log_normal_pdf(a, peak, sigma):
    msk = a>0
    a = np.maximum(a,1e-8)
    y = np.exp(-(np.log(a/peak))**2/(2*sigma**2))/(np.sqrt(2*np.pi)*sigma*a)
    return np.where(msk, y, 0)

def log_normal_cdf(a, peak, sigma):
    a = np.maximum(a,1e-8)
    return (1+scipy.special.erf( np.log(a/peak) / (sigma*np.sqrt(2)) ))/2

def log_normal_kernel(a, **kwargs):
    return log_normal_cdf(a+0.5, **kwargs) - log_normal_cdf(a-0.5, **kwargs)

def fit_poisson(M, q, niter):
    """ 
    Consider the model
        C_i = sum_j K_{ij} f_j, 
    where the kernel K_{ij}=q(j-i) is known.
    Given observations M_i of random values having Poisson distribution with mean C_i,
    the function computes MLE for f. 
    Iterative Richardson-Lucy solver is used.
    """
    assert M.ndim==1
    assert niter>=1
    t = np.arange(M.shape[0])
    K = q(t[:,None]-t[None,:])
    KK = K/np.sum(K,axis=0,keepdims=True)
    f = np.ones(M.shape, dtype=np.float32)
    # print(f"{K=}")
    # print(f"{M=}")
    # print(f"Initial {f=}")
    for n in range(niter):
        C = K@f
        # print(f"Iteration {n}: {C=}")
        f *= (M/C)@KK 
        # print(f"Iteration {n}: {f=}")
    return f, C


class ModeProduct:
    name = 'prod'

    def __init__(self, peak:float = 10, sigma=1.2, niter=30, drop_last=1, **kwargs):
        super().__init__(**kwargs)
        self.peak = peak
        self.sigma = sigma
        self.niter = niter
        self.drop_last = drop_last

    def decay_kernel(self, t):
        return log_normal_kernel(t, peak=self.peak, sigma=self.sigma)

    def process(self, author):
        # compute cumulative sums
        # P = author.get('publications')
        M = author.get('citations')
        n = M.shape[0]
        M = M[:n-self.drop_last]

        f, C = fit_poisson(M=M, q=self.decay_kernel, niter=self.niter)

        return DoublePlotter(
            title=author.get('name'),
            years=author.get('years')[:n-self.drop_last],

            left_label='Citations recorded',
            left_data=C,
            left_scale=Scale(digits=0),
            left_text=f"{np.sum(C):.0f}",

            right_label='Citations generated',
            right_data=f,
            right_scale=Scale(digits=0),
            right_text=f"{np.sum(f):.0f}",

            left_color = 'tab:blue',
            right_color = 'tab:green',

        )
