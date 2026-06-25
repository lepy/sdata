# -*- coding: utf-8 -*-
"""Vollständige Abdeckung von sdata/sclass/zipfile.py."""
import io
import zipfile as zf_mod

import pytest

from sdata.base import Base
from sdata.sclass.zipfile import ZipFile


def _zip_with_file(tmp_path):
    p = tmp_path / "a.txt"
    p.write_bytes(b"hello")
    z = ZipFile(name="z")
    z.add(str(p))
    return z


def test_add_and_dataframes(tmp_path):
    z = _zip_with_file(tmp_path)
    assert len(list(z.get_filereferences())) == 1
    assert len(z.get_filereferences_df()) == 1


def test_to_zip_variants_and_from_zip(tmp_path):
    z = _zip_with_file(tmp_path)
    buf = z.to_zip()                         # deterministic, BytesIO
    assert isinstance(buf, io.BytesIO)
    out = tmp_path / "sub" / "out.zip"
    z.to_zip(filepath=out)                   # in Datei
    assert out.exists()
    z.to_zip(deterministic=False)            # nicht-deterministisch
    # from_zip: bytes / Pfad / BytesIO / file-like
    assert ZipFile.from_zip(buf.getvalue()) is not None
    assert ZipFile.from_zip(str(out)) is not None
    assert ZipFile.from_zip(z.to_zip()) is not None
    with open(out, "rb") as fh:
        assert ZipFile.from_zip(fh) is not None


def test_from_zip_member_single_and_ambiguity(tmp_path):
    z = _zip_with_file(tmp_path)
    fr_sname = list(z.filereferences.keys())[0]
    member = f"{fr_sname}.sjson"
    assert ZipFile.from_zip(z.to_zip().getvalue(), member=member) is not None

    valid_json = Base(name="x").to_json()
    one = io.BytesIO()
    with zf_mod.ZipFile(one, "w") as zf:
        zf.writestr("only.json", valid_json)     # einzelner Nicht-.sjson-Eintrag
    assert ZipFile.from_zip(one.getvalue()) is not None

    many = io.BytesIO()
    with zf_mod.ZipFile(many, "w") as zf:
        zf.writestr("a.txt", "x")
        zf.writestr("b.txt", "y")
    with pytest.raises(ValueError):              # mehrdeutig
        ZipFile.from_zip(many.getvalue())
