# -*- coding: utf-8 -*-
"""Ergänzende Abdeckung von sdata/iolib/jsonsqlitestore.py (ungetestete Methoden)."""
from datetime import datetime

import pytest

from sdata.iolib.jsonsqlitestore import JSONSQLiteStore


@pytest.fixture
def store(tmp_path):
    return JSONSQLiteStore(str(tmp_path / "s.sqlite"))


def test_indices(store):
    store.insert({"user": "a"})
    store.create_index("user")
    assert "idx_json_user" in [n for n, _ in store.list_indices()]
    store.regenerate_index("user")


def test_serialize_error_and_get_missing(store):
    with pytest.raises(ValueError):
        store.insert({"bad": object()})        # nicht JSON-serialisierbar
    assert store.get(999999) is None


def test_update_delete(store):
    rid = store.insert({"x": 1})
    store.update(rid, {"x": 2})
    assert store.get(rid)["x"] == 2
    store.delete(rid)
    assert store.get(rid) is None


def test_count_where_and_fetch_page(store):
    for i in range(5):
        store.insert({"k": f"v{i}", "n": i})
    assert store.count() == 5
    assert store.count_where("n", ">", 2) == 2
    assert store.count_where("k", "=", "v*") == 5      # Wildcard -> LIKE
    assert len(store.fetch_page(2, 0)) == 2
    assert len(store.fetch_page(10, 0, key="k", op="=", value="v*")) == 5


def test_versions_and_migrate(store):
    assert store.get_version() == 0
    store.set_version(3)
    assert store.get_version() == 3
    store.migrate("CREATE TABLE IF NOT EXISTS t (id INTEGER)")


def test_backup_restore_execute_raw(store, tmp_path):
    store.insert({"a": 1})
    dest = str(tmp_path / "backup.sqlite")
    store.backup(dest)
    store.restore(dest)
    assert store.execute_raw("SELECT COUNT(*) FROM data").fetchone()[0] == 1
    assert store.execute_raw("SELECT * FROM data WHERE id = ?", (1,)).fetchone() is not None


def test_transaction_commit_and_rollback(store):
    with store.transaction():
        store.insert({"t": 1})
    assert store.count() == 1
    with pytest.raises(RuntimeError):
        with store.transaction():
            store.insert({"t": 2})
            raise RuntimeError("boom")
    assert store.count() == 1                  # rollback


def test_delete_expired(store):
    store.insert({"a": 1})
    assert store.delete_expired("2000-01-01T00:00:00Z") == 0
    assert store.delete_expired(datetime(2999, 1, 1)) == 1


def test_get_dict_and_exists_where(store):
    store.insert({"user": "alice"})
    assert len(store.get_dict("user", "alice")) == 1
    assert store.exists_where("user", "alice") is True
    assert store.exists_where("user", "bob") is False


def test_hooks_insert_update_many(tmp_path):
    seen = []
    hooks = {
        "on_insert_many": lambda objs: seen.append(("im", len(objs))),
        "on_update_many": lambda pairs: seen.append(("um", len(pairs))),
    }
    s = JSONSQLiteStore(str(tmp_path / "h.sqlite"), hooks=hooks)
    ids = s.insert_many([{"a": 1}, {"a": 2}])
    s.update_many([(ids[0], {"a": 9})])
    assert ("im", 2) in seen and ("um", 1) in seen


def test_context_and_iter(tmp_path):
    path = str(tmp_path / "ctx.sqlite")
    with JSONSQLiteStore(path) as s:
        s.insert({"c": 1})
        assert list(iter(s)) == [{"c": 1}]
