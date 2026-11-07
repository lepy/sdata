# -*- coding: utf-8 -*-
"""``strict=True`` greift auch beim Aktualisieren eines vorhandenen Attributs."""
import pytest

from sdata.dtypes import DtypeError
from sdata.metadata import Metadata


def test_strict_rejects_invalid_value_for_existing_attribute():
    m = Metadata()
    m.add("rate", 1.0, dtype="float")
    with pytest.raises(DtypeError):
        m.add("rate", "schnell", dtype="float", strict=True)
    assert m.get("rate").value == 1.0                 # unverändert


def test_strict_on_update_applies_to_this_call_only():
    m = Metadata()
    m.add("rate", 1.0, dtype="float")
    m.add("rate", 2.0, strict=True)
    assert m.get("rate").value == 2.0
    m.add("rate", "schnell")                          # nachsichtig wie zuvor
    assert m.get("rate").value == 2.0


def test_strict_attribute_stays_strict_unless_overridden():
    m = Metadata()
    m.add("n", 1, dtype="int", strict=True)
    with pytest.raises(DtypeError):
        m.add("n", "abc")
    m.add("n", "abc", strict=False)                   # ausdrücklich nachsichtig
    assert m.get("n").value == 1


def test_strict_new_attribute_still_rejects():
    with pytest.raises(DtypeError):
        Metadata().add("neu", "schnell", dtype="float", strict=True)
