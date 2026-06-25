# -*- coding: utf-8 -*-
"""Zusätzliche Tests zur vollständigen Abdeckung von sdata/base.py
(Serialisierung: gzip/zip, Factories, kleinere Branches)."""
import io
import zipfile

import pytest

from sdata.base import (
    Base, SdataUuidException, cls_from_spec, sclass_factory, sdata_factory,
)


# --- gzip ---------------------------------------------------------------
def test_to_from_bytes_gzip():
    b = Base(name="x", description="d", data={"k": 1})
    blob = b.to_bytes_gzip()
    assert isinstance(blob, bytes)
    r = Base.from_bytes_gzip(blob)
    assert r.name == "x" and r.description == "d" and r.data == {"k": 1}


# --- zip ----------------------------------------------------------------
def test_to_zip_roundtrip_bytes_and_bytesio(tmp_path):
    b = Base(name="zipme", data={"a": 1})
    buf = b.to_zip()                          # deterministic, BytesIO
    assert isinstance(buf, io.BytesIO)
    assert Base.from_zip(buf.getvalue()).name == "zipme"        # aus bytes
    assert Base.from_zip(b.to_zip()).data == {"a": 1}           # aus BytesIO


def test_to_zip_to_file_and_back(tmp_path):
    b = Base(name="zipme")
    p = tmp_path / "sub" / "out.zip"
    b.to_zip(filepath=p)                       # legt Verzeichnis an + schreibt
    assert p.exists()
    assert Base.from_zip(str(p)).name == "zipme"
    # aus generischem file-like Stream
    with open(p, "rb") as fh:
        assert Base.from_zip(fh).name == "zipme"


def test_to_zip_non_deterministic():
    b = Base(name="nd")
    buf = b.to_zip(deterministic=False, compresslevel=1)
    assert Base.from_zip(buf).name == "nd"


def test_from_zip_member_selection_and_ambiguity():
    b = Base(name="m")
    member = f"{b.sname}.sjson"
    assert Base.from_zip(b.to_zip().getvalue(), member=member).name == "m"

    # genau ein Nicht-.sjson-Eintrag -> automatisch gewählt
    one = io.BytesIO()
    with zipfile.ZipFile(one, "w") as zf:
        zf.writestr("only.json", b.to_json())
    assert Base.from_zip(one.getvalue()).name == "m"

    # mehrdeutig -> ValueError
    many = io.BytesIO()
    with zipfile.ZipFile(many, "w") as zf:
        zf.writestr("a.txt", "x")
        zf.writestr("b.txt", "y")
    with pytest.raises(ValueError):
        Base.from_zip(many.getvalue())


# --- suuid_str setter / suuid_bytes / did ------------------------------
def test_suuid_str_setter_and_bytes():
    b = Base(name="s")
    assert b.suuid_bytes == b.suuid_str.encode()
    b.suuid_str = b.suuid_str  # gültig -> ok
    with pytest.raises(SdataUuidException):
        b.suuid_str = "not-a-valid-token"


def test_did_and_did_method():
    b = Base(name="d")
    assert b.did.startswith("did:suuid:")
    assert isinstance(b.get_sdata_did_method(), str)


# --- Factories ----------------------------------------------------------
def test_cls_from_spec():
    C = cls_from_spec("sdata.base:Base")
    assert issubclass(C, Base)
    assert isinstance(C(name="z"), Base)
    # unbekannte Spec -> ignore liefert Base-Subklasse, strict wirft
    assert issubclass(cls_from_spec("nope.mod:Thing", on_error="ignore"), Base)
    with pytest.raises(ModuleNotFoundError):
        cls_from_spec("nope.mod:Thing", on_error="strict")


def test_sclass_factory():
    inst = sclass_factory("sdata.base:Base", name="w")
    assert isinstance(inst, Base) and inst.name == "w"
    assert isinstance(sclass_factory("nope:Thing", on_error="ignore", name="w2"), Base)
    with pytest.raises(ModuleNotFoundError):
        sclass_factory("nope:Thing", on_error="strict", name="w3")


def test_sdata_factory_basic():
    M = sdata_factory("Material", name="DP800")
    assert isinstance(M, Base) and M.class_name == "Material" and M.name == "DP800"


# --- kleinere Branches --------------------------------------------------
def test_suuid_kwarg_branch():
    a = Base(name="orig")
    b = Base(name="ignored", suuid=a.suuid)          # SUUID-Instanz -> übernommen
    assert b.suuid.sname == a.suuid.sname


def test_sname_setter():
    b = Base(name="snm")
    new = "Base__x__" + "0" * 32
    b.sname = new
    assert b.sname == new


def test_parent_project_properties():
    parent = Base(name="p")
    proj = Base(name="pr")
    child = Base(name="c", parent=parent, project=proj)
    assert child.parent.sname == parent.sname
    assert child.project.sname == proj.sname


def test_classname_from_classspec_no_colon():
    assert Base.classname_from_classspec("NoColon") == "NoColon"


def test_get_sdata_did_method_no_colon():
    b = Base(name="x")
    b.metadata.set_attr(b.SDATA_CLASS, "NoColonClass")   # Wert ohne ':'
    assert isinstance(b.get_sdata_did_method(), str)


def test_factory_specs_without_colon():
    assert issubclass(cls_from_spec("NoColon", on_error="ignore"), Base)
    assert isinstance(sclass_factory("NoColon", on_error="ignore", name="z"), Base)
