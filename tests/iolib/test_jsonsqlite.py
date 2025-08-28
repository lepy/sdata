import pytest
import sqlite3
from datetime import datetime, timezone
from sdata.iolib.json1sqlitestore import JSON1SQLiteStore  # Assuming the class is in a module named JSON1SQLiteStore.py


@pytest.fixture
def store(tmp_path):
    """Fixture to create a temporary in-memory store for testing."""
    # Use in-memory DB for faster tests
    store = JSON1SQLiteStore(':memory:')
    yield store
    store.conn.close()


def test_initialization(store):
    """Test store initialization and table creation."""
    cursor = store.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data'")
    assert cursor.fetchone() is not None, "Table 'data' should exist"

    # Check base columns
    cursor.execute("PRAGMA table_info(data)")
    columns = [row['name'] for row in cursor.fetchall()]
    assert 'id' in columns
    assert 'payload' in columns
    assert 'created_at' in columns

    # Check automatic indices (with correct name)
    indices = store.list_indices()
    index_names = [name for name, _ in indices]
    assert 'idx__sdata_class' in index_names
    assert 'idx__sdata_name' in index_names
    assert 'idx__sdata_suuid' in index_names
    assert 'idx__sdata_sname' in index_names


def test_generated_columns(store):
    """Test functionality of generated columns."""
    doc = {
        '!sdata_class': 'TestClass',
        '!sdata_name': 'TestName',
        '!sdata_suuid': 'test-suuid-123',
        '!sdata_sname': 'test-sname-123'
    }
    rid = store.insert(doc)

    cursor = store.conn.cursor()
    cursor.execute("SELECT sdata_class, sdata_name, sdata_suuid, sdata_sname FROM data WHERE id = ?", (rid,))
    row = cursor.fetchone()
    assert row['sdata_class'] == 'TestClass'
    assert row['sdata_name'] == 'TestName'
    assert row['sdata_suuid'] == 'test-suuid-123'
    assert row['sdata_sname'] == 'test-sname-123'


def test_insert_and_get(store):
    """Test inserting a document and retrieving it."""
    doc = {
        '!sdata_class': 'TestClass',
        '!sdata_name': 'TestName',
        '!sdata_suuid': 'test-suuid-123',
        '!sdata_sname': 'test-sname-123',
        'extra': 'data'
    }
    rid = store.insert(doc)
    assert rid > 0, "Insert should return a positive ID"

    retrieved = store.get(rid)
    assert retrieved == doc, "Retrieved document should match inserted"


def test_insert_many_and_fetch_all(store):
    """Test batch insert and fetching all documents."""
    docs = [
        {'!sdata_class': 'Class1', '!sdata_name': 'Name1', '!sdata_suuid': 'suuid1', '!sdata_sname': 'sname1'},
        {'!sdata_class': 'Class2', '!sdata_name': 'Name2', '!sdata_suuid': 'suuid2', '!sdata_sname': 'sname2'}
    ]
    ids = store.insert_many(docs)
    assert len(ids) == 2, "Should return two IDs"

    all_docs = list(store.fetch_all())
    assert len(all_docs) == 2, "Should fetch two documents"
    assert all_docs[0] == docs[0]
    assert all_docs[1] == docs[1]


def test_update_and_delete(store):
    """Test updating and deleting a document."""
    doc = {'!sdata_class': 'Class', '!sdata_name': 'Name', '!sdata_suuid': 'suuid', '!sdata_sname': 'sname'}
    rid = store.insert(doc)

    updated_doc = {'!sdata_class': 'UpdatedClass', '!sdata_name': 'UpdatedName', '!sdata_suuid': 'suuid',
                   '!sdata_sname': 'sname'}
    store.update(rid, updated_doc)
    retrieved = store.get(rid)
    assert retrieved == updated_doc, "Document should be updated"

    store.delete(rid)
    assert store.get(rid) is None, "Document should be deleted"


def test_find_by_optimized_fields(store):
    """Test find_by using generated columns for !sdata_* fields."""
    docs = [
        {'!sdata_class': 'ClassA', '!sdata_name': 'NameA', '!sdata_suuid': 'suuidA', '!sdata_sname': 'snameA'},
        {'!sdata_class': 'ClassB', '!sdata_name': 'NameB', '!sdata_suuid': 'suuidB', '!sdata_sname': 'snameB'},
        {'!sdata_class': 'ClassA', '!sdata_name': 'NameC', '!sdata_suuid': 'suuidC', '!sdata_sname': 'snameC'}
    ]
    store.insert_many(docs)

    results = store.find_by('!sdata_class', 'ClassA')
    assert len(results) == 2
    assert results[0]['!sdata_name'] == 'NameA'
    assert results[1]['!sdata_name'] == 'NameC'

    like_results = store.find_by('!sdata_name', 'Name*', op='LIKE')
    assert len(like_results) == 3  # All names start with 'Name'

    suuid_result = store.find_by('!sdata_suuid', 'suuidB')
    assert len(suuid_result) == 1
    assert suuid_result[0]['!sdata_class'] == 'ClassB'


def test_find_by_non_optimized_field(store):
    """Test find_by fallback for non-!sdata fields."""
    doc = {'!sdata_class': 'Class', '!sdata_name': 'Name', '!sdata_suuid': 'suuid', '!sdata_sname': 'sname',
           'custom': 'value'}
    store.insert(doc)

    with pytest.warns(UserWarning, match="not optimized"):
        results = store.find_by('custom', 'value')
    assert len(results) == 1
    assert results[0]['custom'] == 'value'


def test_extract_and_path_operations(store):
    """Test JSON path operations."""
    doc = {'!sdata_class': 'Class', '!sdata_name': 'Name', '!sdata_suuid': 'suuid', '!sdata_sname': 'sname',
           'array': [1, 2, 3], 'nested': {'key': 'value'}}
    rid = store.insert(doc)

    # Extract
    assert store.extract(rid, '$.array[1]') == 2
    assert store.extract(rid, '$.nested.key') == 'value'

    # Set path
    store.set_path(rid, '$.new_key', 'new_value')
    updated = store.get(rid)
    assert updated['new_key'] == 'new_value'

    # Insert path (only if not exists)
    store.insert_path(rid, '$.new_key', 'ignored')  # Should not change
    assert store.get(rid)['new_key'] == 'new_value'

    # Replace path (only if exists)
    store.replace_path(rid, '$.new_key', 'replaced')
    assert store.get(rid)['new_key'] == 'replaced'

    # Remove path
    store.remove_path(rid, '$.new_key')
    assert 'new_key' not in store.get(rid)

    # Array length
    assert store.array_length(rid, '$.array') == 3


def test_transaction(store):
    """Test transaction context manager."""
    with store.transaction():
        rid = store.insert(
            {'!sdata_class': 'Class', '!sdata_name': 'Name', '!sdata_suuid': 'suuid', '!sdata_sname': 'sname'})
        assert store.get(rid) is not None

    # Outside transaction, should still exist
    assert store.get(rid) is not None

    try:
        with store.transaction():
            store.insert(
                {'!sdata_class': 'Fail', '!sdata_name': 'Fail', '!sdata_suuid': 'fail', '!sdata_sname': 'fail'})
            raise ValueError("Rollback test")
    except ValueError:
        pass

    assert len(list(store.fetch_all())) == 1, "Failed insert should be rolled back"


def test_delete_expired(store):
    """Test deleting expired records."""
    old_ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%fZ')
    store.insert({'!sdata_class': 'Old', '!sdata_name': 'Old', '!sdata_suuid': 'old', '!sdata_sname': 'old'})

    # Manually set old created_at
    store.conn.execute("UPDATE data SET created_at = '2020-01-01T00:00:00.000Z' WHERE id = 1")

    count = store.delete_expired('2025-01-01T00:00:00.000Z')
    assert count == 1, "Should delete one expired record"
    assert store.count() == 0


def test_migrate_and_version(store):
    """Test schema migration and version."""
    assert store.version == 0
    store.version = 1
    assert store.version == 1

    # Test migrate (add a dummy column)
    migration_sql = "ALTER TABLE data ADD COLUMN dummy TEXT;"
    store.migrate(migration_sql)

    # Insert to test
    rid = store.insert(
        {'!sdata_class': 'Class', '!sdata_name': 'Name', '!sdata_suuid': 'suuid', '!sdata_sname': 'sname'})
    store.conn.execute("UPDATE data SET dummy = 'test' WHERE id = ?", (rid,))

    cursor = store.conn.cursor()
    cursor.execute("SELECT dummy FROM data WHERE id = ?", (rid,))
    assert cursor.fetchone()['dummy'] == 'test', "Dummy column should be added and updatable"