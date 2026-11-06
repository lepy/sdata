# -*-coding: utf-8-*-


import collections
import sdata
import sdata.contrib.sobol_seq
from sdata.contrib.sobol_seq import Sobol
import pandas as pd
from sdata.sclass.dataframe import DataFrame


class Range:
    """Geschlossenes Intervall ``[min, max]`` eines DoE-Parameters.

    Ersetzt das früher vendorte ``ranger.Range`` (BSD); sdata nutzt davon nur
    :meth:`closed`, :attr:`min`, :attr:`max`, :attr:`length` und die Textform
    ``"[min , max]"``, die so auch in den Metadaten landet.
    """

    __slots__ = ("min", "max")

    def __init__(self, lower, upper):
        if lower > upper:
            raise ValueError("Lower bound cannot be greater than upper bound")
        self.min = lower
        self.max = upper

    @classmethod
    def closed(cls, lower, upper):
        return cls(lower, upper)

    @property
    def length(self):
        return self.max - self.min

    def __eq__(self, other):
        if not isinstance(other, Range):
            return NotImplemented
        return (self.min, self.max) == (other.min, other.max)

    def __hash__(self):
        return hash((self.min, self.max))

    def __repr__(self):
        return f"[{self.min!r} , {self.max!r}]"

    __str__ = __repr__


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
        df = df.set_index("doe_id")
        return df

    def gen_sobol(self, n=1):
        S = Sobol()
        X = S.i4_sobol_generate(dim_num=self.dim_num, n=n, skip=1)
        df = pd.DataFrame(X, columns=self._ranges.keys())
        df["doe_id"] = range(1, len(X)+1)
        df = df.set_index("doe_id")
        for param_name, r in self._ranges.items():
            df[param_name] *= r.length
            df[param_name] += r.min
        return df

    def to_data(self, name, df_doe, uid=None):
        """Design-Tabelle als :class:`~sdata.sclass.dataframe.DataFrame` verpacken.

        Die Parameterbereiche landen in den Objekt-Metadaten (je Parameter ein
        Attribut mit dem Bereich als Wert).

        :param name: Name des Datenobjekts.
        :param df_doe: Design-Tabelle (z. B. aus :meth:`gen_sobol`).
        :param uid: optionale Identität — eine :class:`~sdata.suuid.SUUID` oder
          ein UUID-Hex-String; ohne Angabe wird die SUUID deterministisch aus
          Klasse und ``name`` abgeleitet.
        :return: sdata.sclass.dataframe.DataFrame
        """
        kwargs = {}
        if isinstance(uid, sdata.SUUID):
            kwargs["suuid"] = uid
        elif uid is not None:
            # Fremd vorgegebene UUID (Hex, mit oder ohne Bindestriche) übernehmen.
            kwargs["suuid"] = sdata.SUUID(DataFrame.__name__, name, huuid=str(uid).replace("-", ""))
        # Benannten Index (z. B. "doe_id") zur Spalte machen: DataFrame
        # serialisiert ohne Index, die Versuchs-ID ginge sonst verloren.
        if df_doe.index.name is not None and df_doe.index.name not in df_doe.columns:
            df_doe = df_doe.reset_index()
        data = DataFrame(df=df_doe, name=name, description="my DoE", **kwargs)
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