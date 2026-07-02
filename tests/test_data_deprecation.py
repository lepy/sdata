# -*- coding: utf-8 -*-
"""Ablösung der Alt-Generation Data (RFC 0012, Stufe 1).

Deckt ab: direkte ``Data()``-Instanziierung warnt; Subklassen (Domäne/Experimente)
werden NICHT gestört; ``DataFrame`` ist Default-Export; ``Data`` bleibt für die
Deserialisierung alter Objekte über ``SDATACLS`` auflösbar."""
import warnings

import sdata
from sdata.deprecated.data import Data


def test_direct_data_instantiation_warns():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        Data(name="legacy")
    assert any(issubclass(x.category, DeprecationWarning)
               and "RFC 0012" in str(x.message) for x in w)


def test_subclass_does_not_warn():
    # Subklassen (wie Pud/TestProgram) sollen nicht spammen -> type(self) is Data-Guard
    class LegacySub(Data):
        pass

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)   # jede Warnung wäre ein Fehler
        LegacySub(name="sub")                                # darf NICHT warnen


def test_dataframe_is_default_export():
    assert sdata.__all__[0] == "DataFrame"
    assert "Data" in sdata.__all__               # weiterhin verfügbar, nur nicht führend


def test_data_still_resolvable_for_deserialization():
    # Alte Objekte tragen _sdata_class = "...:Data"; die Registry muss Data halten.
    assert sdata.SDATACLS["Data"] is Data
    assert sdata.SDATACLS["DataFrame"] is sdata.DataFrame


def test_import_sdata_does_not_warn():
    # frischer Interpreter mit -W error: der Import selbst darf nicht warnen
    # (kein Data() auf Modulebene)
    import subprocess
    import sys
    proc = subprocess.run(
        [sys.executable, "-W", "error::DeprecationWarning", "-c", "import sdata"],
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
