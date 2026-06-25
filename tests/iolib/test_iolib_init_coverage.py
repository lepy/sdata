# -*- coding: utf-8 -*-
"""Vollständige Abdeckung von sdata/iolib/__init__.py (PID)."""
import uuid as uuidlib

from sdata.iolib import PID


def test_pid_full():
    p = PID(name="x", uuid="c224fddec28245309cc4fe4912ac951f", metadata={})
    assert p.name == "x"
    assert isinstance(p.uuid, uuidlib.UUID)
    p.add_attr("k", 1)
    p.set_attr("k2", 2)
    assert p.get_attr("k") == 1
    assert p.get_attr("missing", "d") == "d"
    p.metadata = {"extra": 5}                 # set_metadata (update)
    assert p.get_metadata()["extra"] == 5
    assert "PID" in str(p) and "PID" in repr(p)


def test_pid_uuid_fallback():
    p = PID(name="y")                         # kein uuid -> uuid4-Zweig
    assert isinstance(p.uuid, uuidlib.UUID)
