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
    JSON-Store auf SQLite-Basis mit:
    - CRUD-Methoden
    - dynamische Index-Erstellung, Listing, Regeneration
    - Wildcard-Suchen
    - Transaktionen (manuell & Kontextmanager)
    - Batch-Operationen
    - Existence/Count-Methoden
    - Pagination
    - Schema-Versionierung/Migration
    - Backup & Restore
    - Roh-SQL-Hooks
    - TTL-Ablauf
    - Ereignis-Callbacks
    - optionale Kompression
    - Typ-Parsing beim Lesen
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
        # Verbindung mit konfigurierbaren Parametern
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
        idx_name = f"idx_json_{key}"
        sql = (
            f"CREATE INDEX IF NOT EXISTS {idx_name} "
            f"ON data ( json_extract(payload, '$.{key}') );"
        )
        self.conn.execute(sql)

    def list_indices(self) -> List[Tuple[str, bool]]:
        cur = self.conn.execute("PRAGMA index_list('data')")
        return [(row['name'], bool(row['unique'])) for row in cur]

    def regenerate_index(self, key: str) -> None:
        idx_name = f"idx_json_{key}"
        self.conn.execute(f"DROP INDEX IF EXISTS {idx_name}")
        self.create_index(key)

    def _serialize(self, obj: Dict[str, Any]) -> str:
        js = json.dumps(obj, separators=(',',':'))
        if self.compression:
            comp = zlib.compress(js.encode('utf-8'))
            return base64.b64encode(comp).decode('ascii')
        return js

    def _deserialize(self, payload: str) -> Dict[str, Any]:
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
        payload = self._serialize(obj)
        cur = self.conn.execute(
            "INSERT INTO data (payload) VALUES (json(?))", (payload,)
        )
        rid = cur.lastrowid
        if hook := self.hooks.get('on_insert'):
            hook(rid, obj)
        return rid

    def insert_many(self, objs: List[Dict[str,Any]]) -> List[int]:
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
        row = self.conn.execute(
            "SELECT payload FROM data WHERE id = ?", (record_id,)
        ).fetchone()
        return self._deserialize(row['payload']) if row else None

    def fetch_all(self) -> List[Dict[str, Any]]:
        cur = self.conn.execute("SELECT payload FROM data")
        return [self._deserialize(r['payload']) for r in cur]

    def find_by(
        self,
        key: str,
        op: str,
        value: Any
    ) -> List[Dict[str, Any]]:
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
        return self.find_by(key, '=', value)

    def update(
        self,
        record_id: int,
        new_obj: Dict[str, Any]
    ) -> None:
        payload = self._serialize(new_obj)
        self.conn.execute(
            "UPDATE data SET payload = json(?) WHERE id = ?", (payload, record_id)
        )
        if hook := self.hooks.get('on_update'):
            hook(record_id, new_obj)

    def update_many(self, pairs: List[Tuple[int, Dict[str,Any]]]) -> None:
        arr = [(self._serialize(obj), rid) for rid, obj in pairs]
        self.conn.executemany(
            "UPDATE data SET payload = json(?) WHERE id = ?", arr
        )
        if hook := self.hooks.get('on_update_many'):
            hook(pairs)

    def delete(self, record_id: int) -> None:
        self.conn.execute("DELETE FROM data WHERE id = ?", (record_id,))
        if hook := self.hooks.get('on_delete'):
            hook(record_id)

    def exists(self, record_id: int) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM data WHERE id = ? LIMIT 1", (record_id,)
        )
        return cur.fetchone() is not None

    def exists_where(self, key: str, value: Any) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM data WHERE json_extract(payload, '$." + key + "') = ? LIMIT 1", (value,)
        )
        return cur.fetchone() is not None

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM data").fetchone()[0]

    def count_where(
        self,
        key: str,
        op: str,
        value: Any
    ) -> int:
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
        return self.conn.execute("PRAGMA user_version").fetchone()[0]

    def set_version(self, version: int) -> None:
        self.conn.execute(f"PRAGMA user_version = {version}")

    def migrate(self, migration_sql: str) -> None:
        self.conn.executescript(migration_sql)

    def backup(self, dest_path: str) -> None:
        dest = sqlite3.connect(dest_path)
        with dest:
            self.conn.backup(dest)
        dest.close()

    def restore(self, src_path: str) -> None:
        self.conn.close()
        shutil.copy(src_path, self.filename)
        self.conn = sqlite3.connect(self.filename)

    def execute_raw(
        self,
        sql: str,
        params: Optional[Union[Tuple[Any,...],List[Any]]] = None
    ) -> sqlite3.Cursor:
        if params:
            return self.conn.execute(sql, params)
        return self.conn.execute(sql)

    @contextmanager
    def transaction(self) -> Iterator[None]:
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
        if isinstance(created_before, datetime):
            ts = created_before.strftime('%Y-%m-%dT%H:%M:%fZ')
        else:
            ts = created_before
        cur = self.conn.execute(
            "DELETE FROM data WHERE created_at < ?", (ts,)
        )
        return cur.rowcount

    def __enter__(self) -> 'JSONSQLiteStore':
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.conn.close()

    def __iter__(self) -> Iterator[Dict[str, Any]]:
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
