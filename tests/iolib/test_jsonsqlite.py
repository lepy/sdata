import pytest
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Any
import os
import tempfile
import shutil
import pandas as pd

from sdata.iolib.json1sqlitestore import JSON1SQLiteStore

@pytest.fixture
def store():
    """Fixture for an in-memory store."""
    s = JSON1SQLiteStore(':memory:', index_keys=['age'], unique_index_keys=['email'])
    yield s
    s.conn.close()

@pytest.fixture
def file_store():
    """Fixture for a file-based store using temp file."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    s = JSON1SQLiteStore(db_path)
    yield s, db_path, temp_dir
    s.conn.close()
    shutil.rmtree(temp_dir)

def test_init(store):
    # Check table exists
    cur = store.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data'")
    assert cur.fetchone() is not None
    # Check generated columns
    cur = store.conn.execute("PRAGMA table_xinfo('data')")
    columns = [row['name'] for row in cur]

    query = "SELECT * FROM data"
    df = pd.read_sql_query(query, store.conn)
    print(df)

    assert 'sdata_class' in columns
    assert 'sdata_name' in columns
    assert 'sdata_suuid' in columns
    assert 'sdata_sname' in columns
    # Check auto indices
    indices = store.list_indices()
    index_names = [name for name, _ in indices]
    assert 'idx__sdata_class' in index_names
    assert 'idx__sdata_name' in index_names
    assert 'idx__sdata_suuid' in index_names  # unique
    assert 'idx__sdata_sname' in index_names  # unique
    # Custom indices from fixture
    assert 'idx_age' in index_names
    assert 'idx_email' in index_names

def test_insert_and_get(store):
    obj = {
        '!sdata_class': 'user',
        '!sdata_name': 'alice',
        '!sdata_suuid': 'suuid1',
        '!sdata_sname': 'sname1',
        'age': 30,
        'email': 'alice@example.com'
    }
    rid = store.insert(obj)
    assert rid > 0
    fetched = store.get(rid)
    assert fetched == obj

def test_insert_many(store):
    objs = [
        {'!sdata_class': 'user', '!sdata_name': 'bob', '!sdata_suuid': 'suuid2', '!sdata_sname': 'sname2', 'age': 25},
        {'!sdata_class': 'user', '!sdata_name': 'charlie', '!sdata_suuid': 'suuid3', '!sdata_sname': 'sname3', 'age': 35}
    ]
    rids = store.insert_many(objs)
    assert len(rids) == 2
    assert store.get(rids[0]) == objs[0]
    assert store.get(rids[1]) == objs[1]

def test_update(store):
    obj = {'!sdata_class': 'user', '!sdata_name': 'dave', '!sdata_suuid': 'suuid4', '!sdata_sname': 'sname4', 'age': 40}
    rid = store.insert(obj)
    new_obj = {**obj, 'age': 41}
    store.update(rid, new_obj)
    fetched = store.get(rid)
    assert fetched['age'] == 41

def test_update_by_suuid(store):
    obj = {'!sdata_class': 'user', '!sdata_name': 'eve', '!sdata_suuid': 'suuid5', '!sdata_sname': 'sname5', 'age': 28}
    store.insert(obj)
    new_obj = {**obj, 'age': 29}
    store.update('suuid5', new_obj)
    fetched = store.get(store.get_id_by_key('!sdata_suuid', 'suuid5'))
    assert fetched['age'] == 29

def test_update_many(store):
    obj1 = {'!sdata_class': 'user', '!sdata_name': 'frank', '!sdata_suuid': 'suuid6', '!sdata_sname': 'sname6', 'age': 50}
    obj2 = {'!sdata_class': 'user', '!sdata_name': 'grace', '!sdata_suuid': 'suuid7', '!sdata_sname': 'sname7', 'age': 45}
    rid1 = store.insert(obj1)
    rid2 = store.insert(obj2)
    new_obj1 = {**obj1, 'age': 51}
    new_obj2 = {**obj2, 'age': 46}
    store.update_many([(rid1, new_obj1), (rid2, new_obj2)])
    assert store.get(rid1)['age'] == 51
    assert store.get(rid2)['age'] == 46

def test_delete(store):
    obj = {'!sdata_class': 'user', '!sdata_name': 'hank', '!sdata_suuid': 'suuid8', '!sdata_sname': 'sname8'}
    rid = store.insert(obj)
    store.delete(rid)
    assert store.get(rid) is None

def test_exists(store):
    obj = {'!sdata_class': 'user', '!sdata_name': 'ivy', '!sdata_suuid': 'suuid9', '!sdata_sname': 'sname9'}
    rid = store.insert(obj)
    assert store.exists(rid)
    assert not store.exists(9999)

def test_exists_where(store):
    obj = {'!sdata_class': 'user', '!sdata_name': 'jack', '!sdata_suuid': 'suuid10', '!sdata_sname': 'sname10'}
    store.insert(obj)
    assert store.exists_where('!sdata_name', 'jack')
    assert not store.exists_where('!sdata_name', 'nonexistent')

def test_count(store):
    store.insert({'!sdata_class': 'user', '!sdata_name': 'kate', '!sdata_suuid': 'suuid11', '!sdata_sname': 'sname11'})
    store.insert({'!sdata_class': 'user', '!sdata_name': 'leo', '!sdata_suuid': 'suuid12', '!sdata_sname': 'sname12'})
    assert store.count() == 2

def test_count_where(store):
    store.insert({'!sdata_class': 'admin', '!sdata_name': 'mike', '!sdata_suuid': 'suuid13', '!sdata_sname': 'sname13', 'level': 1})
    store.insert({'!sdata_class': 'admin', '!sdata_name': 'nina', '!sdata_suuid': 'suuid14', '!sdata_sname': 'sname14', 'level': 2})
    assert store.count_where('!sdata_class', '=', 'admin') == 2
    assert store.count_where('level', '>', 1) == 1

def test_fetch_page(store):
    for i in range(10):
        store.insert({'!sdata_class': 'item', '!sdata_name': f'item{i}', '!sdata_suuid': f'suuid{i+15}', '!sdata_sname': f'sname{i+15}', 'value': i})
    page = store.fetch_page(5, 0, sort_by='id ASC')
    assert len(page) == 5
    assert page[0]['value'] == 0
    page2 = store.fetch_page(5, 5)
    assert page2[0]['value'] == 5

def test_fetch_page_with_where(store):
    store.insert({'!sdata_class': 'even', '!sdata_name': 'even1', '!sdata_suuid': 'suuid20', '!sdata_sname': 'sname20', 'num': 2})
    store.insert({'!sdata_class': 'odd', '!sdata_name': 'odd1', '!sdata_suuid': 'suuid21', '!sdata_sname': 'sname21', 'num': 3})
    store.insert({'!sdata_class': 'even', '!sdata_name': 'even2', '!sdata_suuid': 'suuid22', '!sdata_sname': 'sname22', 'num': 4})
    evens = store.fetch_page(10, 0, key='!sdata_class', op='=', value='even')
    assert len(evens) == 2
    assert all(o['!sdata_class'] == 'even' for o in evens)

def test_find_by(store):
    store.insert({'!sdata_class': 'user', '!sdata_name': 'oliver', '!sdata_suuid': 'suuid23', '!sdata_sname': 'sname23', 'age': 20})
    store.insert({'!sdata_class': 'user', '!sdata_name': 'paula', '!sdata_suuid': 'suuid24', '!sdata_sname': 'sname24', 'age': 25})
    users = store.find_by('!sdata_class', 'user')
    assert len(users) == 2
    like = store.find_by('!sdata_name', 'p*', op='LIKE')
    assert len(like) == 1
    assert like[0]['!sdata_name'] == 'paula'

def test_extract(store):
    obj = {'!sdata_class': 'user', '!sdata_name': 'quinn', '!sdata_suuid': 'suuid25', '!sdata_sname': 'sname25', 'nested': {'key': 'value'}}
    rid = store.insert(obj)
    assert store.extract(rid, '$.!sdata_name') == 'quinn'
    assert store.extract(rid, '$.nested.key') == 'value'

def test_set_path(store):
    obj = {'!sdata_class': 'user', '!sdata_name': 'rachel', '!sdata_suuid': 'suuid26', '!sdata_sname': 'sname26', 'data': {}}
    rid = store.insert(obj)
    store.set_path(rid, '$.data.new', 'test')
    fetched = store.get(rid)
    assert fetched['data']['new'] == 'test'

def test_insert_path(store):
    obj = {'!sdata_class': 'user', '!sdata_name': 'sam', '!sdata_suuid': 'suuid27', '!sdata_sname': 'sname27', 'list': [1, 2]}
    rid = store.insert(obj)
    store.insert_path(rid, '$.list[2]', 3)  # Inserts at index 2
    fetched = store.get(rid)
    assert fetched['list'] == [1, 2, 3]

def test_replace_path(store):
    obj = {'!sdata_class': 'user', '!sdata_name': 'tina', '!sdata_suuid': 'suuid28', '!sdata_sname': 'sname28', 'key': 'old'}
    rid = store.insert(obj)
    store.replace_path(rid, '$.key', 'new')
    fetched = store.get(rid)
    assert fetched['key'] == 'new'

def test_remove_path(store):
    obj = {'!sdata_class': 'user', '!sdata_name': 'uma', '!sdata_suuid': 'suuid29', '!sdata_sname': 'sname29', 'remove_me': True, 'keep': True}
    rid = store.insert(obj)
    store.remove_path(rid, '$.remove_me')
    fetched = store.get(rid)
    assert 'remove_me' not in fetched
    assert 'keep' in fetched

def test_array_length(store):
    obj = {'!sdata_class': 'user', '!sdata_name': 'victor', '!sdata_suuid': 'suuid30', '!sdata_sname': 'sname30', 'arr': [1, 2, 3]}
    rid = store.insert(obj)
    assert store.array_length(rid, '$.arr') == 3

def test_each(store):
    obj = {'!sdata_class': 'user', '!sdata_name': 'wendy', '!sdata_suuid': 'suuid31', '!sdata_sname': 'sname31', 'dict': {'a': 1, 'b': 2}}
    rid = store.insert(obj)
    each = store.each(rid, '$.dict')
    assert sorted(each, key=lambda x: x['key']) == [{'key': 'a', 'value': 1}, {'key': 'b', 'value': 2}]

def test_tree(store):
    obj = {'!sdata_class': 'user', '!sdata_name': 'xavier', '!sdata_suuid': 'suuid32', '!sdata_sname': 'sname32', 'nested': {'child': 'value'}}
    rid = store.insert(obj)
    tree = store.tree(rid)
    paths = [t['path'] for t in tree]
    assert '$' in paths
    assert '$.nested' in paths
    assert '$.nested.child' in paths

def test_create_index(store):
    store.create_index('custom_key')
    indices = store.list_indices()
    assert any('idx_custom_key' in name for name, _ in indices)

def test_unique_index(store):
    store.create_index('unique_test', unique=True)
    obj1 = {'!sdata_class': 'user', '!sdata_name': 'yara', '!sdata_suuid': 'suuid33', '!sdata_sname': 'sname33', 'unique_test': 'same'}
    store.insert(obj1)
    obj2 = {'!sdata_class': 'user', '!sdata_name': 'zach', '!sdata_suuid': 'suuid34', '!sdata_sname': 'sname34', 'unique_test': 'same'}
    with pytest.raises(sqlite3.IntegrityError):
        store.insert(obj2)

def test_get_id_by_key(store):
    obj = {'!sdata_class': 'user', '!sdata_name': 'alice', '!sdata_suuid': 'suuid35', '!sdata_sname': 'sname35'}
    rid = store.insert(obj)
    assert store.get_id_by_key('!sdata_name', 'alice') == rid
    assert store.get_id_by_key('!sdata_suuid', 'suuid35') == rid

def test_transaction(store):
    with store.transaction():
        rid = store.insert({'!sdata_class': 'user', '!sdata_name': 'trans', '!sdata_suuid': 'suuid36', '!sdata_sname': 'sname36'})
        assert store.exists(rid)
    assert store.exists(rid)  # Committed

    try:
        with store.transaction():
            rid2 = store.insert({'!sdata_class': 'user', '!sdata_name': 'fail', '!sdata_suuid': 'suuid37', '!sdata_sname': 'sname37'})
            raise Exception("Rollback")
    except Exception:
        pass
    assert not store.exists(rid2)  # Rolled back

def test_delete_expired(store):
    # Insert with old created_at by manual insert
    old_ts = (datetime.utcnow() - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%fZ')
    store.conn.execute("INSERT INTO data (payload, created_at) VALUES (json(?), ?)", (json.dumps({'!sdata_class': 'expire', '!sdata_name': 'old', '!sdata_suuid': 'suuid38', '!sdata_sname': 'sname38'}), old_ts))
    recent_rid = store.insert({'!sdata_class': 'keep', '!sdata_name': 'new', '!sdata_suuid': 'suuid39', '!sdata_sname': 'sname39'})
    deleted = store.delete_expired(datetime.utcnow() - timedelta(days=1))
    assert deleted == 1
    assert store.exists(recent_rid)

def test_hooks(store):
    calls = []
    def on_insert(rid, obj):
        calls.append(('insert', rid, obj))
    store.hooks['on_insert'] = on_insert
    obj = {'!sdata_class': 'user', '!sdata_name': 'hook', '!sdata_suuid': 'suuid40', '!sdata_sname': 'sname40'}
    rid = store.insert(obj)
    assert calls == [('insert', rid, obj)]

def test_type_parsers(store):
    def parse_age(val):
        return int(val) + 1  # Dummy parser
    store.type_parsers['age'] = parse_age
    obj = {'!sdata_class': 'user', '!sdata_name': 'parse', '!sdata_suuid': 'suuid41', '!sdata_sname': 'sname41', 'age': '30'}
    rid = store.insert(obj)
    fetched = store.get(rid)
    assert fetched['age'] == 31

def test_backup_and_restore(file_store):
    s, db_path, temp_dir = file_store
    obj = {'!sdata_class': 'user', '!sdata_name': 'backup', '!sdata_suuid': 'suuid42', '!sdata_sname': 'sname42'}
    rid = s.insert(obj)
    backup_path = os.path.join(temp_dir, 'backup.db')
    s.backup(backup_path)
    # Modify original
    s.delete(rid)
    assert s.get(rid) is None
    # Restore
    s.restore(backup_path)
    assert s.get(rid) is not None

def test_migrate(store):
    # Add a new generated column as migration
    migration_sql = """
    ALTER TABLE data ADD COLUMN new_gen TEXT GENERATED ALWAYS AS (json_extract(payload, '$.new_field')) VIRTUAL;
    """
    store.migrate(migration_sql)
    # Check if column added
    cur = store.conn.execute("PRAGMA table_xinfo('data')")
    columns = [row['name'] for row in cur]
    print(columns)
    assert 'new_gen' in columns

def test_execute_raw(store):
    cur = store.execute_raw("SELECT 1 + 1")
    assert cur.fetchone()[0] == 2