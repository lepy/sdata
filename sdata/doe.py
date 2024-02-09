# -*-coding: utf-8-*-


import collections
from sdata.contrib.ranger import Range
import sdata.contrib.sobol_seq
from sdata.contrib.sobol_seq import Sobol
import pandas as pd
class DOE():
    """
    DoE Generator

    params_ranges = {"sheet_thickness": [0.8, 1.8],
                 "slant_depth": [10., 50.],}
    doe = DOE(params_ranges)

    """
    def __init__(self, ranges=None, name="N.N."):
        """DoE Generator

        params_ranges = {"sheet_thickness": [0.8, 1.8],
                 "slant_depth": [10., 50.],}
        doe = DOE(params_ranges)

        :param ranges:
        :param name:
        """

        self._ranges = collections.OrderedDict()
        if ranges is not None:
            for param_name, l in ranges.items():
                r = Range.closed(float(min(l)), float(max(l)))
                self._ranges[param_name] = r

    def add_range(self, param_name, l):
        """add range

        :param param_name: str
        :param range: [min, max]
        :return:
        """
        r = Range.closed(float(min(l)), float(max(l)))
        self._ranges[param_name] = r

    @property
    def ranges(self):
        return self._ranges

    @property
    def dim_num(self):
        return len(self._ranges)

    def gen_sobol01(self, n=1):
        S = Sobol()
        X = S.i4_sobol_generate(dim_num=self.dim_num, n=n, skip=1)
        df = pd.DataFrame(X, columns=self._ranges.keys())
        df["doe_id"] = range(1, len(X)+1)
        df.set_index("doe_id", inplace=True)
        return df

    def gen_sobol(self, n=1):
        S = Sobol()
        X = S.i4_sobol_generate(dim_num=self.dim_num, n=n, skip=1)
        df = pd.DataFrame(X, columns=self._ranges.keys())
        df["doe_id"] = range(1, len(X)+1)
        df.set_index("doe_id", inplace=True)
        for param_name, r in self._ranges.items():
            df[param_name] *= r.length
            df[param_name] += r.min
        return df

    def to_data(self, name, df_doe, uid=None):
        """

        :param df_doe: design table
        :return: sdata.Data
        """
        data = sdata.Data(name=name, uuid=uid, table=df_doe, description="my DoE")
        for parameter_name, r in self.ranges.items():
            data.metadata.add(parameter_name, r, unit="?", description=f"parameter range {parameter_name}",
                              label=rf"${parameter_name}$")
        return data

if __name__ == '__main__':
    import logging
    try:
        from itertools import combinations
        import matplotlib.pyplot as plt
        def plot_doe(df, figsize=(10,10), alpha=.5, s=5, dpi=150):
            dim_num = len(df.columns)
            fig, axs = plt.subplots(dim_num-1, dim_num-1, figsize=figsize, dpi=dpi)
            for i, j in list(combinations(range(dim_num), 2)):
                xi = df.columns[i]
                xj = df.columns[j]
                axs[i][j-1].scatter(df.iloc[:,i], df.iloc[:,j], alpha=alpha, s=s)
                axs[i][j-1].set_xlabel(xi)
                axs[i][j-1].set_ylabel(xj)
            fig.tight_layout()
    except Exception as exp:
        logging.warning(f"doe: {exp}")