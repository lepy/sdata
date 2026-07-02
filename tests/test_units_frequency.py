# -*- coding: utf-8 -*-
"""Frequenz-Einheiten Hz/kHz/MHz/GHz (RFC 0006, Folge zu open-points).

`Hz` & Co. sind als benannte Einheiten erkennbar/konvertierbar und QUDT-gemappt.
Die kanonische Rück-Benennung der Rate/Frequenz-Dimension bleibt bewusst neutral
(`1/s`/`1/ms`), weil dieselbe Dimension auch die Dehnrate bezeichnet.
"""
import pandas as pd

from sdata.units import convert, convert_factor, dimension_of, quantity_of, UnitSystem
from sdata.sclass.dataframe import DataFrame


def test_hz_family_recognized():
    for sym in ("Hz", "kHz", "MHz", "GHz"):
        assert dimension_of(sym) == (0, 0, -1, 0)
        assert quantity_of(sym) == "rate"


def test_hz_interconversion():
    assert convert_factor("kHz", "Hz") == 1000.0
    assert convert_factor("MHz", "kHz") == 1000.0
    assert convert_factor("GHz", "MHz") == 1000.0
    assert convert_factor("Hz", "1/s") == 1.0          # Hz == 1/s
    assert convert_factor("kHz", "1/ms") == 1.0        # kHz == 1/ms
    assert convert(2.0, "kHz", "Hz") == 2000.0


def test_hz_aliases():
    assert dimension_of("hertz") == (0, 0, -1, 0)
    assert dimension_of("khz") == (0, 0, -1, 0)


def test_backnaming_stays_neutral_not_hz():
    # Frequenz/Rate wird NICHT automatisch als Hz benannt (Dehnrate-Schutz)
    s_ms = UnitSystem(["kN", "mm", "ms"])
    assert s_ms.target_for("Hz") == "1/ms"
    assert s_ms.target_for("1/s") == "1/ms"
    s_s = UnitSystem(["m", "kg", "s"])
    assert s_s.target_for("Hz") == "1/s"
    assert s_s.target_for("1/s") == "1/s"


def test_energy_still_names_joule():
    # Regression zur zweiten mehrdeutigen Dimension (N*m vs J): Energie -> J
    s = UnitSystem(["m", "kg", "s"])
    assert s.unit_for("energy") == "J"
    assert s.target_for("J") == "J"


def test_convert_hz_column_in_dataframe():
    sdf = DataFrame(df=pd.DataFrame({"freq": [1.0, 2.0]}), name="f")
    sdf.set_column("freq", unit="kHz")
    out = sdf.convert({"freq": "Hz"})
    assert out.get_column("freq").unit == "Hz"
    assert out.df["freq"].tolist() == [1000.0, 2000.0]


def test_hz_column_jsonld_qudt():
    sdf = DataFrame(df=pd.DataFrame({"freq": [50.0]}), name="f")
    sdf.set_column("freq", unit="Hz")
    col = sdf.to_jsonld()["columns"][0]
    assert col["unitRef"] == "unit:HZ"
    assert col["symbol"] == "Hz"
