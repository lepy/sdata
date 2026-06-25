# -*- coding: utf-8 -*-
"""Vollständige Abdeckung von sdata/sclass/filereference.py."""
from sdata.sclass.filereference import FileReference, FileReferences


def test_filereference_init_basename():
    fr = FileReference(name="/some/folder/file.txt")
    assert fr.name == "file.txt"
    assert fr.filetype == ".txt"
    assert fr.stem == "file"


def test_filereference_from_file(tmp_path):
    p = tmp_path / "doc.pdf"
    p.write_bytes(b"hello pdf")
    fr = FileReference.from_file(str(p))
    assert fr.filetype == ".pdf" and fr.stem == "doc"
    assert fr.metadata.get("_sdata_sha3_256").value == FileReference.get_hash(str(p))
    assert fr.metadata.get("_sdata_filesize").value == len(b"hello pdf")
    assert fr.ctime is not None
    df = fr.to_dataframe()
    assert df.index[0] == fr.sname


def test_filereferences_collection(tmp_path):
    p = tmp_path / "a.csv"
    p.write_bytes(b"x")
    fr = FileReference.from_file(str(p))
    frs = FileReferences(name="coll")
    frs.add(fr)
    assert list(frs.get_filereferences()) == [fr]
    assert len(frs.get_filereferences_df()) == 1
