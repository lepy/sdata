from sdata.iolib.json1sqlitestore import JSON1SQLiteStore

from typing import Any, Dict, List, Callable, Optional, Union
import re
import warnings

# Annahme: JSON1SQLiteStore ist wie zuvor definiert. Hier importieren oder kopieren.
# Für diese Antwort nehme ich an, es ist verfügbar.

class Condition:
    """Callable Condition for queries, matching TinyDB behavior."""
    def __init__(self, test: Callable[[Dict[str, Any]], bool]):
        self.test = test

    def __call__(self, doc: Dict[str, Any]) -> bool:
        return self.test(doc)

    def __and__(self, other: 'Condition') -> 'Condition':
        return Condition(lambda doc: self(doc) and other(doc))

    def __or__(self, other: 'Condition') -> 'Condition':
        return Condition(lambda doc: self(doc) or other(doc))

    def __invert__(self) -> 'Condition':
        return Condition(lambda doc: not self(doc))

class Query:
    """Query factory, similar to TinyDB Query."""
    def __init__(self):
        pass

    def __getattr__(self, field: str) -> 'Field':
        return Field(field)

    def __getitem__(self, field: str) -> 'Field':
        return Field(field)

    def fragment(self, mapping: Dict[str, Any]) -> Condition:
        return Condition(lambda doc: all(doc.get(k) == v for k, v in mapping.items()))

    def noop(self) -> Condition:
        return Condition(lambda doc: True)

class Field:
    """Field descriptor for building conditions."""
    def __init__(self, field: str):
        self.field = field

    def _get(self, doc: Dict[str, Any]) -> Any:
        parts = self.field.split('.')
        current = doc
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def __eq__(self, value: Any) -> Condition:
        return Condition(lambda doc: self._get(doc) == value)

    def __ne__(self, value: Any) -> Condition:
        return Condition(lambda doc: self._get(doc) != value)

    def __gt__(self, value: Any) -> Condition:
        return Condition(lambda doc: self._get(doc) > value)

    def __ge__(self, value: Any) -> Condition:
        return Condition(lambda doc: self._get(doc) >= value)

    def __lt__(self, value: Any) -> Condition:
        return Condition(lambda doc: self._get(doc) < value)

    def __le__(self, value: Any) -> Condition:
        return Condition(lambda doc: self._get(doc) <= value)

    def exists(self) -> Condition:
        return Condition(lambda doc: self._get(doc) is not None)

    def matches(self, regex: str, flags: int = 0) -> Condition:
        return Condition(lambda doc: bool(re.match(regex, str(self._get(doc)), flags)))

    def search(self, regex: str, flags: int = 0) -> Condition:
        return Condition(lambda doc: bool(re.search(regex, str(self._get(doc)), flags)))

    def test(self, func: Callable[[Any], bool], *args: Any) -> Condition:
        return Condition(lambda doc: func(self._get(doc), *args))

    def any(self, cond: Union[List[Any], Condition]) -> Condition:
        if isinstance(cond, list):
            return Condition(lambda doc: any(item in cond for item in self._get(doc) or []))
        else:
            return Condition(lambda doc: any(cond(item) for item in self._get(doc) or []))

    def all(self, cond: Union[List[Any], Condition]) -> Condition:
        if isinstance(cond, list):
            return Condition(lambda doc: all(item in cond for item in self._get(doc) or []))
        else:
            return Condition(lambda doc: all(cond(item) for item in self._get(doc) or []))

    def one_of(self, values: List[Any]) -> Condition:
        return Condition(lambda doc: self._get(doc) in values)

    def map(self, func: Callable[[Any], Any]) -> 'MappedField':
        return MappedField(self, func)

class MappedField(Field):
    """For map transformations."""
    def __init__(self, field: Field, func: Callable[[Any], Any]):
        self.field = field.field
        self.func = func

    def _get(self, doc: Dict[str, Any]) -> Any:
        return self.func(super()._get(doc))

# Table and TinyDB remain similar, but use Condition instead of Query for typing where appropriate
class Table:
    """Simuliert TinyDB Table; verwendet den Store mit Filter auf '!table' Field."""
    def __init__(self, store: 'JSON1SQLiteStore', name: str = '_default'):
        self.store = store
        self.name = name

    def insert(self, doc: Dict[str, Any]) -> int:
        doc['!table'] = self.name
        return self.store.insert(doc)

    def insert_multiple(self, docs: List[Dict[str, Any]]) -> List[int]:
        for doc in docs:
            doc['!table'] = self.name
        return self.store.insert_many(docs)

    def all(self) -> List[Dict[str, Any]]:
        return [doc for doc in self.store.fetch_all() if doc.get('!table') == self.name]

    def search(self, query: Condition) -> List[Dict[str, Any]]:
        return [doc for doc in self.all() if query(doc)]

    def get(self, query: Optional[Condition] = None) -> Optional[Dict[str, Any]]:
        if query is None:
            return None
        results = self.search(query)
        return results[0] if results else None

    def update(self, fields: Dict[str, Any], query: Optional[Condition] = None) -> List[int]:
        if query is None:
            query = Condition(lambda doc: True)
        matching = self.search(query)
        updated_ids = []
        for doc in matching:
            doc_id = self._get_id_from_doc(doc)
            updated_doc = doc.copy()
            updated_doc.update(fields)
            self.store.update(doc_id, updated_doc)
            updated_ids.append(doc_id)
        return updated_ids

    def remove(self, query: Optional[Condition] = None) -> List[int]:
        if query is None:
            query = Condition(lambda doc: True)
        matching = self.search(query)
        removed_ids = []
        for doc in matching:
            doc_id = self._get_id_from_doc(doc)
            self.store.delete(doc_id)
            removed_ids.append(doc_id)
        return removed_ids

    def truncate(self) -> None:
        self.remove()

    def count(self, query: Optional[Condition] = None) -> int:
        if query is None:
            return len(self.all())
        return len(self.search(query))

    def contains(self, query: Optional[Condition] = None) -> bool:
        return self.count(query) > 0

    def _get_id_from_doc(self, doc: Dict) -> int:
        suuid = doc.get('!sdata_suuid')
        if suuid:
            return self.store.get_id_by_key('!sdata_suuid', suuid) or 0
        raise ValueError("No identifiable ID in document")

class TinyDB:
    """Implementierung der TinyDB-API auf Basis von JSON1SQLiteStore (v4.8.0-kompatibel)."""
    def __init__(self, path: str, storage=None, **kwargs):
        # Ignoriere storage, da wir SQLite nutzen; passe filename an
        self.store = JSON1SQLiteStore(path, **kwargs)
        self._tables: Dict[str, Table] = {}
        self.Query = Query
        self.table('_default')  # Default-Table

    def table(self, name: str = '_default') -> Table:
        if name not in self._tables:
            self._tables[name] = Table(self.store, name)
        return self._tables[name]

    def tables(self) -> List[str]:
        return list(self._tables.keys())

    def drop_table(self, name: str) -> None:
        if name in self._tables:
            self.table(name).truncate()
            del self._tables[name]

    def drop_tables(self) -> None:
        for name in list(self._tables.keys()):
            self.drop_table(name)

    def close(self) -> None:
        self.store.conn.close()

    # Default-Table-Methoden delegieren
    def insert(self, doc: Dict[str, Any]) -> int:
        return self.table().insert(doc)

    def insert_multiple(self, docs: List[Dict[str, Any]]) -> List[int]:
        return self.table().insert_multiple(docs)

    def all(self) -> List[Dict[str, Any]]:
        return self.table().all()

    def search(self, query: Condition) -> List[Dict[str, Any]]:
        return self.table().search(query)

    def get(self, query: Optional[Condition] = None) -> Optional[Dict[str, Any]]:
        return self.table().get(query)

    def update(self, fields: Dict[str, Any], query: Optional[Condition] = None) -> List[int]:
        return self.table().update(fields, query)

    def remove(self, query: Optional[Condition] = None) -> List[int]:
        return self.table().remove(query)

    def truncate(self) -> None:
        self.table().truncate()

    def count(self, query: Optional[Condition] = None) -> int:
        return self.table().count(query)

    def contains(self, query: Optional[Condition] = None) -> bool:
        return self.table().contains(query)


if __name__ == '__main__':
    # Liste der normalen Indizes (nicht unique)
    index_keys = [
        '!sdata_class',
        '!sdata_name',
        '!sdata_parent',
        '!sdata_project',
        '!sdata_uuid'  # UUID ist unique, aber nach Anfrage nur die zwei spezifizierten als unique
    ]

    # Liste der unique Indizes
    unique_index_keys = [
        '!sdata_sname',
        '!sdata_suuid'
    ]
    #Beispielnutzung (wie TinyDB)
    db = TinyDB('/tmp/sdata.db', index_keys=index_keys, unique_index_keys=unique_index_keys)
    db.insert({'!sdata_name': 'Alice'})
    print(db.search(db.Query()['!sdata_name'] == 'Alice'))
