import sqlite3
import json
import shutil
import zlib
import base64
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union
import re
import warnings

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
        if self.compression:
            warnings.warn("Compression enabled: Native JSON1 queries and indexing are disabled. Use with caution for large datasets.")
        else:
            # Check if JSON1 is available
            try:
                self.conn.execute("SELECT json('{}')")
            except sqlite3.OperationalError:
                if json1_extension:
                    self.conn.enable_load_extension(True)
                    self.conn.load_extension(json1_extension)
                    self.conn.enable_load_extension(False)
                    try:
                        self.conn.execute("SELECT json('{}')")
                    except sqlite3.OperationalError:
                        raise RuntimeError("Failed to load JSON1 extension.")
                else:
                    raise RuntimeError("SQLite without JSON1 support. Compile with ENABLE_JSON1 or provide extension.")
        # PRAGMAs for performance
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.conn.execute("PRAGMA temp_store = MEMORY")
        self.conn.row_factory = sqlite3.Row
        self._ensure_table()
        index_keys = index_keys or []
        unique_index_keys = unique_index_keys or []
        for key in index_keys:
            self.create_index(key, unique=False)
        for key in unique_index_keys:
            self.create_index(key, unique=True)

    def _ensure_table(self) -> None:
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
        parts = re.split(r'\.|\[|\]', path[1:].lstrip('.'))  # Verbessert: Besserer Split für Pfade
        parts = [p for p in parts if p]  # Entferne leere Teile von []
        current = obj
        try:
            for part in parts:
                if part.isdigit():
                    current = current[int(part)]
                else:
                    current = current[part]
            return current
        except (KeyError, IndexError, TypeError) as e:
            raise KeyError(f"Path '{path}' not found or type mismatch: {e}")

    def _set_by_path(self, obj: Any, path: str, value: Any, mode: str = 'set') -> None:
        # Verbessert: Sauberere Handhabung, mit Default-Werten für fehlende Container
        if not path.startswith('$'):
            path = '$' + path
        parts = re.split(r'\.|\[|\]', path[1:].lstrip('.'))
        parts = [p for p in parts if p]
        current = obj
        for i, part in enumerate(parts[:-1]):
            if part.isdigit():
                idx = int(part)
                if not isinstance(current, list):
                    raise ValueError("Path type mismatch: Expected list")
                while len(current) <= idx:
                    current.append(None)
                if current[idx] is None:
                    next_part = parts[i + 1]
                    current[idx] = [] if next_part.isdigit() else {}
                current = current[idx]
            else:
                if part not in current:
                    if mode == 'replace':
                        return
                    next_part = parts[i + 1]
                    current[part] = [] if next_part.isdigit() else {}
                current = current[part]
        # Letzter Teil
        last = parts[-1]
        if last.isdigit():
            idx = int(last)
            if not isinstance(current, list):
                if mode == 'replace':
                    return
                current = []  # Konvertiere zu List
            exists = idx < len(current)
            if mode == 'insert' and exists:
                return
            if mode == 'replace' and not exists:
                return
            while len(current) <= idx:
                current.append(None)
            current[idx] = value
        else:
            exists = last in current
            if mode == 'insert' and exists:
                return
            if mode == 'replace' and not exists:
                return
            current[last] = value

    def _remove_by_path(self, obj: Any, path: str) -> None:
        # Verbessert: Sauberer mit try-except
        try:
            parent = self._get_by_path(obj, path.rsplit('.', 1)[0] if '.' in path else '$')
            key = path.rsplit('.', 1)[-1]
            if '[' in key:
                key, idx_str = key.split('[')
                idx = int(idx_str.rstrip(']'))
                if isinstance(parent.get(key, []), list):
                    parent[key].pop(idx)
            else:
                parent.pop(key, None)
        except KeyError:
            pass  # Ignoriere, wenn nicht existent (pythonic: EAFP)

    def _compare(self, a: Any, op: str, b: Any) -> bool:
        op = op.upper()
        ops = {
            '=': lambda: a == b,
            '>': lambda: a > b,
            '<': lambda: a < b,
            '>=': lambda: a >= b,
            '<=': lambda: a <= b,
            'LIKE': lambda: re.match('^' + re.escape(str(b)).replace('%', '.*').replace('_', '.' ) + '$', str(a)) is not None if isinstance(a, str) else False,
        }
        try:
            return ops[op]()
        except KeyError:
            raise ValueError(f"Unsupported operator: {op}")

    def _each_python(self, obj: Any, json_path: str) -> List[Dict[str, Any]]:
        sub = self._get_by_path(obj, json_path)
        if isinstance(sub, list):
            return [{'key': i, 'value': v} for i, v in enumerate(sub)]
        elif isinstance(sub, dict):
            return [{'key': k, 'value': v} for k, v in sorted(sub.items())]
        return []

    def _tree_python(self, obj: Any, path: str = '$') -> Iterator[Dict[str, Any]]:
        # Verbessert: Generator für Memory-Effizienz bei tiefen Trees
        yield {'path': path, 'key': None, 'value': obj}
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield from self._tree_python(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                yield from self._tree_python(v, f"{path}[{i}]")

    def create_index(self, key: str, unique: bool = False) -> None:
        if self.compression:
            raise RuntimeError("Indexing not supported with compression")
        idx_name = f"idx_json_{key.replace('.', '_').replace('[', '_').replace(']', '_').replace('!', '_')}"
        unique_str = 'UNIQUE ' if unique else ''
        sql = f"CREATE {unique_str}INDEX IF NOT EXISTS {idx_name} ON data (json_extract(payload, '$.{key}'));"
        self.conn.execute(sql)

    def list_indices(self) -> List[Tuple[str, bool]]:
        cur = self.conn.execute("PRAGMA index_list('data')")
        return [(row['name'], bool(row['unique'])) for row in cur.fetchall()]

    def regenerate_index(self, key: str, unique: bool = False) -> None:
        if self.compression:
            raise RuntimeError("Indexing not supported with compression")
        idx_name = f"idx_json_{key.replace('.', '_').replace('[', '_').replace(']', '_').replace('!', '_')}"
        self.conn.execute(f"DROP INDEX IF EXISTS {idx_name}")
        self.create_index(key, unique=unique)

    def get_id_by_key(self, key: str, value: Any) -> Optional[int]:
        if self.compression:
            for row in self.conn.execute("SELECT id, payload FROM data"):
                obj = self._deserialize(row['payload'])
                if self._get_by_path(obj, key) == value:
                    return row['id']
            return None
        else:
            row = self.conn.execute(
                "SELECT id FROM data WHERE json_extract(payload, ?) = ?", (f'$.{key}', value)
            ).fetchone()
            return row['id'] if row else None

    def insert(self, obj: Dict[str, Any]) -> int:
        payload = self._serialize(obj)
        sql = "INSERT INTO data (payload) VALUES (?)" if self.compression else "INSERT INTO data (payload) VALUES (json(?))"
        cur = self.conn.execute(sql, (payload,))
        rid = cur.lastrowid
        if 'on_insert' in self.hooks:
            self.hooks['on_insert'](rid, obj)
        return rid

    def insert_many(self, objs: List[Dict[str, Any]]) -> List[int]:
        arr = [(self._serialize(o),) for o in objs]
        sql = "INSERT INTO data (payload) VALUES (?)" if self.compression else "INSERT INTO data (payload) VALUES (json(?))"
        self.conn.executemany(sql, arr)
        max_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        ids = list(range(max_id - len(objs) + 1, max_id + 1))
        if 'on_insert_many' in self.hooks:  # Neu: Batch-Hook
            self.hooks['on_insert_many'](list(zip(ids, objs)))
        return ids

    def get(self, record_id: int) -> Optional[Dict[str, Any]]:
        row = self.conn.execute("SELECT payload FROM data WHERE id = ?", (record_id,)).fetchone()
        return self._deserialize(row['payload']) if row else None

    def fetch_all(self) -> Iterator[Dict[str, Any]]:  # Verbessert: Generator für Lazy-Loading
        cur = self.conn.execute("SELECT payload FROM data")
        for row in cur:
            yield self._deserialize(row['payload'])

    def update(self, identifier: Union[int, str], new_obj: Dict[str, Any]) -> None:
        if isinstance(identifier, str):
            rid = self.get_id_by_key('!sdata_suuid', identifier)
            if rid is None:
                raise ValueError(f"No record with '!sdata_suuid': {identifier}")
        else:
            rid = identifier
        payload = self._serialize(new_obj)
        sql = "UPDATE data SET payload = ? WHERE id = ?" if self.compression else "UPDATE data SET payload = json(?) WHERE id = ?"
        self.conn.execute(sql, (payload, rid))
        if 'on_update' in self.hooks:
            self.hooks['on_update'](rid, new_obj)

    def update_many(self, pairs: List[Tuple[int, Dict[str, Any]]]) -> None:
        arr = [(self._serialize(obj), rid) for rid, obj in pairs]
        sql = "UPDATE data SET payload = ? WHERE id = ?" if self.compression else "UPDATE data SET payload = json(?) WHERE id = ?"
        self.conn.executemany(sql, arr)
        if 'on_update_many' in self.hooks:
            self.hooks['on_update_many'](pairs)

    def delete(self, record_id: int) -> None:
        self.conn.execute("DELETE FROM data WHERE id = ?", (record_id,))
        if 'on_delete' in self.hooks:
            self.hooks['on_delete'](record_id)

    def exists(self, record_id: int) -> bool:
        return self.conn.execute("SELECT 1 FROM data WHERE id = ? LIMIT 1", (record_id,)).fetchone() is not None

    def exists_where(self, key: str, value: Any) -> bool:
        if self.compression:
            for row in self.conn.execute("SELECT payload FROM data"):
                obj = self._deserialize(row['payload'])
                if self._get_by_path(obj, key) == value:
                    return True
            return False
        else:
            return self.conn.execute(
                "SELECT 1 FROM data WHERE json_extract(payload, ?) = ? LIMIT 1", (f'$.{key}', value)
            ).fetchone() is not None

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM data").fetchone()[0]

    def count_where(self, key: str, op: str, value: Any) -> int:
        op_sql = op.upper()
        val = value if '%' not in str(value) else value.replace('*', '%')  # Auto-Handle Wildcards
        if op_sql == 'LIKE':
            val = val.replace('*', '%')
        if self.compression:
            return sum(1 for row in self.conn.execute("SELECT payload FROM data")
                       if self._compare(self._get_by_path(self._deserialize(row['payload']), key), op_sql, val))
        else:
            sql = f"SELECT COUNT(*) FROM data WHERE json_extract(payload, '$.{key}') {op_sql} ?"
            return self.conn.execute(sql, (val,)).fetchone()[0]

    def fetch_page(
        self,
        limit: int,
        offset: int,
        key: Optional[str] = None,
        op: str = '=',
        value: Any = None,
        sort_by: str = 'id ASC'  # Neu: Sortier-Option
    ) -> List[Dict[str, Any]]:
        where_clause = ""
        params = (limit, offset)
        if key and value is not None:
            op_sql = op.upper()
            val = value if '%' not in str(value) else value.replace('*', '%')
            if op_sql == 'LIKE':
                val = val.replace('*', '%')
            if self.compression:
                matching = [self._deserialize(row['payload']) for row in self.conn.execute("SELECT payload FROM data")
                            if self._compare(self._get_by_path(self._deserialize(row['payload']), key), op_sql, val)]
                matching.sort(key=lambda x: x.get('id', 0))  # Simuliere Sort
                return matching[offset:offset + limit]
            else:
                where_clause = f"WHERE json_extract(payload, '$.{key}') {op_sql} ? "
                params = (val, *params)
        sql = f"SELECT payload FROM data {where_clause}ORDER BY {sort_by} LIMIT ? OFFSET ?"
        cur = self.conn.execute(sql, params)
        return [self._deserialize(row['payload']) for row in cur]

    @property
    def version(self) -> int:  # Verbessert: Property für einfachen Access
        return self.conn.execute("PRAGMA user_version").fetchone()[0]

    @version.setter
    def version(self, version: int) -> None:
        self.conn.execute(f"PRAGMA user_version = {version}")

    def migrate(self, migration_sql: str) -> None:
        self.conn.executescript(migration_sql)
        # Neu: Auto-Regenerate Indizes nach Migration
        for idx, unique in self.list_indices():
            if idx.startswith('idx_json_'):
                key = idx.replace('idx_json_', '').replace('_', '.')  # Approximativ
                self.regenerate_index(key, unique)

    def backup(self, dest_path: str) -> None:
        with sqlite3.connect(dest_path) as dest:
            self.conn.backup(dest)

    def restore(self, src_path: str) -> None:
        self.conn.close()
        shutil.copy(src_path, self.filename)
        self.conn = sqlite3.connect(self.filename)

    def execute_raw(self, sql: str, params: Optional[Tuple[Any, ...]] = None) -> sqlite3.Cursor:
        return self.conn.execute(sql, params or ())

    @contextmanager
    def transaction(self) -> Iterator[None]:
        self.conn.execute("BEGIN")
        try:
            yield
            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def delete_expired(self, created_before: Union[datetime, str]) -> int:
        ts = created_before if isinstance(created_before, str) else created_before.strftime('%Y-%m-%dT%H:%M:%fZ')
        cur = self.conn.execute("DELETE FROM data WHERE created_at < ?", (ts,))
        if 'on_delete_expired' in self.hooks:
            self.hooks['on_delete_expired'](cur.rowcount)
        return cur.rowcount

    def extract(self, record_id: int, json_path: str) -> Any:
        if self.compression:
            obj = self.get(record_id)
            return self._get_by_path(obj, json_path) if obj else None
        else:
            return self.conn.execute(
                "SELECT json_extract(payload, ?) FROM data WHERE id = ?", (json_path, record_id)
            ).fetchone()[0]

    def set_path(self, record_id: int, json_path: str, value: Any) -> None:
        if self.compression:
            obj = self.get(record_id)
            if obj:
                self._set_by_path(obj, json_path, value, mode='set')
                self.update(record_id, obj)
        else:
            val = json.dumps(value, separators=(',', ':'))
            self.conn.execute(
                "UPDATE data SET payload = json_set(payload, ?, json(?)) WHERE id = ?",
                (json_path, val, record_id)
            )

    def insert_path(self, record_id: int, json_path: str, value: Any) -> None:
        if self.compression:
            obj = self.get(record_id)
            if obj:
                self._set_by_path(obj, json_path, value, mode='insert')
                self.update(record_id, obj)
        else:
            val = json.dumps(value, separators=(',', ':'))
            self.conn.execute(
                "UPDATE data SET payload = json_insert(payload, ?, json(?)) WHERE id = ?",
                (json_path, val, record_id)
            )

    def replace_path(self, record_id: int, json_path: str, value: Any) -> None:
        if self.compression:
            obj = self.get(record_id)
            if obj:
                self._set_by_path(obj, json_path, value, mode='replace')
                self.update(record_id, obj)
        else:
            val = json.dumps(value, separators=(',', ':'))
            self.conn.execute(
                "UPDATE data SET payload = json_replace(payload, ?, json(?)) WHERE id = ?",
                (json_path, val, record_id)
            )

    def remove_path(self, record_id: int, *json_paths: str) -> None:
        if self.compression:
            obj = self.get(record_id)
            if obj:
                for p in json_paths:
                    self._remove_by_path(obj, p)
                self.update(record_id, obj)
        else:
            params = (*json_paths, record_id)
            placeholders = ', '.join('?' for _ in json_paths)
            sql = f"UPDATE data SET payload = json_remove(payload, {placeholders}) WHERE id = ?"
            self.conn.execute(sql, params)

    def array_length(self, record_id: int, json_path: str) -> int:
        if self.compression:
            obj = self.get(record_id)
            arr = self._get_by_path(obj, json_path) if obj else []
            return len(arr) if isinstance(arr, list) else 0
        else:
            return self.conn.execute(
                "SELECT json_array_length(payload, ?) FROM data WHERE id = ?", (json_path, record_id)
            ).fetchone()[0] or 0

    def each(self, record_id: int, json_path: str) -> List[Dict[str, Any]]:
        if self.compression:
            obj = self.get(record_id)
            return self._each_python(obj, json_path) if obj else []
        else:
            cur = self.conn.execute(
                "SELECT key, value FROM data, json_each(payload, ?) WHERE data.id = ?",
                (json_path, record_id)
            )
            return [dict(row) for row in cur]

    def tree(self, record_id: int) -> List[Dict[str, Any]]:
        if self.compression:
            obj = self.get(record_id)
            return list(self._tree_python(obj)) if obj else []
        else:
            cur = self.conn.execute(
                "SELECT path, key, value FROM data, json_tree(payload) WHERE data.id = ?",
                (record_id,)
            )
            return [dict(row) for row in cur]

    def find_by(self, attribute: str, value: Any, op: str = '=', limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Einfacher Zugriff auf Elemente basierend auf Attribut (z.B. '!sdata_class').
        Nutzt Indizes, wenn vorhanden. Pythonic: Wie eine Query-Methode in ORMs.

        :param attribute: Attribut-Key (z.B. '!sdata_class')
        :param value: Wert zum Matchen
        :param op: Operator ('=', '>', '<', 'LIKE' etc.)
        :param limit: Max. Ergebnisse (None = alle)
        :param offset: Offset für Pagination
        :return: Liste von passenden Dicts

        Example:
            classes = store.find_by('!sdata_class', 'MyClass')  # Alle mit !sdata_class == 'MyClass'
            names_like = store.find_by('!sdata_name', 'alice*', op='LIKE', limit=10)  # Wildcard-Suche
            parents = store.find_by('!sdata_parent', 42, op='>')  # Numerische Vergleiche
        """
        if attribute not in ['!sdata_class', '!sdata_name', '!sdata_parent', '!sdata_project', '!sdata_uuid', '!sdata_sname', '!sdata_suuid']:
            warnings.warn(f"Attribute '{attribute}' not in indexed keys; query may be slow.")
        return self.fetch_page(limit or 999999, offset, key=attribute, op=op, value=value)  # Hoher Default-Limit für "alle"

    def __enter__(self) -> 'JSON1SQLiteStore':
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.conn.close()