from __future__ import print_function, division

import pandas as pd
import numpy as np

import matplotlib.pyplot as plt

import statsmodels.formula.api as smf

import re


def read_gss(dirname, **options):
    """Reads GSS files from the given directory.

    dirname: string

    returns: DataFrame
    """
    dct = read_stata_dct(dirname + '/GSS.dct')
    options['compress'] = 'gzip'
    gss = dct.read_fixed_width(dirname + '/GSS.dat.gz', **options)
    return gss


def read_stata_dct(dct_file, **options):
    """Reads a Stata dictionary file.

    dct_file: string filename
    options: dict of options passed to open()

    returns: FixedWidthVariables object
    """
    type_map = dict(byte=int, int=int, long=int, float=float, 
                    double=float, numeric=float)

    var_info = []
    with open(dct_file, **options) as f:
        for line in f:
            match = re.search( r'_column\(([^)]*)\)', line)
            if not match:
                continue
            start = int(match.group(1))
            t = line.split()
            vtype, name, fstring = t[1:4]
            name = name.lower()
            if vtype.startswith('str'):
                vtype = str
            else:
                vtype = type_map[vtype]
            long_desc = ' '.join(t[4:]).strip('"')
            var_info.append((start, vtype, name, fstring, long_desc))
            
    columns = ['start', 'type', 'name', 'fstring', 'desc']
    variables = pd.DataFrame(var_info, columns=columns)

    # fill in the end column by shifting the start column
    variables['end'] = variables.start.shift(-1)
    variables.loc[len(variables)-1, 'end'] = 0

    dct = FixedWidthVariables(variables, index_base=1)
    return dct


class FixedWidthVariables(object):
    """Represents a set of variables in a fixed width file."""

    def __init__(self, variables, index_base=0):
        """Initializes.

        variables: DataFrame
        index_base: are the indices 0 or 1 based?

        Attributes:
        colspecs: list of (start, end) index tuples
        names: list of string variable names
        """
        self.variables = variables

        # note: by default, subtract 1 from colspecs
        self.colspecs = variables[['start', 'end']] - index_base

        # convert colspecs to a list of pair of int
        self.colspecs = self.colspecs.astype(np.int).values.tolist()
        self.names = variables['name']

    def read_fixed_width(self, filename, **options):
        """Reads a fixed width ASCII file.

        filename: string filename

        returns: DataFrame
        """
        df = pd.read_fwf(filename,
                         colspecs=self.colspecs, 
                         names=self.names,
                         **options)
        return df


def resample_by_year(df, column='wtssall'):
    """Resample rows within each year.

    df: DataFrame
    column: string name of weight variable

    returns DataFrame
    """
    grouped = df.groupby('year')
    samples = [resample_rows_weighted(group, column)
               for _, group in grouped]
    sample = pd.concat(samples, ignore_index=True)
    return sample


def resample_rows_weighted(df, column='finalwgt'):
    """Resamples a DataFrame using probabilities proportional to given column.

    df: DataFrame
    column: string column name to use as weights

    returns: DataFrame
    """
    weights = df[column].copy()
    weights /= sum(weights)
    indices = np.random.choice(df.index, len(df), replace=True, p=weights)
    sample = df.loc[indices]
    return sample


def values(df, varname):
    """Values and counts in index order.

    df: DataFrame
    varname: strign column name

    returns: Series that maps from value to frequency
    """
    return df[varname].value_counts().sort_index()


def fill_missing(df, varname, badvals=[98, 99]):
    """Fill missing data with random values.

    df: DataFrame
    varname: string column name
    badvals: list of values to be replaced
    """
    df[varname].replace(badvals, np.nan, inplace=True)
    null = df[varname].isnull()
    fill = np.random.choice(df[varname].dropna(), sum(null), replace=True)
    df.loc[null, varname] = fill
    return sum(null)


def RoundIntoBins(df, var, bin_width, high=None, low=0):
    """Rounds values down to the bin they belong in.

    df: DataFrame
    var: string variable name
    bin_width: number, width of the bins

    returns: array of bin values
    """
    if high is None:
        high = df[var].max()

    bins = np.arange(low, high+bin_width, bin_width)
    indices = np.digitize(df[var], bins)
    return bins[indices-1]

def decorate(**options):
    """Decorate the current axes.

    Call decorate with keyword arguments like

    decorate(title='Title',
             xlabel='x',
             ylabel='y')

    The keyword arguments can be any of the axis properties

    https://matplotlib.org/api/axes_api.html

    In addition, you can use `legend=False` to suppress the legend.

    And you can use `loc` to indicate the location of the legend
    (the default value is 'best')
    """
    loc = options.pop('loc', 'best')
    if options.pop('legend', True):
        legend(loc=loc)

    plt.gca().set(**options)
    plt.tight_layout()


def legend(**options):
    """Draws a legend only if there is at least one labeled item.

    options are passed to plt.legend()
    https://matplotlib.org/api/_as_gen/matplotlib.pyplot.legend.html

    """
    underride(options, loc='best')

    ax = plt.gca()
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles, labels, **options)

def underride(d, **options):
    """Add key-value pairs to d only if key is not in d.

    If d is None, create a new dictionary.

    d: dictionary
    options: keyword args to add to d
    """
    if d is None:
        d = {}

    for key, val in options.items():
        d.setdefault(key, val)

    return d

def save(root, formats=None, **options):
    """Saves the plot in the given formats and clears the figure.

    For options, see plt.savefig.

    Args:
      root: string filename root
      formats: list of string formats
      options: keyword args passed to plt.savefig
    """
    if formats is None:
        formats = ['png']

    for fmt in formats:
        save_format(root, fmt, **options)
        
def save_format(root, fmt='eps', **options):
    """Writes the current figure to a file in the given format.

    Args:
      root: string filename root
      fmt: string format
    """
    underride(options, dpi=300)
    filename = '%s.%s' % (root, fmt)
    print('Writing', filename)
    plt.savefig(filename, format=fmt, **options)