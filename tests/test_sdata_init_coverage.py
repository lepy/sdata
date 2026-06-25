# -*- coding: utf-8 -*-
"""Abdeckung der Helfer in sdata/__init__.py und sdata.suuid.SUUID.from_obj."""
import uuid as _uuid

import sdata
from sdata.suuid import SUUID


def test_uuid_from_str_and_osname():
    assert isinstance(sdata.uuid_from_str("x"), _uuid.UUID)
    assert sdata.osname("Hällo/Welt\\x") == "haello_welt_x"
    assert sdata.osname("ABC", lower=False) == "ABC"


def test_generate_safe_filename_branches():
    f = sdata.generate_safe_name
    assert f("Über Größe!") != ""          # Umlaute/Sonderzeichen
    assert f("a/b\\c:d") != ""             # verbotene Zeichen
    assert f("") == "noname"               # leer -> Fallback
    assert f(123) != ""                    # non-str
    assert not f("123start")[0].isdigit()  # Ziffern-Start -> '_' vorangestellt
    assert len(f("x" * 300)) <= 255        # Längenbegrenzung


def test_print_classes(capsys):
    sdata.print_classes()


def test_suuid_from_obj_none():
    assert SUUID.from_obj(123) is None     # weder Objekt mit sname noch String
