# -*- coding: utf-8 -*-
"""Ergänzende Abdeckung von sdata/iolib/json1sqlitestore.py (JSON-Path + Admin)."""
from datetime import datetime

import pytest

from sdata.iolib.json1sqlitestore import JSON1SQLiteStore


def _rec(**kw):
    base = {"_sdata_class": "C", "_sdata_name": "n",
            "_sdata_suuid": "s", "_sdata_sname": "sn"}
    base.update(kw)
    return base


@pytest.fixture
def store():
    s = JSON1SQLiteStore(":memory:")
    yield s
    s.conn.close()


def test_json_path_methods(store):
    rid = store.insert(_rec(arr=[1, 2, 3], nested={"a": 1}))
    assert store.extract(rid, "$.nested.a") == 1
    store.set_path(rid, "$.nested.a", 5)
    assert store.extract(rid, "$.nested.a") == 5
    store.insert_path(rid, "$.nested.b", 9)
    store.replace_path(rid, "$.nested.a", 7)
    store.remove_path(rid, "$.nested.b")
    assert store.array_length(rid, "$.arr") == 3
    assert isinstance(store.each(rid, "$.arr"), list)
    assert isinstance(store.tree(rid), list)


def test_find_by_variants(store):
    store.insert(_rec(_sdata_name="alice", _sdata_suuid="s1", _sdata_sname="sn1"))
    store.insert(_rec(_sdata_name="bob", _sdata_suuid="s2", _sdata_sname="sn2"))
    assert len(store.find_by("_sdata_name", "alice")) == 1
    assert len(store.find_by("_sdata_name", "al*", op="LIKE")) == 1
    assert len(store.find_by("_sdata_class", "C", limit=1, offset=0)) == 1
    # nicht-generierte Spalte -> Warnung + json_extract-Pfad
    store.insert(_rec(custom="abc"))
    with pytest.warns(UserWarning, match="not optimized"):
        assert len(store.find_by("custom", "abc")) == 1


def test_get_index_df(store):
    store.insert(_rec(_sdata_project_sname="P", _sdata_parent_sname="PA"))
    assert store.get_index_df() is not None
    assert store.get_index_df(class_name="C", project="P", parent="PA") is not None


def test_id_by_key_and_indices(store):
    rid = store.insert(_rec(_sdata_suuid="uniq"))
    assert store.get_id_by_key("_sdata_suuid", "uniq") == rid
    assert store.get_id_by_key("some_json_only_key", "x") is None   # column=None-Pfad
    assert isinstance(store.get_indices_columns(), list)
    store.regenerate_index("_sdata_name")


def test_admin_methods(store):
    rid = store.insert(_rec(_sdata_suuid="a"))
    assert store.exists(rid) is True
    assert store.exists_where("_sdata_name", "n") is True
    assert store.count() >= 1
    assert store.count_where("_sdata_name", "=", "n") == 1
    assert isinstance(store.fetch_page(10, 0), list)
    store.version = 2
    assert store.version == 2
    store.migrate("CREATE TABLE IF NOT EXISTS t (id INTEGER)")
    assert store.execute_raw("SELECT 1").fetchone() is not None
    with store.transaction():
        store.insert(_rec(_sdata_suuid="b", _sdata_sname="sn2"))
    store.update(rid, _rec(_sdata_name="upd", _sdata_suuid="a"))
    store.delete(rid)
    assert store.delete_expired(datetime(2999, 1, 1)) >= 1


def test_backup_restore_and_context(tmp_path):
    path = str(tmp_path / "j.sqlite")
    with JSON1SQLiteStore(path) as s:
        s.insert(_rec(_sdata_suuid="x"))
        dest = str(tmp_path / "bak.sqlite")
        s.backup(dest)
        s.restore(dest)
        assert s.count() == 1


def test_path_helpers(store):
    obj = {"a": {"b": [10, 20]}}
    assert store._get_by_path(obj, "$.a.b[1]") == 20
    assert store._get_by_path(obj, "a.b[0]") == 10           # ohne '$'
    with pytest.raises(KeyError):
        store._get_by_path(obj, "$.x.y")

    o = {}
    store._set_by_path(o, "$.a.b", 1)                        # nested dict
    assert o["a"]["b"] == 1
    store._set_by_path(o, "$.arr[2]", 7)                     # Liste erstellen+füllen
    assert o["arr"][2] == 7
    store._set_by_path(o, "$.deep[0].x", 5)                  # Liste->dict
    assert o["deep"][0]["x"] == 5
    store._set_by_path(o, "$.a.b", 9, mode="replace")        # replace vorhanden
    store._set_by_path(o, "$.zzz", 1, mode="replace")        # replace fehlend -> noop
    assert "zzz" not in o
    store._set_by_path(o, "$.ins", 1, mode="insert")         # insert neu
    store._set_by_path(o, "$.ins", 2, mode="insert")         # insert vorhanden -> noop
    assert o["ins"] == 1
    store._set_by_path(o, "$.arr[0]", 1, mode="insert")      # list insert vorhanden -> noop
    store._set_by_path(o, "$.arr[5]", 9, mode="insert")      # list insert neu
    store._set_by_path(o, "$.lst[0]", 1, mode="replace")     # replace fehlende Liste -> noop
    with pytest.raises(ValueError):
        store._set_by_path({"a": 1}, "$.a[0].b", 5)          # Zwischenteil-Typ-Mismatch

    store._remove_by_path(o, "$.a.b")
    assert store._compare(5, ">", 3) is True
    with pytest.raises(ValueError):
        store._compare(1, "BAD", 2)
    assert isinstance(store._each_python({"a": {"x": 1}}, "$.a"), list)
    assert isinstance(store._each_python({"a": [1, 2]}, "$.a"), list)
    assert store._each_python({"a": 1}, "$.a") == []
    assert isinstance(list(store._tree_python({"a": {"b": 1}})), list)


def test_fetch_all_and_update_by_suuid(store):
    store.insert(_rec(_sdata_suuid="x"))
    assert isinstance(list(store.fetch_all()), list)
    store.update("x", _rec(_sdata_suuid="x", _sdata_name="upd"))   # str-Identifier gefunden
    with pytest.raises(ValueError):
        store.update("nonexistent", _rec())                       # nicht gefunden


def test_exists_where_and_wildcards(store):
    store.insert(_rec(custom2="yy", _sdata_name="alice"))
    assert store.exists_where("custom2", "yy") is True
    assert store.count_where("_sdata_name", "LIKE", "al*") >= 1
    assert isinstance(store.fetch_page(5, 0, key="_sdata_name", op="LIKE", value="al*"), list)


def test_delete_expired_hook():
    seen = []
    s = JSON1SQLiteStore(":memory:", hooks={"on_delete_expired": lambda n: seen.append(n)})
    s.insert(_rec(_sdata_suuid="x"))
    s.delete_expired(datetime(2999, 1, 1))
    assert len(seen) == 1
    s.conn.close()


def test_path_helper_edges(store):
    o = {}
    store._set_by_path(o, "noprefix", 1)                          # ohne '$'
    assert o["noprefix"] == 1
    store._set_by_path({"a": 1}, "$.a[0]", 9, mode="replace")     # replace + nicht-Liste
    store._set_by_path({}, "$.x", 1, mode="replace")              # replace fehlend
    store._set_by_path({"arr": [1]}, "$.arr[5]", 9, mode="replace")  # replace fehlender Index
    store._set_by_path({"a": 1}, "$.a[0]", 9)                     # -> Liste
    obj = {"arr": [1, 2, 3]}
    store._remove_by_path(obj, "$.arr[1]")                        # Listen-Index
    assert obj["arr"] == [1, 3]
    store._remove_by_path({}, "$.missing.x")                      # KeyError -> ignoriert
    assert isinstance(list(store._tree_python([1, 2])), list)     # Listen-Zweig


def test_hooks():
    seen = []
    hooks = {
        "on_insert": lambda rid, obj: seen.append("i"),
        "on_insert_many": lambda objs: seen.append(("im", len(objs))),
        "on_update": lambda rid, obj: seen.append("u"),
        "on_update_many": lambda pairs: seen.append(("um", len(pairs))),
        "on_delete": lambda rid: seen.append("d"),
    }
    s = JSON1SQLiteStore(":memory:", hooks=hooks)
    rid = s.insert(_rec(_sdata_suuid="i0"))
    s.insert_many([_rec(_sdata_suuid="i1", _sdata_sname="a"),
                   _rec(_sdata_suuid="i2", _sdata_sname="b")])
    s.update(rid, _rec(_sdata_suuid="i0", _sdata_name="x"))
    s.update_many([(rid, _rec(_sdata_suuid="i0", _sdata_name="y"))])
    s.delete(rid)
    assert "i" in seen and ("im", 2) in seen and "u" in seen and ("um", 1) in seen and "d" in seen
    s.conn.close()
