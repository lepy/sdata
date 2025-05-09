import sqlite3
import json
import shutil
import zlib
import base64
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

class JSON1SQLiteStore:
    """
    JSON store based on SQLite with extensive functionality:
      - CRUD operations
      - JSON1 functions (json_extract, json_set, ...)
      - dynamic index creation
      - wildcard searches
      - transactions (manual & context manager)
      - batch operations
      - existence/count methods
      - pagination
      - schema versioning/migrations
      - backup & restore
      - raw SQL hooks
      - TTL expiration
      - event callbacks
      - optional compression
      - type parsing on read

    Example:
        store = JSON1SQLiteStore('data.db', index_keys=['user'], compression=True)
        # Insert an entry
        rid = store.insert({'user':'alice', 'scores':[1,2,3]})
        # Extract a value
        username = store.extract(rid, '$.user')
        print(username)  # 'alice'
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
        json1_extension: Optional[str] = None,
    ):
        """
        Initialize the store and ensure JSON1 availability.

        :param filename: Path to SQLite database file
        :param index_keys: List of JSON keys to create indices for
        :param timeout: DB connection timeout in seconds
        :param check_same_thread: Allow connection sharing across threads
        :param compression: Enable compression of JSON data
        :param type_parsers: Mapping of JSON key to parser callable for reads
        :param hooks: Event hooks such as on_insert, on_update, etc.
        :param json1_extension: Path to loadable JSON1 extension if not compiled-in
        :raises RuntimeError: If JSON1 is unavailable and no extension provided
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
        # Check and load JSON1 extension if necessary
        compile_opts = [row[0] for row in self.conn.execute("PRAGMA compile_options").fetchall()]
        if not any("ENABLE_JSON1" in opt for opt in compile_opts):
            if json1_extension:
                self.conn.enable_load_extension(True)
                self.conn.load_extension(json1_extension)
                self.conn.enable_load_extension(False)
            else:
                raise RuntimeError(
                    "SQLite without JSON1 support. Compile with ENABLE_JSON1 or provide json1_extension path."
                )
        # Basic PRAGMAs
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
        Create the base table if it does not exist.
        """
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS data (
                id INTEGER PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            );
            """
        )

    def create_index(self, key: str) -> None:
        """
        Create an index on json_extract(payload, '$.key').

        Example:
            store.create_index('user')
        """
        idx_name = f"idx_json_{key}"
        sql = (
            f"CREATE INDEX IF NOT EXISTS {idx_name} "
            f"ON data ( json_extract(payload, '$.{key}') );"
        )
        self.conn.execute(sql)

    def list_indices(self) -> List[Tuple[str, bool]]:
        """
        List all indices on the 'data' table.

        :return: List of (index_name, is_unique)

        Example:
            print(store.list_indices())
        """
        cur = self.conn.execute("PRAGMA index_list('data')")
        return [(row['name'], bool(row['unique'])) for row in cur]

    def regenerate_index(self, key: str) -> None:
        """
        Drop and recreate the index for the given key.

        Example:
            store.regenerate_index('user')
        """
        idx_name = f"idx_json_{key}"
        self.conn.execute(f"DROP INDEX IF EXISTS {idx_name}")
        self.create_index(key)

    def insert(self, obj: Dict[str, Any]) -> int:
        """
        Insert a JSON object.

        :param obj: Dictionary to store
        :return: Generated record ID

        Example:
            rid = store.insert({'user':'bob'})
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
        Batch insert multiple objects.

        :param objs: List of dictionaries
        :return: List of newly inserted IDs

        Example:
            ids = store.insert_many([{'a':1},{'a':2}])
        """
        arr = [(self._serialize(o),) for o in objs]
        self.conn.executemany(
            "INSERT INTO data (payload) VALUES (json(?))", arr
        )
        max_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return list(range(max_id - len(objs) + 1, max_id + 1))

    def get(self, record_id: int) -> Optional[Dict[str, Any]]:
        """
        Read the JSON document by its ID.

        :param record_id: Record ID
        :return: Dictionary or None

        Example:
            doc = store.get(rid)
        """
        row = self.conn.execute(
            "SELECT payload FROM data WHERE id = ?", (record_id,)
        ).fetchone()
        return self._deserialize(row['payload']) if row else None

    def fetch_all(self) -> List[Dict[str, Any]]:
        """
        Read all records.

        :return: List of dictionaries

        Example:
            all_docs = store.fetch_all()
        """
        cur = self.conn.execute("SELECT payload FROM data")
        return [self._deserialize(r['payload']) for r in cur]

    def update(self, record_id: int, new_obj: Dict[str, Any]) -> None:
        """
        Overwrite the object with a new version.

        :param record_id: Record ID
        :param new_obj: New dictionary

        Example:
            store.update(rid, {'user':'carol'})
        """
        payload = self._serialize(new_obj)
        self.conn.execute(
            "UPDATE data SET payload = json(?) WHERE id = ?", (payload, record_id)
        )
        if hook := self.hooks.get('on_update'):
            hook(record_id, new_obj)

    def update_many(self, pairs: List[Tuple[int, Dict[str, Any]]]) -> None:
        """
        Batch update multiple records.

        :param pairs: List of (ID, dictionary) pairs

        Example:
            store.update_many([(1,{'a':9}), (2,{'a':8})])
        """
        arr = [(self._serialize(obj), rid) for rid, obj in pairs]
        self.conn.executemany(
            "UPDATE data SET payload = json(?) WHERE id = ?", arr
        )
        if hook := self.hooks.get('on_update_many'):
            hook(pairs)

    def delete(self, record_id: int) -> None:
        """
        Delete a record.

        :param record_id: Record ID

        Example:
            store.delete(rid)
        """
        self.conn.execute("DELETE FROM data WHERE id = ?", (record_id,))
        if hook := self.hooks.get('on_delete'):
            hook(record_id)

    def exists(self, record_id: int) -> bool:
        """
        Check if a record exists.

        :return: True/False

        Example:
            print(store.exists(rid))
        """
        cur = self.conn.execute(
            "SELECT 1 FROM data WHERE id = ? LIMIT 1", (record_id,)
        )
        return cur.fetchone() is not None

    def exists_where(self, key: str, value: Any) -> bool:
        """
        Check existence based on a JSON field.

        :param key: JSON path key
        :param value: Comparison value
        :return: True/False

        Example:
            store.exists_where('user','alice')
        """
        cur = self.conn.execute(
            "SELECT 1 FROM data WHERE json_extract(payload, '$."+key+"') = ? LIMIT 1", (value,)
        )
        return cur.fetchone() is not None

    def count(self) -> int:
        """
        Count all records.

        :return: Count

        Example:
            print(store.count())
        """
        return self.conn.execute("SELECT COUNT(*) FROM data").fetchone()[0]

    def count_where(
        self,
        key: str,
        op: str,
        value: Any
    ) -> int:
        """
        Count records matching a condition.

        :param key: JSON field
        :param op: Comparison operator (=, >, <, LIKE)
        :param value: Comparison value
        :return: Number of matches

        Example:
            print(store.count_where('age','>',30))
        """
        op_sql = op.upper()
        val = value
        if isinstance(value, str) and '*' in value:
            op_sql = 'LIKE'
            val = value.replace('*','%')
        sql = (
            "SELECT COUNT(*) FROM data "
            f"WHERE json_extract(payload, '$.{key}') {op_sql} ?"
        )
        return self.conn.execute(sql,(val,)).fetchone()[0]

    def fetch_page(
        self,
        limit: int,
        offset: int,
        key: Optional[str] = None,
        op: str = '=',
        value: Any = None
    ) -> List[Dict[str, Any]]:
        """
        Paginated query with optional filter.

        :param limit: Page size
        :param offset: Offset
        :param key: Optional filter key
        :param op: Comparison operator
        :param value: Comparison value
        :return: List of dictionaries

        Example:
            page = store.fetch_page(10,0,'user','=','alice')
        """
        if key and value is not None:
            op_sql = op.upper()
            val = value
            if isinstance(value,str) and '*' in value:
                op_sql='LIKE'
                val = value.replace('*','%')
            sql = (
                "SELECT payload FROM data "
                f"WHERE json_extract(payload,'$.{key}') {op_sql} ? "
                "ORDER BY id ASC LIMIT ? OFFSET ?"
            )
            cur = self.conn.execute(sql,(val,limit,offset))
        else:
            cur = self.conn.execute(
                "SELECT payload FROM data ORDER BY id ASC LIMIT ? OFFSET ?",(limit,offset)
            )
        return [self._deserialize(r['payload']) for r in cur]

    def get_version(self) -> int:
        """
        Get the current schema version (PRAGMA user_version).

        :return: Version number

        Example:
            print(store.get_version())
        """
        return self.conn.execute("PRAGMA user_version").fetchone()[0]

    def set_version(self, version: int) -> None:
        """
        Set the schema version (PRAGMA user_version).

        :param version: New version number

        Example:
            store.set_version(2)
        """
        self.conn.execute(f"PRAGMA user_version = {version}")

    def migrate(self, migration_sql: str) -> None:
        """
        Execute migration SQL script.

        :param migration_sql: SQL script with ALTER/CREATE statements

        Example:
            store.migrate("ALTER TABLE data ADD COLUMN extra TEXT;")
        """
        self.conn.executescript(migration_sql)

    def backup(self, dest_path: str) -> None:
        """
        Create a backup of the database.

        :param dest_path: Destination file path

        Example:
            store.backup('backup.db')
        """
        dest = sqlite3.connect(dest_path)
        with dest:
            self.conn.backup(dest)
        dest.close()

    def restore(self, src_path: str) -> None:
        """
        Restore from a backup file.

        :param src_path: Path to the backup file

        Example:
            store.restore('backup.db')
        """
        self.conn.close()
        shutil.copy(src_path,self.filename)
        self.conn = sqlite3.connect(self.filename)

    def execute_raw(
        self,
        sql: str,
        params: Optional[Union[Tuple[Any,...],List[Any]]] = None
    ) -> sqlite3.Cursor:
        """
        Execute raw SQL and return a cursor.

        :param sql: SQL string
        :param params: Optional parameters
        :return: sqlite3.Cursor

        Example:
            cursor = store.execute_raw("SELECT id FROM data WHERE ...")
        """
        return self.conn.execute(sql,params) if params else self.conn.execute(sql)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """
        Context manager for transactions.

        Example:
            with store.transaction():
                store.insert({'x':1})
                store.insert({'x':2})
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
        created_before: Union[datetime,str]
    ) -> int:
        """
        Delete entries older than the given timestamp.

        :param created_before: datetime or ISO-formatted string
        :return: Number of deleted entries

        Example:
            expired = store.delete_expired(datetime.utcnow() - timedelta(days=30))
        """
        ts = (created_before.strftime('%Y-%m-%dT%H:%M:%fZ')
              if isinstance(created_before,datetime) else created_before)
        cur = self.conn.execute(
            "DELETE FROM data WHERE created_at < ?",(ts,)
        )
        return cur.rowcount

    # JSON1-specific methods
    def extract(self, record_id: int, json_path: str) -> Any:
        """
        Extract a value at the given JSON path.

        :param record_id: Record ID
        :param json_path: JSON path (e.g., '$.user')
        :return: Extracted value

        Example:
            val = store.extract(rid,'$.scores[0]')
        """
        cur = self.conn.execute(
            "SELECT json_extract(payload, ?) FROM data WHERE id = ?",(json_path,record_id)
        )
        return cur.fetchone()[0]

    def set_path(self, record_id: int, json_path: str, value: Any) -> None:
        """
        Set or update a value at the given JSON path.

        :param record_id: Record ID
        :param json_path: JSON path
        :param value: New value to set

        Example:
            store.set_path(rid,'$.count',5)
        """
        val = json.dumps(value,separators=(',',':'))
        self.conn.execute(
            "UPDATE data SET payload = json_set(payload, ?, json(?)) WHERE id = ?",
            (json_path,val,record_id)
        )

    def insert_path(self, record_id: int, json_path: str, value: Any) -> None:
        """
        Insert a new key at the given JSON path if it does not exist.

        Example:
            store.insert_path(rid,'$.newKey','val')
        """
        val = json.dumps(value,separators=(',',':'))
        self.conn.execute(
            "UPDATE data SET payload = json_insert(payload, ?, json(?)) WHERE id = ?",
            (json_path,val,record_id)
        )

    def replace_path(self, record_id: int, json_path: str, value: Any) -> None:
        """
        Replace the existing value at the given JSON path.

        Example:
            store.replace_path(rid,'$.user','eve')
        """
        val = json.dumps(value,separators=(',',':'))
        self.conn.execute(
            "UPDATE data SET	payload = json_replace(payload, ?, json(?)) WHERE id = ?",
            (json_path,val,record_id)
        )

    def remove_path(self, record_id: int, *json_paths: str) -> None:
        """
        Remove keys or elements at the given JSON paths.

        Example:
            store.remove_path(rid,'$.oldKey')
        """
        placeholders = ",".join("?" for _ in json_paths)
        sql = f"UPDATE data SET	payload = json_remove(payload,{placeholders}) WHERE id = ?"
        self.conn.execute(sql,(*json_paths,record_id))

    def array_length(self, record_id: int, json_path: str) -> int:
        """
        Return the length of a JSON array at the given path.

        Example:
            length = store.array_length(rid,'$.scores')
        """
        cur = self.conn.execute(
            "SELECT json_array_length(payload, ?) FROM data WHERE id = ?",(json_path,record_id)
        )
        return cur.fetchone()[0]

    def each(self, record_id: int, json_path: str) -> List[Dict[str, Any]]:
        """
        Return an array or object as a table (json_each).

        Example:
            rows = store.each(rid,'$.scores')
        """
        cur = self.conn.execute(
            "SELECT key,value FROM data,json_each(data.payload, ?) WHERE id = ?",
            (json_path,record_id)
        )
        return [dict(r) for r in cur.fetchall()]

    def tree(self, record_id: int) -> List[Dict[str, Any]]:
        """
        Return the tree structure of all JSON nodes (json_tree).

        Example:
            nodes = store.tree(rid)
        """
        cur = self.conn.execute(
            "SELECT path,key,value FROM data,json_tree(data.payload) WHERE id = ?",
            (record_id,)
        )
        return [dict(r) for r in cur.fetchall()]

    def __enter__(self) -> 'JSONSQLiteStore':
        """
        Enable usage as a context manager.
        """
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """
        Close the database connection.
        """
        self.conn.close()
