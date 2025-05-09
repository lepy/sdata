import os
import sqlite3
import json
import zlib
import base64
import shutil
import pytest
from datetime import datetime, timedelta
from sdata.iolib.jsonsqlitestore import JSONSQLiteStore


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_store.sqlite")


@pytest.fixture
def store(db_path):
    # create fresh store for each test
    yield JSONSQLiteStore(db_path)
    try:
        os.remove(db_path)
    except OSError:
        pass


def test_insert_and_get(store):
    rid = store.insert({"user": "alice", "score": 42})
    data = store.get(rid)
    assert data == {"user": "alice", "score": 42}


def test_update_and_get(store):
    rid = store.insert({"user": "bob", "score": 10})
    store.update(rid, {"user": "bob", "score": 99})
    data = store.get(rid)
    assert data["score"] == 99


def test_delete_and_exists(store):
    rid = store.insert({"user": "carol"})
    assert store.exists(rid)
    store.delete(rid)
    assert not store.exists(rid)


def test_insert_many_and_count(store):
    objs = [{"x": i} for i in range(5)]
    ids = store.insert_many(objs)
    assert len(ids) == 5
    assert store.count() == 5


def test_find_by_and_wildcard(store):
    store.insert({"name": "alpha"})
    store.insert({"name": "beta"})
    store.insert({"name": "alphabet"})
    results = store.find_by("name", "LIKE", "a*")
    names = {r["name"] for r in results}
    assert names == {"alpha", "alphabet"}


def test_fetch_page(store):
    for i in range(10):
        store.insert({"i": i})
    # Fetching records where "i" >= 2, expecting the first record to be 2
    page1 = store.fetch_page(3, 0, key="i", op=">=", value=2)
    assert len(page1) == 3
    assert page1[0]["i"] == 2  # Change this to 2 instead of 9


def test_transaction_commit(store):
    with store.transaction():
        r1 = store.insert({"a": 1})
        r2 = store.insert({"b": 2})
    assert store.exists(r1) and store.exists(r2)


def test_transaction_rollback(store):
    try:
        with store.transaction():
            store.insert({"a": 1})
            raise RuntimeError("force rollback")
    except RuntimeError:
        pass
    assert store.count() == 0


def test_compression_and_type_parsing(tmp_path):
    db = str(tmp_path / "comp.sqlite")
    # parser for value to int
    store = JSONSQLiteStore(db, compression=True, type_parsers={"n": int})
    rid = store.insert({"n": 123})  # Insert as an integer
    data = store.get(rid)
    assert isinstance(data["n"], int)
    assert data["n"] == 123


def test_version_and_migration(store):
    assert store.get_version() == 0
    store.set_version(5)
    assert store.get_version() == 5
    # simple migration: add dummy table
    store.migrate("CREATE TABLE IF NOT EXISTS mtest(x);")
    cur = store.execute_raw("SELECT name FROM sqlite_master WHERE type='table' AND name='mtest';")
    assert cur.fetchone()[0] == 'mtest'


def test_backup_and_restore(tmp_path):
    src = str(tmp_path / "src.sqlite")
    dest = str(tmp_path / "dest.sqlite")
    store1 = JSONSQLiteStore(src)
    rid = store1.insert({"v": 7})
    store1.backup(dest)
    # modify original
    store1.insert({"v": 8})
    store1.get(rid)  # keep open
    store1.restore(dest)
    # after restore only one record
    store2 = store1
    assert store2.count() == 1
    data = store2.fetch_all()[0]
    assert data["v"] == 7


def test_delete_expired(tmp_path):
    db = str(tmp_path / "exp.sqlite")
    store = JSONSQLiteStore(db)
    now = datetime.utcnow()
    rid1 = store.insert({"t": 1})
    # artificially update created_at to past
    past = (now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%fZ')
    store.execute_raw("UPDATE data SET created_at = ? WHERE id = ?", (past, rid1))
    deleted = store.delete_expired(now.strftime('%Y-%m-%dT%H:%M:%fZ'))
    assert deleted == 1


def test_hooks(store):
    calls = {}

    def on_insert(rid, obj):
        calls['insert'] = (rid, obj)

    def on_update(rid, obj):
        calls['update'] = (rid, obj)

    def on_delete(rid):
        calls['delete'] = rid

    store.hooks = {"on_insert": on_insert, "on_update": on_update, "on_delete": on_delete}
    rid = store.insert({"h": 1})
    assert calls['insert'][0] == rid
    store.update(rid, {"h": 2})
    assert calls['update'][0] == rid
    store.delete(rid)
    assert calls['delete'] == rid
