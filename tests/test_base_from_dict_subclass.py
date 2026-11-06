# -*- coding: utf-8 -*-
"""``Cls.from_dict`` liefert eine Instanz von ``Cls`` (bzw. der gespeicherten Unterklasse).

Vorher baute ``Base.from_dict`` per ``sdata_factory`` eine neue Klasse gleichen
Namens, die nur von ``Base`` erbte — ``Blob.from_dict`` ergab ein Objekt ohne
``content_bytes``/``verify``.
"""
import pytest

pytest.importorskip("fsspec")

from sdata.base import Base
from sdata.sclass.blob import Blob
from sdata.sclass.filereference import FileReference, FileReferences
from sdata.sclass.image import Image
from sdata.sclass.process import ProcessData, ProcessNode
from sdata.sclass.zipfile import ZipFile


@pytest.mark.parametrize("cls", [Blob, FileReference, FileReferences, Image,
                                 ZipFile, ProcessData, ProcessNode])
def test_from_dict_returns_calling_class(cls):
    obj = cls(name="t")
    restored = cls.from_dict(obj.to_dict())
    assert type(restored) is cls
    assert restored.to_dict() == obj.to_dict()


def test_blob_roundtrip_keeps_content_api(tmp_path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"abc")
    b = Blob(content_type="uri", value=str(p), filetype="bin", name="b")
    digest = b.update_checksum()
    restored = Blob.from_dict(b.to_dict())
    assert restored.content_bytes == b"abc"
    assert restored.verify() is True
    assert restored.metadata.get("checksum").value == digest
    assert restored.sname == b.sname


def test_from_dict_picks_stored_subclass():
    fr = FileReference(name="f")
    restored = Blob.from_dict(fr.to_dict())                 # gespeichert: FileReference
    assert type(restored) is FileReference


def test_base_from_dict_unchanged_generic_class():
    """Generisches Laden über Base bleibt wie bisher (dynamische Klasse)."""
    restored = Base.from_dict(Blob(name="b").to_dict())
    assert type(restored).__name__ == "Blob"
    assert type(restored) is not Blob
    assert isinstance(restored, Base)
