import os
import sqlite3
import json
import shutil
import zlib
import base64
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union


class JSONSQLiteStore:
    """
    JSON-based store on SQLite with:
    - CRUD methods
    - Dynamic index creation, listing, regeneration
    - Wildcard searches
    - Transactions (manual & context manager)
    - Batch operations
    - Existence/Count methods
    - Pagination
    - Schema versioning/migration
    - Backup & Restore
    - Raw SQL hooks
    - TTL expiration
    - Event callbacks
    - Optional compression
    - Type parsing on read

    Example usage:
        db_path = "/path/to/database.sqlite"
        with JSONSQLiteStore(db_path) as store:
            # Insert a record
            uid = store.insert({"user": "alice", "score": 42})
            print("New ID:", uid)

            # Fetch a record
            alice = store.get(uid)
            print("Fetched:", alice)

            # Update a record
            alice["score"] = 99
            store.update(uid, alice)

            # Delete a record
            store.delete(uid)
    """

    def __init__(
            self,
            filename: str,
            index_keys: Optional[List[str]] = None,
            timeout: float = 5.0,
            check_same_thread: bool = True,
            compression: bool = False,
            type_parsers: Optional[Dict[str, Callable[[Any], Any]]] = None,
            hooks: Optional[Dict[str, Callable[..., None]]] = None,
    ):
        """
        Initializes the JSONSQLiteStore with the specified parameters.

        Args:
            filename (str): The path to the SQLite database file.
            index_keys (Optional[List[str]]): List of keys to create indices on.
            timeout (float): Timeout for database connections.
            check_same_thread (bool): Whether to check the same thread for connections.
            compression (bool): Whether to enable compression for stored data.
            type_parsers (Optional[Dict[str, Callable[[Any], Any]]]): Custom type parsers for deserialization.
            hooks (Optional[Dict[str, Callable[..., None]]]): Event hooks for various operations.
        """
        self.filename = filename
        self.compression = compression
        self.type_parsers = type_parsers or {}
        self.hooks = hooks or {}
        self.conn = sqlite3.connect(
            filename,
            timeout=timeout,
            check_same_thread=check_same_thread,
            isolation_level=None,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.conn.execute("PRAGMA temp_store = MEMORY")
        self.conn.row_factory = sqlite3.Row
        self._ensure_table()
        if index_keys:
            for key in index_keys:
                self.create_index(key)

    def _ensure_table(self) -> None:
        """
        Ensures that the data table exists in the database.

        Creates the table if it does not already exist.
        """
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS data (
                id      INTEGER PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            );
            """
        )

    def create_index(self, key: str) -> None:
        """
        Creates an index on the specified key in the data table.

        Args:
            key (str): The key to create an index on.
        """
        idx_name = f"idx_json_{key}"
        sql = (
            f"CREATE INDEX IF NOT EXISTS {idx_name} "
            f"ON data ( json_extract(payload, '$.{key}') );"
        )
        self.conn.execute(sql)

    def list_indices(self) -> List[Tuple[str, bool]]:
        """
        Lists all indices on the data table.

        Returns:
            List[Tuple[str, bool]]: A list of tuples containing index names and their uniqueness.
        """
        cur = self.conn.execute("PRAGMA index_list('data')")
        return [(row['name'], bool(row['unique'])) for row in cur]

    def regenerate_index(self, key: str) -> None:
        """
        Regenerates the index for the specified key.

        Args:
            key (str): The key for which to regenerate the index.
        """
        idx_name = f"idx_json_{key}"
        self.conn.execute(f"DROP INDEX IF EXISTS {idx_name}")
        self.create_index(key)

    def _serialize(self, obj: Dict[str, Any]) -> str:
        """
        Serializes a dictionary to a JSON string, optionally compressing it.

        Args:
            obj (Dict[str, Any]): The object to serialize.

        Returns:
            str: The serialized JSON string.
        """
        try:
            js = json.dumps(obj, separators=(',', ':'))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Serialization error: {e} for object: {obj}")

        if self.compression:
            comp = zlib.compress(js.encode('utf-8'))
            return base64.b64encode(comp).decode('ascii')
        return js

    def _deserialize(self, payload: str) -> Dict[str, Any]:
        """
        Deserializes a JSON string back into a dictionary, applying type parsing if necessary.

        Args:
            payload (str): The JSON string to deserialize.

        Returns:
            Dict[str, Any]: The deserialized object.
        """
        raw = payload
        if self.compression:
            comp = base64.b64decode(payload.encode('ascii'))
            raw = zlib.decompress(comp).decode('utf-8')
        obj = json.loads(raw)
        # Typ-Parsing
        for key, parser in self.type_parsers.items():
            if key in obj:
                obj[key] = parser(obj[key])
        return obj

    def insert(self, obj: Dict[str, Any]) -> int:
        """
        Inserts a new record into the database.

        Args:
            obj (Dict[str, Any]): The object to insert.

        Returns:
            int: The ID of the newly inserted record.
        """
        payload = self._serialize(obj)
        cur = self.conn.execute(
            "INSERT INTO data (payload) VALUES (json(?))", (payload,)
        )
        rid = cur.lastrowid
        if hook := self.hooks.get('on_insert'):
            hook(rid, obj)
        return rid

    def insert_many(self, objs: List[Dict[str, Any]]) -> List[int]:
        """
        Inserts multiple records into the database.

        Args:
            objs (List[Dict[str, Any]]): The list of objects to insert.

        Returns:
            List[int]: A list of IDs of the newly inserted records.
        """
        arr = [(self._serialize(o),) for o in objs]
        cur = self.conn.executemany(
            "INSERT INTO data (payload) VALUES (json(?))", arr
        )
        if hook := self.hooks.get('on_insert_many'):
            hook(objs)
        # SQLite executemany doesn't return rowids list; fetch max id minus count +1
        max_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return list(range(max_id - len(objs) + 1, max_id + 1))

    def get(self, record_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves a record by its ID.

        Args:
            record_id (int): The ID of the record to retrieve.

        Returns:
            Optional[Dict[str, Any]]: The retrieved object, or None if not found.
        """
        row = self.conn.execute(
            "SELECT payload FROM data WHERE id = ?", (record_id,)
        ).fetchone()
        return self._deserialize(row['payload']) if row else None

    def fetch_all(self) -> List[Dict[str, Any]]:
        """
        Fetches all records from the database.

        Returns:
            List[Dict[str, Any]]: A list of all records.
        """
        cur = self.conn.execute("SELECT payload FROM data")
        return [self._deserialize(r[0]) for r in cur]  # Access the first element of the tuple

    def find_by(
            self,
            key: str,
            op: str,
            value: Any
    ) -> List[Dict[str, Any]]:
        """
        Finds records based on a specific key and operation.

        Args:
            key (str): The key to search by.
            op (str): The operation to perform (e.g., '=', '>', '<', 'LIKE').
            value (Any): The value to compare against.

        Returns:
            List[Dict[str, Any]]: A list of matching records.
        """
        op_sql = op.upper()
        val = value
        if isinstance(value, str) and '*' in value:
            op_sql = 'LIKE'
            val = value.replace('*', '%')
        sql = (
            "SELECT payload FROM data "
            f"WHERE json_extract(payload, '$.{key}') {op_sql} ? "
            f"ORDER BY json_extract(payload, '$.{key}') DESC"
        )
        cur = self.conn.execute(sql, (val,))
        return [self._deserialize(r['payload']) for r in cur]

    def get_dict(self, key: str, value: Any) -> List[Dict[str, Any]]:
        """
        Retrieves records where a specific key matches a value.

        Args:
            key (str): The key to match.
            value (Any): The value to match against.

        Returns:
            List[Dict[str, Any]]: A list of matching records.

        Example usage:
            users = store.get_dict("user", "alice")
            print(users)
        """
        return self.find_by(key, '=', value)

    def update(
            self,
            record_id: int,
            new_obj: Dict[str, Any]
    ) -> None:
        """
        Updates an existing record in the database.

        Args:
            record_id (int): The ID of the record to update.
            new_obj (Dict[str, Any]): The new object data to update the record with.

        Example usage:
            store.update(uid, {"user": "alice", "score": 100})
        """
        payload = self._serialize(new_obj)
        self.conn.execute(
            "UPDATE data SET payload = json(?) WHERE id = ?", (payload, record_id)
        )
        if hook := self.hooks.get('on_update'):
            hook(record_id, new_obj)

    def update_many(self, pairs: List[Tuple[int, Dict[str, Any]]]) -> None:
        """
        Updates multiple records in the database.

        Args:
            pairs (List[Tuple[int, Dict[str, Any]]]): A list of tuples containing record IDs and their new data.

        Example usage:
            updates = [(uid1, {"score": 50}), (uid2, {"score": 75})]
            store.update_many(updates)
        """
        arr = [(self._serialize(obj), rid) for rid, obj in pairs]
        self.conn.executemany(
            "UPDATE data SET payload = json(?) WHERE id = ?", arr
        )
        if hook := self.hooks.get('on_update_many'):
            hook(pairs)

    def delete(self, record_id: int) -> None:
        """
        Deletes a record from the database by its ID.

        Args:
            record_id (int): The ID of the record to delete.

        Example usage:
            store.delete(uid)
        """
        self.conn.execute("DELETE FROM data WHERE id = ?", (record_id,))
        if hook := self.hooks.get('on_delete'):
            hook(record_id)

    def exists(self, record_id: int) -> bool:
        """
        Checks if a record exists in the database by its ID.

        Args:
            record_id (int): The ID of the record to check.

        Returns:
            bool: True if the record exists, False otherwise.

        Example usage:
            exists = store.exists(uid)
            print("Record exists:", exists)
        """
        cur = self.conn.execute(
            "SELECT 1 FROM data WHERE id = ? LIMIT 1", (record_id,)
        )
        return cur.fetchone() is not None

    def exists_where(self, key: str, value: Any) -> bool:
        """
        Checks if a record exists based on a specific key and value.

        Args:
            key (str): The key to check.
            value (Any): The value to match against.

        Returns:
            bool: True if a matching record exists, False otherwise.

        Example usage:
            exists = store.exists_where("user", "alice")
            print("User exists:", exists)
        """
        cur = self.conn.execute(
            "SELECT 1 FROM data WHERE json_extract(payload, '$." + key + "') = ? LIMIT 1", (value,)
        )
        return cur.fetchone() is not None

    def count(self) -> int:
        """
        Counts the total number of records in the database.

        Returns:
            int: The total number of records.

        Example usage:
            total_count = store.count()
            print("Total records:", total_count)
        """
        return self.conn.execute("SELECT COUNT(*) FROM data").fetchone()[0]

    def count_where(
            self,
            key: str,
            op: str,
            value: Any
    ) -> int:
        """
        Counts the number of records that match a specific key and operation.

        Args:
            key (str): The key to search by.
            op (str): The operation to perform (e.g., '=', '>', '<', 'LIKE').
            value (Any): The value to compare against.

        Returns:
            int: The count of matching records.

        Example usage:
            count_high_scores = store.count_where("score", ">", 40)
            print("High scores count:", count_high_scores)
        """
        op_sql = op.upper()
        val = value
        if isinstance(value, str) and '*' in value:
            op_sql = 'LIKE'
            val = value.replace('*', '%')
        sql = (
            "SELECT COUNT(*) FROM data "
            f"WHERE json_extract(payload, '$.{key}') {op_sql} ?"
        )
        return self.conn.execute(sql, (val,)).fetchone()[0]

    def fetch_page(
            self,
            limit: int,
            offset: int,
            key: Optional[str] = None,
            op: str = '=',
            value: Any = None
    ) -> List[Dict[str, Any]]:
        """
        Fetches a paginated list of records from the database.

        Args:
            limit (int): The maximum number of records to return.
            offset (int): The number of records to skip before starting to collect the result set.
            key (Optional[str]): The key to filter by (if provided).
            op (str): The operation to perform (default is '=').
            value (Any): The value to compare against (if provided).

        Returns:
            List[Dict[str, Any]]: A list of records for the specified page.

        Example usage:
            page_records = store.fetch_page(10, 0)
            print("First page records:", page_records)
        """
        if key and value is not None:
            op_sql = op.upper()
            val = value
            if isinstance(value, str) and '*' in value:
                op_sql = 'LIKE'
                val = value.replace('*', '%')
            sql = (
                "SELECT payload FROM data "
                f"WHERE json_extract(payload, '$.{key}') {op_sql} ? "
                "ORDER BY id ASC LIMIT ? OFFSET ?"
            )
            cur = self.conn.execute(sql, (val, limit, offset))
        else:
            cur = self.conn.execute(
                "SELECT payload FROM data ORDER BY id ASC LIMIT ? OFFSET ?", (limit, offset)
            )
        return [self._deserialize(r['payload']) for r in cur]

    def get_version(self) -> int:
        """
        Retrieves the current version of the database schema.

        Returns:
            int: The current user version of the database.

        Example usage:
            version = store.get_version()
            print("Current database version:", version)
        """
        return self.conn.execute("PRAGMA user_version").fetchone()[0]

    def set_version(self, version: int) -> None:
        """
        Sets the user version of the database schema.

        Args:
            version (int): The new user version to set.

        Example usage:
            store.set_version(2)
            print("Database version updated to 2.")
        """
        self.conn.execute(f"PRAGMA user_version = {version}")

    def migrate(self, migration_sql: str) -> None:
        """
        Applies a migration script to the database.

        Args:
            migration_sql (str): The SQL commands to execute for the migration.

        Example usage:
            store.migrate(migration_script)
        """
        self.conn.executescript(migration_sql)

    def backup(self, dest_path: str) -> None:
        """
        Creates a backup of the database to the specified destination path.

        Args:
            dest_path (str): The file path where the backup should be saved.

        Example usage:
            store.backup("/path/to/backup.sqlite")
            print("Backup created successfully.")
        """
        dest = sqlite3.connect(dest_path)
        with dest:
            self.conn.backup(dest)
        dest.close()

    def restore(self, src_path: str) -> None:
        """
        Restores the database from a backup file.

        Args:
            src_path (str): The file path of the backup to restore from.

        Example usage:
            store.restore("/path/to/backup.sqlite")
            print("Database restored from backup.")
        """
        self.conn.close()
        shutil.copy(src_path, self.filename)
        self.conn = sqlite3.connect(self.filename)

    def execute_raw(
            self,
            sql: str,
            params: Optional[Union[Tuple[Any, ...], List[Any]]] = None
    ) -> sqlite3.Cursor:
        """
        Executes a raw SQL command against the database.

        Args:
            sql (str): The SQL command to execute.
            params (Optional[Union[Tuple[Any, ...], List[Any]]]): Optional parameters for the SQL command.

        Returns:
            sqlite3.Cursor: The cursor object containing the result of the query.

        Example usage:
            cursor = store.execute_raw("SELECT * FROM data WHERE id = ?", (uid,))
            results = cursor.fetchall()
            print("Query results:", results)
        """
        if params:
            return self.conn.execute(sql, params)
        return self.conn.execute(sql)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """
        Context manager for handling transactions.

        This method begins a transaction, yields control to the caller,
        and commits the transaction if no exceptions occur. If an exception
        is raised, the transaction is rolled back.

        Example usage:
            with store.transaction():
                store.insert({"user": "alice", "score": 42})
                store.insert({"user": "bob", "score": 37})
        """
        try:
            self.conn.execute("BEGIN")
            yield
            self.conn.execute("COMMIT")
        except:
            self.conn.execute("ROLLBACK")
            raise

    def delete_expired(
            self,
            created_before: Union[datetime, str]
    ) -> int:
        """
        Deletes records that were created before a specified date.

        Args:
            created_before (Union[datetime, str]): The cutoff date for deletion.
                Can be a datetime object or a string in ISO format.

        Returns:
            int: The number of records deleted.

        Example usage:
            deleted_count = store.delete_expired(datetime(2022, 1, 1))
            print(f"Deleted {deleted_count} expired records.")
        """
        if isinstance(created_before, datetime):
            ts = created_before.strftime('%Y-%m-%dT%H:%M:%fZ')
        else:
            ts = created_before
        cur = self.conn.execute(
            "DELETE FROM data WHERE created_at < ?", (ts,)
        )
        return cur.rowcount

    def __enter__(self) -> 'JSONSQLiteStore':
        """
        Enters the context of the JSONSQLiteStore.

        Returns:
            JSONSQLiteStore: The current instance of the store.

        Example usage:
            with JSONSQLiteStore(db_path) as store:
                # Perform operations with the store
                pass
        """
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """
        Exits the context of the JSONSQLiteStore.

        Closes the database connection when exiting the context.

        Args:
            exc_type (Optional[type]): The type of exception raised, if any.
            exc (Optional[BaseException]): The exception instance, if any.
            tb (Optional[traceback]): The traceback object, if any.
        """
        self.conn.close()

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """
        Iterates over all records in the store.

        Yields:
            Dict[str, Any]: Each record in the store.

        Example usage:
            for record in store:
                print(record)
        """
        yield from self.fetch_all()


if __name__ == '__main__':

    db_path = os.path.join("/tmp", "json1store.sqlite")

    with JSONSQLiteStore(db_path) as store:
        # Einfügen
        uid = store.insert({"user": "alice", "score": 42})
        print("Neue ID:", uid)
        uid = store.insert({"user": "alices", "score": 43})
        print("Neue ID:", uid)

        # Lesen
        alice = store.get(uid)
        print("Gelesen:", alice)

        # Batch-Einfüge
        for u in [{"user": "bob", "score": 37}, {"user": "carol", "score": 58}]:
            store.insert(u)

        # Suche nach high scores
        highs = store.find_by("score", ">", 40)
        print("Highscores:", highs)

        # Update (ganzes Objekt)
        if alice:
            alice["score"] = 99
            store.update(uid, alice)

        # Löschen
        store.delete(uid)

        # Alle Datensätze via Iterator
        for rec in store:
            print("Datensatz:", rec)
