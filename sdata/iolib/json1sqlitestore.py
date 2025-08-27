import sqlite3
import json
import shutil
import zlib
import base64
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union
import re

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
        unique_index_keys: Optional[List[str]] = None,
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
        :param index_keys: List of JSON keys to create non-unique indices for
        :param unique_index_keys: List of JSON keys to create unique indices for
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
        if not self.compression:
            # Check if JSON1 is available by trying a json function
            try:
                self.conn.execute("SELECT json('{}')")
            except sqlite3.OperationalError:
                if json1_extension:
                    self.conn.enable_load_extension(True)
                    self.conn.load_extension(json1_extension)
                    self.conn.enable_load_extension(False)
                    # Verify after loading
                    try:
                        self.conn.execute("SELECT json('{}')")
                    except sqlite3.OperationalError:
                        raise RuntimeError("Failed to load JSON1 extension.")
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
                self.create_index(key, unique=False)
        if unique_index_keys:
            for key in unique_index_keys:
                self.create_index(key, unique=True)

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

    def _serialize(self, obj: Dict[str, Any]) -> str:
        json_str = json.dumps(obj, separators=(',', ':'))
        if self.compression:
            compressed = zlib.compress(json_str.encode('utf-8'))
            return base64.b64encode(compressed).decode('ascii')
        return json_str

    def _deserialize(self, payload: str) -> Dict[str, Any]:
        if self.compression:
            compressed = base64.b64decode(payload)
            json_str = zlib.decompress(compressed).decode('utf-8')
        else:
            json_str = payload
        obj = json.loads(json_str)
        for key, parser in self.type_parsers.items():
            if key in obj:
                obj[key] = parser(obj[key])
        return obj

    def _get_by_path(self, obj: Any, path: str) -> Any:
        if not path.startswith('$'):
            path = '$' + path
        parts = path[1:].lstrip('.').split('.')
        current = obj
        for part in parts:
            idx = None
            key = part
            if '[' in part:
                key_idx = part.split('[', 1)
                key = key_idx[0]
                idx_str = key_idx[1].rstrip(']')
                idx = int(idx_str)
            if key:
                current = current[key]
            if idx is not None:
                current = current[idx]
        return current

    def _set_by_path(self, obj: Any, path: str, value: Any, mode: str = 'set') -> None:
        # mode: 'set', 'insert', 'replace'
        if not path.startswith('$'):
            path = '$' + path
        parts = path[1:].lstrip('.').split('.')
        current = obj
        for i, part in enumerate(parts[:-1]):
            idx = None
            key = part
            if '[' in part:
                key_idx = part.split('[', 1)
                key = key_idx[0]
                idx_str = key_idx[1].rstrip(']')
                idx = int(idx_str)
            if key:
                if key not in current:
                    if mode == 'replace':
                        return
                    next_part = parts[i + 1]
                    current[key] = [] if next_part.startswith('[') else {}
                if not isinstance(current[key], dict) and key:
                    raise ValueError("Path type mismatch")
                current = current[key]
            if idx is not None:
                if not isinstance(current, list):
                    raise ValueError("Path type mismatch")
                if idx > len(current) - 1:
                    if mode == 'replace':
                        return
                    num_append = idx - len(current) + 1
                    current.extend([None] * num_append)
                if current[idx] is None:
                    next_part = parts[i + 1]
                    current[idx] = [] if next_part.startswith('[') else {}
                current = current[idx]
        # Last part
        last = parts[-1]
        idx = None
        key = last
        if '[' in last:
            key_idx = last.split('[', 1)
            key = key_idx[0]
            idx_str = key_idx[1].rstrip(']')
            idx = int(idx_str)
        container = current
        if key:
            if key not in container:
                if mode == 'replace':
                    return
                container[key] = {}  # temporary, will override if no idx
            container = container[key]
        if idx is not None:
            if not isinstance(container, list):
                if mode == 'replace':
                    return
                container = []
                if key:
                    current[key] = container
                else:
                    current = container  # rare for root
            exists = idx < len(container)
            if mode == 'insert' and exists:
                return
            if mode == 'replace' and not exists:
                return
            while len(container) <= idx:
                container.append(None)
            container[idx] = value
        else:
            exists = key in current
            if mode == 'insert' and exists:
                return
            if mode == 'replace' and not exists:
                return
            current[key] = value

    def _remove_by_path(self, obj: Any, path: str) -> None:
        if not path.startswith('$'):
            path = '$' + path
        parts = path[1:].lstrip('.').split('.')
        current = obj
        for part in parts[:-1]:
            idx = None
            key = part
            if '[' in part:
                key_idx = part.split('[', 1)
                key = key_idx[0]
                idx_str = key_idx[1].rstrip(']')
                idx = int(idx_str)
            if key:
                if key not in current:
                    return
                current = current[key]
            if idx is not None:
                if not isinstance(current, list) or idx >= len(current):
                    return
                current = current[idx]
        # Last part
        last = parts[-1]
        idx = None
        key = last
        if '[' in last:
            key_idx = last.split('[', 1)
            key = key_idx[0]
            idx_str = key_idx[1].rstrip(']')
            idx = int(idx_str)
        if key:
            if key in current:
                del current[key]
        if idx is not None:
            container = current[key] if key else current
            if isinstance(container, list) and 0 <= idx < len(container):
                container.pop(idx)

    def _compare(self, a: Any, op: str, b: Any) -> bool:
        op = op.upper()
        if op == '=':
            return a == b
        elif op == '>':
            return a > b
        elif op == '<':
            return a < b
        elif op == '>=':
            return a >= b
        elif op == '<=':
            return a <= b
        elif op == 'LIKE':
            if not isinstance(a, str):
                return False
            pat = re.escape(str(b)).replace('%', '.*').replace('_', '.')
            return re.match('^' + pat + '$', a) is not None
        else:
            raise ValueError(f"Unsupported operator: {op}")

    def _each_python(self, obj: Any, json_path: str) -> List[Dict[str, Any]]:
        sub = self._get_by_path(obj, json_path)
        res = []
        if isinstance(sub, list):
            for i, v in enumerate(sub):
                res.append({'key': i, 'value': v})
        elif isinstance(sub, dict):
            for k, v in sorted(sub.items()):
                res.append({'key': k, 'value': v})
        return res

    def _tree_python(self, obj: Any, path: str = '$') -> List[Dict[str, Any]]:
        res = [{'path': path, 'key': None, 'value': obj}]
        if isinstance(obj, dict):
            for k, v in obj.items():
                res += self._tree_python(v, path + '.' + k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                res += self._tree_python(v, path + '[' + str(i) + ']')
        return res

    def create_index(self, key: str, unique: bool = False) -> None:
        """
        Create an index on json_extract(payload, '$.key').

        :param key: JSON path to index
        :param unique: If True, create a unique index

        Example:
            store.create_index('user', unique=True)
        """
        if self.compression:
            raise RuntimeError("Indexing is not supported when compression is enabled")
        idx_name = f"idx_json_{key.replace('.', '_').replace('[', '_').replace(']', '_').replace('!', '_')}"
        unique_str = 'UNIQUE ' if unique else ''
        sql = (
            f"CREATE {unique_str}INDEX IF NOT EXISTS {idx_name} "
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

    def regenerate_index(self, key: str, unique: bool = False) -> None:
        """
        Drop and recreate the index for the given key.

        :param key: JSON path to index
        :param unique: If True, recreate as unique index

        Example:
            store.regenerate_index('user', unique=True)
        """
        if self.compression:
            raise RuntimeError("Indexing is not supported when compression is enabled")
        idx_name = f"idx_json_{key.replace('.', '_').replace('[', '_').replace(']', '_').replace('!', '_')}"
        self.conn.execute(f"DROP INDEX IF EXISTS {idx_name}")
        self.create_index(key, unique=unique)

    def get_id_by_key(self, key: str, value: Any) -> Optional[int]:
        """
        Get the record ID by a JSON field value.

        :param key: JSON path key
        :param value: Value to match
        :return: Record ID or None

        Example:
            rid = store.get_id_by_key('!sdata_suuid', suuid)
        """
        if self.compression:
            cur = self.conn.execute("SELECT id, payload FROM data")
            for row in cur:
                obj = self._deserialize(row['payload'])
                val = self._get_by_path(obj, f'$.{key}')
                if val == value:
                    return row['id']
            return None
        else:
            cur = self.conn.execute(
                "SELECT id FROM data WHERE json_extract(payload, ?) = ?", (f'$.{key}', value)
            )
            row = cur.fetchone()
            return row['id'] if row else None

    def insert(self, obj: Dict[str, Any]) -> int:
        """
        Insert a JSON object.

        :param obj: Dictionary to store
        :return: Generated record ID

        Example:
            rid = store.insert({'user':'bob'})
        """
        payload = self._serialize(obj)
        sql = "INSERT INTO data (payload) VALUES (?)" if self.compression else "INSERT INTO data (payload) VALUES (json(?))"
        cur = self.conn.execute(sql, (payload,))
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
        sql = "INSERT INTO data (payload) VALUES (?)" if self.compression else "INSERT INTO data (payload) VALUES (json(?))"
        self.conn.executemany(sql, arr)
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

    def update(self, identifier: Union[int, str], new_obj: Dict[str, Any]) -> None:
        """
        Overwrite the object with a new version.

        :param identifier: Record ID (int) or '!sdata_suuid' (str)
        :param new_obj: New dictionary

        Example:
            store.update(rid, {'user':'carol'})  # by ID
            store.update(suuid, {'user':'carol'})  # by suuid
        """
        if isinstance(identifier, str):
            rid = self.get_id_by_key('!sdata_suuid', identifier)
            if rid is None:
                raise ValueError(f"No record found with '!sdata_suuid': {identifier}")
        else:
            rid = identifier
        payload = self._serialize(new_obj)
        sql = "UPDATE data SET payload = ? WHERE id = ?" if self.compression else "UPDATE data SET payload = json(?) WHERE id = ?"
        self.conn.execute(sql, (payload, rid))
        if hook := self.hooks.get('on_update'):
            hook(rid, new_obj)

    def update_many(self, pairs: List[Tuple[int, Dict[str, Any]]]) -> None:
        """
        Batch update multiple records.

        :param pairs: List of (ID, dictionary) pairs

        Example:
            store.update_many([(1,{'a':9}), (2,{'a':8})])
        """
        arr = [(self._serialize(obj), rid) for rid, obj in pairs]
        sql = "UPDATE data SET payload = ? WHERE id = ?" if self.compression else "UPDATE data SET payload = json(?) WHERE id = ?"
        self.conn.executemany(sql, arr)
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
        if self.compression:
            cur = self.conn.execute("SELECT payload FROM data")
            for row in cur:
                obj = self._deserialize(row['payload'])
                val = self._get_by_path(obj, f'$.{key}')
                if val == value:
                    return True
            return False
        else:
            cur = self.conn.execute(
                "SELECT 1 FROM data WHERE json_extract(payload, ?) = ? LIMIT 1", (f'$.{key}', value,)
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
        if self.compression:
            count = 0
            cur = self.conn.execute("SELECT payload FROM data")
            for row in cur:
                obj = self._deserialize(row['payload'])
                v = self._get_by_path(obj, f'$.{key}')
                if self._compare(v, op_sql, val):
                    count += 1
            return count
        else:
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
        if key is not None and value is not None:
            op_sql = op.upper()
            val = value
            if isinstance(value,str) and '*' in value:
                op_sql='LIKE'
                val = value.replace('*','%')
            if self.compression:
                matching = []
                cur = self.conn.execute("SELECT payload FROM data ORDER BY id ASC")
                for row in cur:
                    obj = self._deserialize(row['payload'])
                    v = self._get_by_path(obj, f'$.{key}')
                    if self._compare(v, op_sql, val):
                        matching.append(obj)
                return matching[offset : offset + limit]
            else:
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
        if self.compression:
            obj = self.get(record_id)
            if obj is None:
                return None
            return self._get_by_path(obj, json_path)
        else:
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
        if self.compression:
            obj = self.get(record_id)
            if obj is None:
                return
            self._set_by_path(obj, json_path, value, mode='set')
            self.update(record_id, obj)
        else:
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
        if self.compression:
            obj = self.get(record_id)
            if obj is None:
                return
            self._set_by_path(obj, json_path, value, mode='insert')
            self.update(record_id, obj)
        else:
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
        if self.compression:
            obj = self.get(record_id)
            if obj is None:
                return
            self._set_by_path(obj, json_path, value, mode='replace')
            self.update(record_id, obj)
        else:
            val = json.dumps(value,separators=(',',':'))
            self.conn.execute(
                "UPDATE data SET    payload = json_replace(payload, ?, json(?)) WHERE id = ?",
                (json_path,val,record_id)
            )

    def remove_path(self, record_id: int, *json_paths: str) -> None:
        """
        Remove keys or elements at the given JSON paths.

        Example:
            store.remove_path(rid,'$.oldKey')
        """
        if self.compression:
            obj = self.get(record_id)
            if obj is None:
                return
            for p in json_paths:
                self._remove_by_path(obj, p)
            self.update(record_id, obj)
        else:
            placeholders = ",".join("?" for _ in json_paths)
            sql = f"UPDATE data SET payload = json_remove(payload,{placeholders}) WHERE id = ?"
            self.conn.execute(sql,(*json_paths,record_id))

    def array_length(self, record_id: int, json_path: str) -> int:
        """
        Return the length of a JSON array at the given path.

        Example:
            length = store.array_length(rid,'$.scores')
        """
        if self.compression:
            obj = self.get(record_id)
            if obj is None:
                return 0
            arr = self._get_by_path(obj, json_path)
            return len(arr) if isinstance(arr, list) else 0
        else:
            cur = self.conn.execute(
                "SELECT json_array_length(payload, ?) FROM data WHERE id = ?",(json_path,record_id)
            )
            return cur.fetchone()[0] or 0

    def each(self, record_id: int, json_path: str) -> List[Dict[str, Any]]:
        """
        Return an array or object as a table (json_each).

        Example:
            rows = store.each(rid,'$.scores')
        """
        if self.compression:
            obj = self.get(record_id)
            if obj is None:
                return []
            return self._each_python(obj, json_path)
        else:
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
        if self.compression:
            obj = self.get(record_id)
            if obj is None:
                return []
            return self._tree_python(obj)
        else:
            cur = self.conn.execute(
                "SELECT path,key,value FROM data,json_tree(data.payload) WHERE id = ?",
                (record_id,)
            )
            return [dict(r) for r in cur.fetchall()]

    def __enter__(self) -> 'JSON1SQLiteStore':
        """
        Enable usage as a context manager.
        """
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """
        Close the database connection.
        """
        self.conn.close()