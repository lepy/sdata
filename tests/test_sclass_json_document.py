# -*- coding: utf-8 -*-
"""Tests für JsonDocument (RFC 0018)."""
import io
import time
import json
import zipfile

import pytest

from sdata.base import Base
from sdata.sclass.blob import Blob
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


class _SubDoc(JsonDocument):
    pass


def test_from_dict_rejects_foreign_class():
    with pytest.raises(ValueError):
        JsonDocument.from_dict(Base(name="x").to_dict())
    with pytest.raises(ValueError):
        JsonDocument.from_dict(Blob(name="b").to_dict())
    d = Base(name="x").to_dict()
    d["metadata"] = {k: v for k, v in d["metadata"].items() if k != "_sdata_class"}
    with pytest.raises(ValueError):
        JsonDocument.from_dict(d)


def test_from_dict_accepts_subclass():
    sub = _SubDoc({"a": 1}, name="s")
    assert isinstance(_SubDoc.from_dict(sub.to_dict()), _SubDoc)
    assert JsonDocument.from_dict(JsonDocument({"a": 1}).to_dict()).content == {"a": 1}


def _nest(n):
    value = []
    for _ in range(n):
        value = [value]
    return value


def test_deep_nesting_no_recursion_error():
    # Tiefe 5000, die json.loads noch liest: Prüfung und Hash laufen durch
    loaded = json.loads("[" * 5000 + "]" * 5000)
    doc = JsonDocument(loaded)
    doc.content = loaded
    assert doc.content_bytes == b"[" * 5000 + b"]" * 5000
    raw = doc.to_dict()
    assert JsonDocument.from_dict(raw).content == loaded


def test_too_deep_for_json_dumps_is_value_error():
    deep = _nest(100000)                # Prüfung iterativ, json.dumps scheitert
    doc = JsonDocument(deep)
    with pytest.raises(ValueError):
        doc.content_bytes
    assert doc.sha256 is None           # Mixin fängt den Fehler


def test_from_dict_rejects_non_json_object():
    raw = JsonDocument({}).to_dict()
    raw["data"]["content"] = {"a": object()}
    with pytest.raises(ValueError):
        JsonDocument.from_dict(raw)


def test_content_bytes_rechecks_after_mutation():
    content = {"a": 1}
    doc = JsonDocument(content)
    content["b"] = {1, 2}
    with pytest.raises(ValueError):
        doc.content_bytes


def test_roundtrip_custom_metadata_and_checksum():
    d = JsonDocument({"b": [1, 2], "a": "ä"}, json_format="scale-board/1", name="rep")
    d.metadata.set_attr("report_id", "R-42", dtype="str", unit="-",
                        label="Report-ID", description="Kennung des Reports")
    d.update_checksum()
    before = d.metadata.to_dict()
    back = JsonDocument.from_dict(d.to_dict())
    assert back.metadata.to_dict() == before
    attr = back.metadata.get("report_id")
    assert (attr.value, attr.label, attr.description) == (
        "R-42", "Report-ID", "Kennung des Reports")
    with zipfile.ZipFile(d.to_zip(deterministic=True)) as zf:
        raw = json.loads(zf.read(zf.namelist()[0]))
    zback = JsonDocument.from_dict(raw)
    assert zback.metadata.to_dict() == before
    assert zback.json_format == "scale-board/1"
    assert zback.content == d.content
    assert zback.verify()
    assert back.verify()


def test_list_root():
    d = JsonDocument([1, {"a": None}, "x"], name="liste")
    d.update_checksum()
    back = JsonDocument.from_dict(d.to_dict())
    assert back.content == [1, {"a": None}, "x"]
    assert back.verify()


def test_cycles_rejected():
    d = {}
    d["x"] = d
    li = [1]
    li.append(li)
    nested = {"a": [{"b": []}]}
    nested["a"][0]["b"].append(nested)
    for cyc in (d, li, nested):
        with pytest.raises(ValueError, match="zyklisch"):
            JsonDocument(cyc)
    doc = JsonDocument({})
    with pytest.raises(ValueError, match="zyklisch"):
        doc.content = d
    ok = JsonDocument({"a": 1})
    ok.content["self"] = ok.content     # Mutation nach dem Setzen
    with pytest.raises(ValueError, match="zyklisch"):
        ok.content_bytes


def test_shared_subobject_allowed():
    shared = [1]
    doc = JsonDocument({"a": shared, "b": shared})
    assert doc.content_bytes == b'{"a":[1],"b":[1]}'


def test_deep_check_is_fast():
    deep = _nest(100000)
    start = time.perf_counter()
    JsonDocument(deep)
    assert time.perf_counter() - start < 5


def test_error_message_short_and_path_truncated():
    value = float("nan")
    for _ in range(5000):
        value = {"k" * 100: value}
    with pytest.raises(ValueError) as exc:
        JsonDocument(value)
    msg = str(exc.value)
    assert len(msg) < 1000
    assert "…" in msg and "NaN" in msg


def test_error_message_list_index_and_long_key():
    with pytest.raises(ValueError, match=r"\$\.a\[1\]"):
        JsonDocument({"a": [0, object()]})
    with pytest.raises(ValueError) as exc:
        JsonDocument({"a": {10 ** 60: 1}})
    assert len(str(exc.value)) < 200
