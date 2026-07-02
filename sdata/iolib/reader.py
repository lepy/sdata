"""Einheitliche Reader-/Source-Abstraktion für :class:`sdata.sclass.dataframe.DataFrame`.

RFC 0009 — das symmetrische Gegenstück zu :mod:`sdata.iolib.writer` (RFC 0007).
Ein gemeinsamer ``read()``-Vertrag, unter dem Quellen (Parquet-Datei/Objektspeicher,
JSON1-SQLite-Store, relationales SQL) austauschbar sind; die ``require_*``-Prüfung
aus dem Writer dient hier als **Eingangs**-Validierung einer Pipeline.

Konkrete Reader:

* :class:`ParquetReader` — eine fsspec-URI, ein Objekt (``_sdata`` reist im Format mit).
* :class:`StoreReader`   — Selektor-Zugriff (``suuid``/``sname``/Record-ID) und Iteration
  über einen :class:`~sdata.iolib.json1sqlitestore.JSON1SQLiteStore`.
* :class:`SqlReader`     — verlustfreier Snapshot aus der ``sdata_dataframe_meta``-Tabelle
  des :class:`~sdata.iolib.writer.SqlWriter`; ``fresh=True`` liest zusätzlich den
  **aktuellen** Stand der Datentabelle.

``read()`` gibt das :class:`DataFrame` selbst zurück — kein ``ReadReceipt``-Pendant:
das Objekt trägt Identität (``suuid``/``sname``) und Provenienz bereits in seinen
Metadaten (RFC 0009 §8).
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Iterator, Protocol, Tuple, runtime_checkable, TYPE_CHECKING

import pandas as pd

from sdata.iolib.writer import check_contract, _safe_identifier, _SQL_META_TABLE

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from sdata.sclass.dataframe import DataFrame

__all__ = [
    "DataFrameReader",
    "BaseDataFrameReader",
    "ParquetReader",
    "StoreReader",
    "SqlReader",
    "read_group",
]

#: Jüngste Metazeile zu einem Selektor (suuid **oder** sname); Literal-SQL mit
#: qmark-Parametern — keine Identifier-Interpolation (wie im Writer, RFC 0007 C1).
_SQL_META_SELECT = (
    "SELECT target_table, sdata FROM sdata_dataframe_meta "
    "WHERE suuid = ? OR sname = ? ORDER BY rowid DESC LIMIT 1"
)


def read_group(reader: "DataFrameReader", keys, *, name: str = "group"):
    """Mehrere Mitglieder aus **einer** Quelle zu einer
    :class:`~sdata.sclass.dataframegroup.DataFrameGroup` zusammenführen (RFC 0011).

    :param reader: eine beliebige :class:`DataFrameReader`-Quelle.
    :param keys: Iterable von Selektoren (suuid/sname/…), je einer pro Mitglied.
    :param name: Name der erzeugten Gruppe.
    :return: eine ``DataFrameGroup`` mit den gelesenen Mitgliedern (Schlüssel = Selektor).
    """
    from sdata.sclass.dataframegroup import DataFrameGroup
    group = DataFrameGroup(name=name)
    with reader:
        for key in keys:
            group.add(reader.read(key), key=str(key), overwrite=True)
    return group


@runtime_checkable
class DataFrameReader(Protocol):
    """Struktureller Vertrag jeder Quelle."""

    def read(self, selector: Any = None) -> "DataFrame":
        ...

    def close(self) -> None:
        ...


class BaseDataFrameReader(ABC):
    """Template-Method: vom Backend lesen, dann den Eingangsvertrag prüfen."""

    def __init__(self,
                 require_metadata: Tuple[str, ...] = (),
                 require_columns: Tuple[str, ...] = (),
                 require_units: Tuple[str, ...] = ()):
        """Store the require_* contract (Pflichtschlüssel/-spalten/-einheiten)."""
        self.require_metadata = tuple(require_metadata)
        self.require_columns = tuple(require_columns)
        self.require_units = tuple(require_units)
        self._count = 0

    def read(self, selector: Any = None) -> "DataFrame":
        sdf = self._read_impl(selector)
        check_contract(sdf, self.require_metadata, self.require_columns,
                       self.require_units, role="reader")
        self._count += 1
        logger.info("%s read %r", type(self).__name__, sdf.sname)
        return sdf

    @abstractmethod
    def _read_impl(self, selector: Any) -> "DataFrame":
        ...

    def close(self) -> None:
        """Release resources (default: no-op)."""

    def __enter__(self) -> "BaseDataFrameReader":
        """Enter the context manager (returns self)."""
        return self

    def __exit__(self, *exc: Any) -> None:
        """Exit the context manager, closing the reader."""
        self.close()


class ParquetReader(BaseDataFrameReader):
    """Liest **eine** Parquet-URI (fsspec: lokal, ``s3://``, …) als :class:`DataFrame`.

    Die Metadaten reisen im Format mit (``_sdata``-Schema-Key, RFC 0007 §6.1);
    :meth:`DataFrame.from_parquet_bytes` restauriert ``metadata``/``column_metadata``/
    ``description``.
    """

    def __init__(self, uri: str, **contract: Any):
        """Bind the source fsspec ``uri`` and the require_* contract."""
        super().__init__(**contract)
        self.uri = uri

    def _read_impl(self, selector: Any) -> "DataFrame":
        if selector is not None:
            raise ValueError(
                "ParquetReader reads exactly one URI; selector is not supported")
        from sdata.sclass.blob import fsspec
        from sdata.sclass.dataframe import DataFrame

        if fsspec is None:  # pragma: no cover - optionale Abhängigkeit
            raise ImportError("ParquetReader requires: pip install sdata[blob]")
        with fsspec.open(self.uri, "rb") as fh:
            return DataFrame.from_parquet_bytes(fh.read())


class StoreReader(BaseDataFrameReader):
    """Selektor-Zugriff und Iteration über einen :class:`JSON1SQLiteStore`.

    Invertiert den Flatten-Adapter des :class:`~sdata.iolib.writer.StoreWriter`
    (RFC 0007 §6.2): die ``_sdata_*``-Spalten machen den Record auffindbar, das
    verlustfreie ``to_dict`` unter ``"sdata"`` stellt das Objekt wieder her.
    """

    def __init__(self, target: Any, **contract: Any):
        """Bind a store: an existing ``JSON1SQLiteStore`` (not owned) or a DB path (owned)."""
        super().__init__(**contract)
        from sdata.iolib.json1sqlitestore import JSON1SQLiteStore

        if hasattr(target, "get_id_by_key"):
            self._store = target
            self._owns = False
        else:
            self._store = JSON1SQLiteStore(target)
            self._owns = True

    def _read_impl(self, selector: Any) -> "DataFrame":
        from sdata.sclass.dataframe import DataFrame

        row = self._resolve(selector)
        if row is None or "sdata" not in row:
            raise KeyError(f"no DataFrame record for selector {selector!r}")
        return DataFrame.from_dict(row["sdata"])

    def _resolve(self, selector: Any):
        """Dokumentiert deterministisch: ``int`` → Record-ID, sonst suuid, dann sname."""
        if isinstance(selector, int):
            return self._store.get(selector)
        sel = str(selector)  # SUUID-Objekte -> str (RFC 0007 F4)
        rid = (self._store.get_id_by_key("_sdata_suuid", sel)
               or self._store.get_id_by_key("_sdata_sname", sel))
        return self._store.get(rid) if rid is not None else None

    def iter(self) -> Iterator["DataFrame"]:
        """Alle DataFrame-Records des Stores; Records ohne ``"sdata"``-Payload
        (Fremdobjekte) werden übersprungen."""
        from sdata.sclass.dataframe import DataFrame

        for row in self._store.fetch_all():
            if isinstance(row, dict) and "sdata" in row:
                yield DataFrame.from_dict(row["sdata"])

    def close(self) -> None:
        """If this reader owns the store, close its connection."""
        if self._owns:
            self._store.conn.close()


class SqlReader(BaseDataFrameReader):
    """Rekonstruiert ein :class:`DataFrame` aus der ``sdata_dataframe_meta``-Tabelle.

    * ``fresh=False`` (Default): Daten **und** Metadaten aus dem ``sdata``-JSON der
      Metazeile — der verlustfreie **Snapshot zum Schreibzeitpunkt** (inkl. Einheiten/
      Ontologie, die ``to_sql`` selbst verliert).
    * ``fresh=True``: Metadaten aus dem Snapshot, Datenzeilen per ``read_sql`` aus
      ``target_table`` — der **aktuelle** Tabellenstand (bei ``if_exists="append"``
      kumulativ über mehrere Schreibvorgänge; Provenienz pro Zeile: ``suuid``-Spalte,
      RFC 0007 §6.2). Der Tabellenname läuft durch dieselbe Allowlist wie im Writer.
    """

    def __init__(self, conn: Any, *, fresh: bool = False, **contract: Any):
        """Bind a DBAPI/PEP-249 connection (oder ``engine.raw_connection()``)."""
        super().__init__(**contract)
        self._conn = conn
        self.fresh = fresh
        self.meta_table = _SQL_META_TABLE

    def _read_impl(self, selector: Any) -> "DataFrame":
        from sdata.sclass.dataframe import DataFrame

        sel = str(selector)
        row = self._conn.execute(_SQL_META_SELECT, (sel, sel)).fetchone()
        if row is None:
            raise KeyError(f"no entry in {self.meta_table} for selector {selector!r}")
        target_table, sdata_json = row[0], row[1]
        sdf = DataFrame.from_dict(json.loads(sdata_json))
        if self.fresh:
            table = _safe_identifier(target_table)
            # Identifier ist Allowlist-validiert (RFC 0009 §5.3); Parameter-Binding
            # für Identifier existiert in SQL nicht.
            query = "SELECT * FROM " + table  # nosec B608
            sdf.df = pd.read_sql_query(query, self._conn)
        return sdf
