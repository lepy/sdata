"""Einheitliche Writer-/Sink-Abstraktion für :class:`sdata.sclass.dataframe.DataFrame`.

RFC 0007. Ein gemeinsamer ``write()``-Vertrag, unter dem Backends (Parquet-Datei/
Objektspeicher, JSON1-SQLite-Store, relationales SQL, Knowledge Graph) austauschbar
sind. Die Wahrheitsquelle der Metadaten ist **nicht** ``df.attrs`` (das pandas über
``groupby``/``concat``/``merge`` meist verwirft), sondern die erstklassigen Felder
``DataFrame.metadata`` und ``DataFrame.column_metadata``; der Writer *platziert* die
Metadaten nur backend-gerecht.

Konkrete Writer:

* :class:`ParquetWriter` — Parquet-Bytes (mit eingebettetem ``_sdata``) an eine fsspec-URI.
* :class:`StoreWriter`   — sdata-Objekt in einen :class:`~sdata.iolib.json1sqlitestore.JSON1SQLiteStore`
  (Dokument-/Objekt-Persistenz; über die ``_sdata_*``-Spalten indiziert/auffindbar).
* :class:`SqlWriter`     — flache Daten in eine relationale Tabelle + Sidecar-Metadatentabelle,
  atomar (eine Transaktion, per ``flush``/``close`` committet).
* :class:`GraphWriter`   — RDF/Turtle bzw. JSON-LD (QUDT + PROV-O + CSVW); optional
  Named-Graph-Akkumulation über ``rdflib``.
"""
from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol, Tuple, runtime_checkable, TYPE_CHECKING

import pandas as pd

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from sdata.sclass.dataframe import DataFrame

__all__ = [
    "WriteReceipt",
    "DataFrameWriter",
    "BaseDataFrameWriter",
    "ParquetWriter",
    "StoreWriter",
    "SqlWriter",
    "GraphWriter",
    "ensure_sdata",
    "write_with_provenance",
]

#: Feste Metadatentabelle des :class:`SqlWriter` — als **Literal** in statischem SQL
#: verwendet (keine Identifier-Interpolation → keine SQL-Injection-Fläche). Welche
#: Datentabelle eine Zeile beschreibt, steht in der Spalte ``target_table``.
_SQL_META_TABLE = "sdata_dataframe_meta"
_SQL_META_DDL = (
    "CREATE TABLE IF NOT EXISTS sdata_dataframe_meta "
    "(suuid TEXT, sname TEXT, target_table TEXT, sdata TEXT)"
)
_SQL_META_INSERT = (
    "INSERT INTO sdata_dataframe_meta(suuid, sname, target_table, sdata) "
    "VALUES (?, ?, ?, ?)"
)
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(name: str) -> str:
    """Validate a SQL table identifier (allowlist) and return it unchanged.

    :raises ValueError: if ``name`` is not a plain ``[A-Za-z_][A-Za-z0-9_]*`` token.
    """
    if not isinstance(name, str) or not _IDENTIFIER_RE.match(name):
        raise ValueError(f"invalid SQL table identifier: {name!r}")
    return name


@dataclass
class WriteReceipt:
    """Einheitliches Ergebnis eines ``write()`` — macht Senken polymorph austauschbar.

    :param backend: Kurzname der Senke (``"parquet"``/``"store"``/``"sql"``/``"graph"``).
    :param sname: S3-sicherer Name der geschriebenen Tabelle.
    :param suuid: stabile ID der geschriebenen Tabelle (als ``str``).
    :param target: das Ziel (URI/Pfad/Tabellenname/Record-ID/Graph-IRI).
    :param detail: backend-spezifische Zusatzangaben.
    """

    backend: str
    sname: str
    suuid: str
    target: Any = None
    detail: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class DataFrameWriter(Protocol):
    """Struktureller Vertrag jeder Senke."""

    def write(self, sdf: "DataFrame") -> WriteReceipt:
        ...

    def flush(self) -> None:
        ...

    def close(self) -> None:
        ...


def ensure_sdata(obj: Any) -> "DataFrame":
    """Bridge: akzeptiert eine sdata-:class:`DataFrame` **oder** eine reine pandas-``df``.

    Bei einer pandas-``df`` wird ``df.attrs['_sdata']`` (der von
    :meth:`DataFrame.to_parquet`/``to_dataframe`` beschriebene „letzte-Meile"-Slot)
    über den vorhandenen ``_restore_from_attrs``-Pfad restauriert.

    :raises TypeError: bei einem anderen Typ.
    """
    from sdata.sclass.dataframe import DataFrame

    if isinstance(obj, DataFrame):
        return obj
    if isinstance(obj, pd.DataFrame):
        sdf = DataFrame(df=obj)
        sdf._restore_from_attrs(obj.attrs.get("_sdata"))
        return sdf
    raise TypeError(f"expected DataFrame or pandas.DataFrame, not {type(obj)!r}")


def write_with_provenance(writer: "DataFrameWriter", obj: Any,
                          provenance: Dict[str, Any]) -> WriteReceipt:
    """Provenienz **explizit** zum Schreibzeitpunkt in die Wahrheitsquelle injizieren.

    Robuster als auf ``df.attrs``-Propagierung zu hoffen: die Werte landen in
    ``sdf.metadata`` (nicht in ``df.attrs``) und damit dort, wo jeder Writer sie liest.
    """
    sdf = ensure_sdata(obj)
    for key, value in provenance.items():
        sdf.metadata.add(key, value)
    return writer.write(sdf)


class BaseDataFrameWriter(ABC):
    """Template-Method: Vertrag prüfen, Metadaten trennen, an das Backend delegieren."""

    def __init__(self,
                 require_metadata: Tuple[str, ...] = (),
                 require_columns: Tuple[str, ...] = (),
                 require_units: Tuple[str, ...] = ()):
        """Store the require_* contract (Pflichtschlüssel/-spalten/-einheiten)."""
        self.require_metadata = tuple(require_metadata)
        self.require_columns = tuple(require_columns)
        self.require_units = tuple(require_units)
        self._count = 0

    def write(self, sdf: "DataFrame") -> WriteReceipt:
        sdf = ensure_sdata(sdf)
        self._check_contract(sdf)
        meta = {
            "metadata": sdf.metadata.to_dict(),
            "column_metadata": sdf.column_metadata.to_dict(),
            "description": sdf.description,
        }
        receipt = self._write_impl(sdf, meta)
        self._count += 1
        logger.info("%s wrote %r -> %s", type(self).__name__, sdf.sname, receipt.target)
        return receipt

    @staticmethod
    def _absent(required: Tuple[str, ...], present) -> list:
        """Return the required keys for which ``present(key)`` is falsy."""
        return [key for key in required if not present(key)]

    def _check_contract(self, sdf: "DataFrame") -> None:
        """Raise ``ValueError`` if the require_* contract is not met."""
        units = sdf.column_units
        missing = {
            "metadata": self._absent(self.require_metadata,
                                     lambda k: sdf.metadata.get(k) is not None),
            "columns": self._absent(self.require_columns,
                                    lambda c: c in sdf.df.columns),
            "units": self._absent(self.require_units,
                                  lambda c: bool(units.get(c))),
        }
        if any(missing.values()):
            detail = ", ".join(f"{k}={v}" for k, v in missing.items())
            raise ValueError(f"writer contract violated: {detail}")

    @abstractmethod
    def _write_impl(self, sdf: "DataFrame", meta: Dict[str, Any]) -> WriteReceipt:
        ...

    def flush(self) -> None:
        """No-op by default; stateful sinks override to commit."""

    def close(self) -> None:
        """Flush and release resources (default: flush only)."""
        self.flush()

    def __enter__(self) -> "BaseDataFrameWriter":
        """Enter the context manager (returns self)."""
        return self

    def __exit__(self, *exc: Any) -> None:
        """Exit the context manager, closing the writer."""
        self.close()


class ParquetWriter(BaseDataFrameWriter):
    """Schreibt Parquet-Bytes (mit eingebettetem ``_sdata``) an eine fsspec-URI.

    Die Metadaten reisen **im** Format mit — kein Sidecar nötig (RFC 0007 §6.1).
    """

    def __init__(self, uri: str, **contract: Any):
        """Bind the destination fsspec ``uri`` and the require_* contract."""
        super().__init__(**contract)
        self.uri = uri

    def _write_impl(self, sdf: "DataFrame", meta: Dict[str, Any]) -> WriteReceipt:
        blob = sdf.as_blob("parquet")   # to_parquet()-Bytes: _sdata eingebettet
        target = blob.write(self.uri)   # fsspec (lokal, s3://, …)
        return WriteReceipt("parquet", sdf.sname, str(sdf.suuid), target,
                            {"bytes": blob.size})


class StoreWriter(BaseDataFrameWriter):
    """Persistiert das ganze sdata-Objekt in einen :class:`JSON1SQLiteStore`.

    Das Payload wird so **abgeflacht**, dass die ``_sdata_*``-Felder auf der obersten
    Ebene liegen (die der Store als generierte Spalten indiziert) und das verlustfreie
    :meth:`DataFrame.to_dict` unter dem Schlüssel ``"sdata"`` mitreist. Dadurch ist das
    Objekt per ``sname``/``suuid`` auffindbar (RFC 0007 §6.2, behebt den
    ``to_dict()``↔Store-Shape-Mismatch).
    """

    def __init__(self, target: Any, **contract: Any):
        """Bind a store: an existing ``JSON1SQLiteStore`` (not owned) or a DB path (owned)."""
        super().__init__(**contract)
        from sdata.iolib.json1sqlitestore import JSON1SQLiteStore

        if hasattr(target, "insert"):
            self._store = target
            self._owns = False
        else:
            self._store = JSON1SQLiteStore(target)
            self._owns = True

    @staticmethod
    def store_payload(sdf: "DataFrame") -> Dict[str, Any]:
        """Flaches Store-Payload: ``_sdata_*`` top-level + volles ``to_dict`` unter ``sdata``."""
        from sdata.iolib.json1sqlitestore import JSON1SQLiteStore

        md = sdf.metadata
        payload: Dict[str, Any] = {}
        for col in JSON1SQLiteStore.GENERATED_COLUMNS:
            attr = md.get(col)
            payload[col] = None if attr is None else attr.value
        # verbindliche Overrides aus den Objekt-Properties (immer gesetzt)
        payload["_sdata_name"] = sdf.name
        payload["_sdata_sname"] = sdf.sname
        payload["_sdata_suuid"] = str(sdf.suuid)
        payload["sdata"] = sdf.to_dict()
        return payload

    def _write_impl(self, sdf: "DataFrame", meta: Dict[str, Any]) -> WriteReceipt:
        rid = self._store.insert(self.store_payload(sdf))
        return WriteReceipt("store", sdf.sname, str(sdf.suuid), rid,
                            {"record_id": rid})

    def close(self) -> None:
        """Flush and, if this writer owns the store, close its connection."""
        self.flush()
        if self._owns:
            self._store.conn.close()


class SqlWriter(BaseDataFrameWriter):
    """Flache Daten in eine relationale Tabelle + gemeinsame Metadatentabelle, atomar.

    Die Metadaten gehen in die **feste** Tabelle ``sdata_dataframe_meta``
    (:data:`_SQL_META_TABLE`), deren Spalte ``target_table`` die zugehörige Datentabelle
    benennt. Das SQL der Metatabelle ist ein **Literal** (keine Identifier-Interpolation
    → keine SQL-Injection-Fläche); der Datentabellenname wird gegen eine Allowlist
    validiert und über ``pandas.to_sql`` (parametrisiert/gequotet) geschrieben. Meta-Insert
    und ``to_sql`` liegen in **einer** Transaktion; bei Fehler verwirft ``rollback`` die
    pending Metazeile (RFC 0007 §6.2, F3/F4).
    """

    def __init__(self, conn: Any, table: str = "dataframe", *,
                 if_exists: str = "append", **contract: Any):
        """Bind a DBAPI/PEP-249 connection and ensure the shared meta table exists.

        :param conn: sqlite3-/DBAPI-Verbindung (oder ``engine.raw_connection()``).
        :param table: Zieltabelle für die flachen Daten (Allowlist-validiert).
        :param if_exists: an ``pandas.to_sql`` durchgereicht (``append``/``replace``/``fail``).
        """
        super().__init__(**contract)
        self._conn = conn
        self.table = _safe_identifier(table)
        self.meta_table = _SQL_META_TABLE
        self.if_exists = if_exists
        self._conn.execute(_SQL_META_DDL)

    def _write_impl(self, sdf: "DataFrame", meta: Dict[str, Any]) -> WriteReceipt:
        suuid = str(sdf.suuid)
        # Atomar: erst die Metadaten (pending), dann ``to_sql`` — dessen abschließender
        # commit schreibt BEIDE fest. Bei einem Fehler in einem der Schritte verwirft
        # das ``rollback`` die noch nicht committete Metadatenzeile (kein Waise, F3).
        try:
            self._conn.execute(
                _SQL_META_INSERT,
                (suuid, sdf.sname, self.table, json.dumps(sdf.to_dict(), default=str)))
            sdf.df.to_sql(self.table, self._conn, if_exists=self.if_exists, index=False)
        except Exception:
            self._conn.rollback()
            raise
        return WriteReceipt("sql", sdf.sname, suuid, self.table,
                            {"meta_table": self.meta_table})

    def flush(self) -> None:
        """Commit the connection (transaction boundary for data + meta)."""
        self._conn.commit()


class GraphWriter(BaseDataFrameWriter):
    """RDF/Turtle bzw. JSON-LD der Metadaten (QUDT + PROV-O + CSVW).

    Einzeldatei-Modus schreibt **tatsächlich** nach ``target`` (RFC 0007 §6.3, F2).
    ``named_graphs=True`` akkumuliert mehrere Tabellen als Named Graphs in einem
    ``rdflib.Dataset`` (Graph-IRI aus ``suuid``) und serialisiert bei :meth:`close`.
    """

    def __init__(self, target: Optional[str] = None, *, fmt: str = "turtle",
                 named_graphs: bool = False, **contract: Any):
        """Configure the RDF target file, serialization ``fmt`` and named-graph mode."""
        super().__init__(**contract)
        self.target = target
        self.fmt = fmt
        self._dataset = None
        if named_graphs:
            from sdata.semantic import _rdflib

            if _rdflib is None:
                raise ImportError("named_graphs requires: pip install sdata[rdf]")
            self._dataset = _rdflib.Dataset()  # pragma: no cover

    def _write_impl(self, sdf: "DataFrame", meta: Dict[str, Any]) -> WriteReceipt:
        suuid = str(sdf.suuid)
        if self._dataset is not None:  # pragma: no cover  (rdflib nicht in kanonischer CI)
            from sdata.semantic import _rdflib

            iri = _rdflib.URIRef(f"urn:sdata:{suuid}")
            self._dataset.graph(iri).parse(
                data=json.dumps(sdf.to_jsonld()), format="json-ld")
            return WriteReceipt("graph", sdf.sname, suuid, str(iri),
                                {"named_graph": True})
        if self.fmt == "json-ld":
            text = json.dumps(sdf.to_jsonld(), indent=2)
        else:
            text = sdf.to_turtle()
        if self.target is not None:
            with open(self.target, "w", encoding="utf-8") as fh:
                fh.write(text)
        return WriteReceipt("graph", sdf.sname, suuid, self.target,
                            {"text": text})

    def close(self) -> None:
        """Serialize the accumulated named-graph dataset to ``target`` (if any)."""
        if self._dataset is not None and self.target:  # pragma: no cover
            self._dataset.serialize(destination=self.target, format="nquads")
