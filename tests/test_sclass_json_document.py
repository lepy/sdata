# -*- coding: utf-8 -*-
"""Tests für JsonDocument (RFC 0018)."""
import io
import json
import zipfile

import pytest

from sdata.sclass.json_document import JsonDocument


def test_roundtrip_dict():
    d = JsonDocument({"b": [1, 2.5, None, True], "a": "ä"}, json_format="x/1", name="Mein Dok")
    back = JsonDocument.from_dict(d.to_dict())
    assert back.sname == d.sname
    assert back.description == d.description
    assert isinstance(back, JsonDocument)
    assert back.content == {"b": [1, 2.5, None, True], "a": "ä"}
    assert back.json_format == "x/1"


def test_roundtrip_zip():
    d = JsonDocument({"k": [1, {"z": "ö"}]}, name="zipdoc")
    first = d.to_zip(deterministic=True).getvalue()
    second = d.to_zip(deterministic=True).getvalue()
    assert first == second
    with zipfile.ZipFile(io.BytesIO(first)) as zf:
        names = zf.namelist()
        assert len(names) == 1
        raw = json.loads(zf.read(names[0]))
    back = JsonDocument.from_dict(raw)
    assert back.content == {"k": [1, {"z": "ö"}]}


def test_content_bytes_canonical():
    expected = b'{"a":2,"b":1}'
    assert JsonDocument({"b": 1, "a": 2}).content_bytes == expected
    assert JsonDocument({"a": 2, "b": 1}).content_bytes == expected
    assert JsonDocument({"u": "äö"}).content_bytes == '{"u":"äö"}'.encode("utf-8")


BAD = [
    float("nan"), float("inf"), float("-inf"),
    {1: "x"}, {"a": {2: "x"}}, [{"a": [{3: 1}]}],
    object(), b"bytes", {"s": {1, 2}}, (1, 2),
]


@pytest.mark.parametrize("bad", BAD, ids=repr)
def test_rejects_nan_and_non_json(bad):
    with pytest.raises(ValueError):
        JsonDocument(bad)
    doc = JsonDocument({})
    with pytest.raises(ValueError):
        doc.content = bad
    assert doc.content == {}


def test_verify():
    d = JsonDocument({"a": 1})
    assert d.verify() is False  # noch keine Prüfsumme
    d.update_checksum()
    assert d.verify()
    d.content = {"a": 2}
    assert not d.verify()
    assert d.sha256 and d.size == len(b'{"a":2}')


def test_sname_class_part():
    assert JsonDocument({}, name="x").sname.startswith("JsonDocument__")


def test_content_is_inline():
    content = {"a": [1, 2], "b": {"c": "d"}}
    assert JsonDocument(content).to_dict()["data"]["content"] == content


def test_json_format_set_and_clear():
    d = JsonDocument(1)
    assert d.json_format is None
    d.json_format = None  # nichts zu entfernen
    d.json_format = "a/1"
    assert d.json_format == "a/1"
    d.json_format = None
    assert d.json_format is None


def test_default_content_none_and_repr():
    d = JsonDocument(name="leer")
    assert d.content is None
    assert d.content_bytes == b"null"
    assert "JsonDocument" in repr(d)
    d.data = {}
    assert d.content is None


def test_from_dict_rejects_non_json_content():
    raw = JsonDocument({"a": 1}).to_dict()
    raw["data"]["content"] = {"a": float("nan")}
    with pytest.raises(ValueError):
        JsonDocument.from_dict(raw)
