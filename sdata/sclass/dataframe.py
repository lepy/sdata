import pandas as pd
import io
import os
import base64
import json
from typing import Any, Dict, Optional, Union
import logging

from sdata.metadata import Metadata, Attribute
from sdata.base import Base
from sdata.interactive import ColumnAccessor
from sdata.sclass.content import ContentIntegrityMixin

logger = logging.getLogger(__name__)

#: Spalten-Annotationen, die zusätzlich nativ als Arrow-Field-Metadata mitreisen
#: (tool-agnostisch lesbar, z. B. von DuckDB/Polars), neben dem ``_sdata``-Blob.
_COL_FIELD_KEYS = ("unit", "label", "description", "ontology")


# Die drei ``_h5_*``-Helfer sind ``# pragma: no cover``: sie laufen nur mit
# installiertem h5py (Extra ``sdata[hdf]``), das die kanonische CI nicht mitbringt
# -> die HDF-Tests skippen dort. Verifiziert in Umgebungen mit ``sdata[hdf]``.
def _h5_string_dtype():  # pragma: no cover
    """Variable-length UTF-8 dtype for object/string columns (h5py)."""
    import h5py
    return h5py.string_dtype(encoding="utf-8")


def _h5_encode(values):  # pragma: no cover
    """Encode a 1-D array for h5py, returning ``(data, kind)``.

    Numeric/boolean arrays are stored natively; ``datetime64``/``timedelta64`` are
    stored as int64 nanoseconds (with a ``kind`` tag for lossless restore); anything
    else (object/string/category) is stored as variable-length UTF-8 strings.

    :param values: a numpy array (e.g. ``series.to_numpy()``).
    :return: ``(data, kind)`` where ``kind`` is one of
        ``"num" | "datetime" | "timedelta" | "str"``.
    """
    import numpy as np
    arr = np.asarray(values)
    kind = arr.dtype.kind
    if kind in ("f", "i", "u", "b"):
        return arr, "num"
    if kind == "M":
        return arr.astype("datetime64[ns]").view("i8"), "datetime"
    if kind == "m":
        return arr.astype("timedelta64[ns]").view("i8"), "timedelta"
    out = np.array(
        ["" if (v is None or (isinstance(v, float) and np.isnan(v))) else str(v)
         for v in arr.tolist()],
        dtype=object,
    )
    return out, "str"


def _h5_decode(dataset):  # pragma: no cover
    """Inverse of :func:`_h5_encode` for one h5py dataset (uses its ``kind`` attr)."""
    import numpy as np
    raw = dataset[()]
    kind = dataset.attrs.get("kind", "num")
    if kind == "datetime":
        return pd.to_datetime(np.asarray(raw, dtype="i8"))
    if kind == "timedelta":
        return pd.to_timedelta(np.asarray(raw, dtype="i8"))
    if kind == "str":
        return [v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else v
                for v in raw]
    return raw


def _require_parquet(engine: str = "pyarrow") -> None:
    """Stelle sicher, dass die Parquet-Engine importierbar ist.

    pandas meldet ein fehlendes Backend erst tief im Aufruf; diese Vorabprüfung
    liefert stattdessen eine klare, handlungsorientierte Meldung.

    :param engine: Name des Parquet-Backends (z. B. ``"pyarrow"``).
    :raises ImportError: wenn das Backend nicht installiert ist.
    """
    try:
        __import__(engine)
    except ImportError as exp:
        raise ImportError(
            f"Parquet engine {engine!r} is not available. "
            f"Install it, e.g. `pip install sdata[parquet]`."
        ) from exp


class DataFrame(ContentIntegrityMixin, Base):
    SDATA_CLS = "sdata.sclass.dataframe.DataFrame"

    #: optionales :class:`~sdata.schema.TableSchema`; beim Init angewandt (Default None)
    TABLE_SCHEMA = None


    def __init__(
            self,
            df: Optional[pd.DataFrame] = None,
            column_metadata: Optional[
                Union[Dict[str, Dict[str, str]], Metadata]
            ] = None,
            unit_system=None,
            **kwargs: Any
    ) -> None:
        """
        Initialize a DataFrame with an optional pandas DataFrame and column metadata.

        The pandas DataFrame is kept in memory; serialization to Parquet/dict/JSON-LD
        happens on demand. Per-column annotations (unit/label/description/ontology)
        live in ``column_metadata`` (a :class:`~sdata.metadata.Metadata`).

        :param df: Optional pandas DataFrame to store (default: an empty DataFrame).
        :param column_metadata: Optional per-column metadata, either a dict
          ``{colname: {'label': ..., 'unit': ...}}`` or a :class:`Metadata`. Keys
          that do not match a df column are kept but a warning is logged.
        :param unit_system: optional target :class:`~sdata.units.UnitSystem` (or a
          unit list like ``["kN", "mm", "ms"]``) recorded on the table; see
          :attr:`unit_system` and :meth:`convert`.
        :param kwargs: forwarded to :class:`~sdata.base.Base` (e.g. ``name``,
          ``description``, ``project``).
        """
        super().__init__(**kwargs)

        if isinstance(column_metadata, dict):
            self._column_metadata = Metadata.from_dict(column_metadata)
        elif isinstance(column_metadata, Metadata):
            self._column_metadata = column_metadata.copy()
        else:
            if column_metadata is not None:
                logger.warning("column_metadata type not supported: %s",
                               type(column_metadata).__name__)
            self._column_metadata = Metadata(name="column_metadata")

        self._df = pd.DataFrame()
        self._unit_system = None
        if unit_system is not None:
            self.unit_system = unit_system
        if df is not None:
            # Bei der Konstruktion vom Nutzer gelieferte column_metadata bewahren
            # (kein Prune); Waisen werden nur gemeldet.
            self._assign_df(df, prune=False)
            self._warn_orphan_columns()

        # Optionales Tabellen-Schema anwenden (column_metadata vollqualifizieren)
        if self.TABLE_SCHEMA is not None:
            self.TABLE_SCHEMA.apply(self)

    def _warn_orphan_columns(self):
        """Warne, wenn column_metadata-Schlüssel keiner df-Spalte entsprechen."""
        cols = {str(c) for c in self._df.columns}
        orphans = [k for k in self._column_metadata.keys() if k not in cols]
        if orphans:
            logger.warning("column_metadata keys not in df columns: %s", orphans)

    @property
    def cmd(self):
        return self._column_metadata

    @property
    def cmdf(self):
        return self._column_metadata.to_dataframe()

    def _get_df(self):
        return self._df

    def _set_df(self, df):
        # Zuweisung über die ``df``-Property synchronisiert die column_metadata und
        # entfernt dabei Attribute zu nicht mehr vorhandenen Spalten (prune).
        self._assign_df(df, prune=True)

    def _assign_df(self, df, prune=False):
        if isinstance(df, pd.DataFrame):
            self._df = df
            if self._df.index.name is None:
                self._df.index.name = "index"
            self._sync_column_metadata(prune=prune)

    def _sync_column_metadata(self, prune=False):
        """Halte column_metadata mit den df-Spalten konsistent.

        Ergänzt fehlende Spalten-Attribute (Wert = pandas-dtype-Name) und bewahrt
        dabei vorhandene Annotationen (unit/label/description/ontology), da
        :meth:`~sdata.metadata.Metadata.set_attr` vorhandene Attribute wiederverwendet.

        :param prune: wenn ``True``, werden Attribute zu Spalten entfernt, die nicht
          (mehr) im df vorhanden sind (z. B. nach einer df-Neuzuweisung).
        """
        colnames = [str(c) for c in self._df.columns]
        for col in self._df.columns:
            self._column_metadata.add(name=str(col), value=self._df[col].dtype.name)
        if prune:
            for key in list(self._column_metadata.keys()):
                if key not in colnames:
                    self._column_metadata.pop(key)

    df = property(fget=_get_df, fset=_set_df, doc="df object(pandas.DataFrame)")

    @property
    def content_bytes(self) -> bytes:
        """Binary serialization of the **data** (plain Parquet of the df, *without* the
        embedded sdata metadata).

        The hook the inherited :class:`~sdata.sclass.content.ContentIntegrityMixin`
        hashes over — enables ``sha256``/``md5``/``sha1``, ``size`` and
        ``verify()``/``update_checksum()`` directly on a :class:`DataFrame`. Hashing
        the data only keeps the checksum stable when *metadata* changes (otherwise
        storing the checksum in the metadata would alter the hash).
        """
        return self.df.to_parquet()

    @property
    def column_metadata(self) -> Metadata:
        """
        Retrieve the per-column metadata.

        :return: a :class:`~sdata.metadata.Metadata` holding one attribute per
          column (e.g. ``label``/``unit`` annotations).
        """
        return self._column_metadata

    def get_column(self, name) -> Optional[Attribute]:
        """Return the column :class:`~sdata.metadata.Attribute` for ``name``.

        :param name: column name.
        :return: the column's :class:`Attribute`, or ``None`` if unknown.
        """
        return self._column_metadata.get(str(name))

    def set_column(self, name, *, unit=None, label=None, description=None,
                   ontology=None, required=None, dtype=None) -> Attribute:
        """Annotate a column; writes through to :attr:`column_metadata`.

        Only the provided fields are changed; existing annotations are preserved
        (delegates to :meth:`~sdata.metadata.Metadata.set_attr`). A warning is
        logged if ``name`` is not a column of the current df.

        :param name: column name.
        :param unit: physical unit (e.g. ``"kg"``).
        :param label: human-readable label.
        :param description: free-text description.
        :param ontology: CURIE/IRI of the column's class.
        :param required: whether the column is required.
        :param dtype: declared dtype string.
        :return: the (created or updated) column :class:`Attribute`.
        """
        name = str(name)
        fields = {"unit": unit, "label": label, "description": description,
                  "ontology": ontology, "required": required, "dtype": dtype}
        self._column_metadata.set_attr(
            name, **{k: v for k, v in fields.items() if v is not None})
        if name not in {str(c) for c in self._df.columns}:
            logger.warning("set_column: %r is not a df column", name)
        return self._column_metadata.get(name)

    @property
    def col(self) -> ColumnAccessor:
        """Column-annotation accessor: ``df.col.weight`` / ``df.col['weight']``.

        Returns the column :class:`Attribute`; mutate its fields in place
        (``df.col.weight.unit = 'kg'``) or use :meth:`set_column`.
        """
        return ColumnAccessor(self)

    @property
    def column_units(self) -> Dict[str, str]:
        """Mapping ``{column: unit}`` (in df-column order) from column_metadata."""
        units = {}
        for col in self._df.columns:
            attr = self._column_metadata.get(str(col))
            if attr is not None:
                units[str(col)] = attr.unit
        return units

    @property
    def unit_system(self):
        """The table's target :class:`~sdata.units.UnitSystem` (or ``None``).

        Assign a :class:`~sdata.units.UnitSystem` **or** a unit list (e.g.
        ``["kN", "mm", "ms"]``, wrapped automatically) to record the unit system
        this table should be expressed in; :meth:`convert` with no argument then
        rescales the data into it. Setting only records the target — it does **not**
        mutate the data (call :meth:`convert` to apply), which keeps it robust when
        the system is set before the column units. Assign ``None`` to clear.

        :return: the recorded :class:`~sdata.units.UnitSystem`, or ``None``.
        """
        return self._unit_system

    @unit_system.setter
    def unit_system(self, value):
        from sdata import units as U
        if value is None or isinstance(value, U.UnitSystem):
            self._unit_system = value
        else:
            self._unit_system = U.UnitSystem(value)

    def _converted_copy(self):
        """Tiefe Kopie dieses DataFrame (Daten + Metadaten) für nicht-mutierende Ops."""
        new = self.__class__(df=self._df.copy(deep=True))
        new.metadata = self.metadata.copy()
        new._column_metadata = self._column_metadata.copy()
        new.description = self.description
        new._unit_system = self._unit_system
        return new

    def convert(self, units=None, inplace=False):
        """Convert numeric columns into a target unit system (or explicit units).

        ``units`` may be

        * ``None`` (the default) — use this table's :attr:`unit_system`,
        * a :class:`~sdata.units.UnitSystem`,
        * a list/tuple of base-unit symbols, e.g. ``["kN", "mm", "ms"]`` — wrapped into
          a :class:`~sdata.units.UnitSystem` (a *consistent* system: **derived** units
          such as stress→``GPa``, energy→``J``, velocity→``m/s`` follow from the base
          units via dimensional algebra), or
        * a dict ``{column: target_unit}`` for explicit per-column targets.

        Every column that carries a unit in :attr:`column_metadata` and whose
        **dimension** the system spans has its values rescaled and its ``unit``
        annotation updated to the system's (derived) unit. Columns without a unit,
        dimensionless columns, and dimensions the system does not span are left
        untouched. By default a converted **copy** is returned (data + metadata);
        pass ``inplace=True`` to mutate this DataFrame. When a full unit system (not
        a per-column dict) is applied, the result's :attr:`unit_system` is set to it.

        :param units: target unit system, unit list, or ``{column: unit}`` mapping;
          ``None`` uses :attr:`unit_system`.
        :param inplace: mutate this DataFrame instead of returning a converted copy.
        :return: the converted :class:`DataFrame` (``self`` if ``inplace``).
        :raises ValueError: if ``units`` is ``None`` and no :attr:`unit_system` is set.
        :raises sdata.units.UnitConversionError: on incompatible units in a
          ``{column: unit}`` mapping (e.g. a length column to a force unit).
        """
        from sdata import units as U
        if units is None:
            units = self._unit_system
        if units is None:
            raise ValueError(
                "no unit system: pass units to convert() or set .unit_system")
        sdf = self if inplace else self._converted_copy()
        if isinstance(units, dict):
            sdf._convert_by_mapping(units, U)
        else:
            system = units if isinstance(units, U.UnitSystem) else U.UnitSystem(units)
            sdf._convert_by_system(system)
            sdf._unit_system = system
        return sdf

    def _convert_by_system(self, system):
        """Rechne jede abgedeckte Spalte in die (hergeleitete) System-Einheit um."""
        for col in self._df.columns:
            attr = self._column_metadata.get(str(col))
            current = attr.unit if attr is not None else None
            if not current or current in ("-", ""):
                continue
            result = system.convert_value(self._df[col], current)
            if result is None:                       # Dimension nicht aufgespannt
                continue
            converted, label = result
            if str(label) == str(current):           # bereits in System-Einheit
                continue
            self._df[col] = converted
            self.set_column(str(col), unit=str(label))
            logger.info("convert: %s %s -> %s", col, current, label)

    def _convert_by_mapping(self, mapping, U):
        """Rechne genau die genannten Spalten in die jeweils angegebene Einheit um."""
        for col, target in mapping.items():
            col = str(col)
            attr = self._column_metadata.get(col)
            current = attr.unit if attr is not None else None
            if not current or current in ("-", ""):
                logger.warning("convert: column %r has no unit; skipped", col)
                continue
            if str(target) == str(current):
                continue
            self._df[col] = U.convert(self._df[col], current, target)
            self.set_column(col, unit=str(target))
            logger.info("convert: %s %s -> %s", col, current, target)

    def relabel_units(self, mapping, *, force=False):
        """Set column units **without** rescaling the values (fix mislabeled units).

        Use this when a column's numbers are already in the intended unit but its
        ``unit`` annotation is wrong. Unlike :meth:`convert`, the data is left
        untouched; only the ``unit`` field is overwritten. Mutates **in place** and
        returns a report.

        Relabeling within the same dimension (e.g. ``"N"`` → ``"kN"`` on data already
        in kN) is allowed and logged. A **dimension change** (e.g. force → length) is
        refused unless ``force=True`` — overwriting then logs a warning and is flagged
        in the report.

        :param mapping: ``{column: new_unit}``; columns may have a missing/unknown
          current unit (the pure mislabel-fix case).
        :param force: allow overwriting with a unit of a different dimension.
        :return: a list of records ``{"column", "old", "new", "dimension_changed"}``.
        :raises sdata.units.UnitConversionError: on a dimension change without
          ``force=True``.
        """
        from sdata import units as U
        report = []
        for col, new_unit in mapping.items():
            col = str(col)
            new_unit = str(new_unit)
            attr = self._column_metadata.get(col)
            old = attr.unit if attr is not None else None
            # "-"/"" zählen wie "keine Einheit": ein Label-Set, kein Dimensionswechsel
            old_real = old if old and old not in ("-", "") else None
            old_dim = U.dimension_of(old_real) if old_real else None
            new_dim = U.dimension_of(new_unit)
            dim_changed = (old_dim is not None and new_dim is not None
                           and old_dim != new_dim)
            if dim_changed and not force:
                raise U.UnitConversionError(
                    f"relabel_units: {col!r} {old!r} -> {new_unit!r} changes dimension; "
                    f"pass force=True to override")
            self.set_column(col, unit=new_unit)
            logger.warning("relabel_units: %s %s -> %s%s", col, old, new_unit,
                           " (dimension changed)" if dim_changed else "")
            report.append({"column": col, "old": old, "new": new_unit,
                           "dimension_changed": dim_changed})
        return report

    def validate_table(self, schema=None):
        """Validate the df/column_metadata against a :class:`~sdata.schema.TableSchema`.

        :param schema: a ``TableSchema``; defaults to the class-level
          :attr:`TABLE_SCHEMA`. Without any schema the result is trivially valid.
        :return: a :class:`~sdata.schema.ValidationReport` (truthy if valid).
        """
        from sdata.schema import ValidationReport
        schema = schema or self.TABLE_SCHEMA
        if schema is None:
            return ValidationReport(ok=True)
        return schema.validate(self)

    def __len__(self) -> int:
        """Number of rows of the underlying df."""
        return len(self.df)

    @property
    def shape(self):
        """``(nrows, ncols)`` of the underlying df."""
        return self.df.shape

    @property
    def columns(self):
        """Column index of the underlying df."""
        return self.df.columns

    @property
    def dtypes(self):
        """Per-column dtypes of the underlying df."""
        return self.df.dtypes

    def head(self, n: int = 5) -> pd.DataFrame:
        """First ``n`` rows of the underlying df (delegates to ``pandas.DataFrame.head``)."""
        return self.df.head(n)

    def describe(self, *args, **kwargs) -> pd.DataFrame:
        """Descriptive statistics of the df (delegates to ``pandas.DataFrame.describe``)."""
        return self.df.describe(*args, **kwargs)

    def __repr__(self) -> str:
        return f"({self.__class__.__name__} <{self.sname}> shape={self.df.shape})"

    def to_dict(self, engine: str = "pyarrow") -> Dict[str, Any]:
        """
        Serialize to a dict, embedding the df as base64 Parquet plus column_metadata.

        :param engine: Parquet engine for pandas (default ``"pyarrow"``).
        :return: dict with the :class:`~sdata.base.Base` payload plus
          ``data['parquet_bytes']`` and ``data['column_metadata']``.
        """
        _require_parquet(engine)
        result = super().to_dict()
        bytes_io = io.BytesIO()
        self.df.to_parquet(bytes_io, engine=engine)
        parquet_bytes = bytes_io.getvalue()
        result['data']['parquet_bytes'] = base64.b64encode(parquet_bytes).decode("ascii")
        result['data']['column_metadata'] = self.column_metadata.to_dict()
        return result

    def _ordered_columns(self):
        """Spalten-Attribute in echter df-Spaltenreihenfolge (nicht alphabetisch)."""
        cols = [self.column_metadata.get(str(c)) for c in self.df.columns]
        return [c for c in cols if c is not None]

    def to_jsonld(self, context_mode="inline"):
        """JSON-LD der Metadaten inkl. Spalten-Metadaten (csvw:column)."""
        from sdata import semantic
        return semantic.to_jsonld(self.metadata, context_mode=context_mode,
                                  columns=self._ordered_columns())

    def to_turtle(self):
        """RDF/Turtle inkl. Spalten-Metadaten."""
        from sdata import semantic
        return semantic.rdf_from_doc(self.to_jsonld(), fmt="turtle")

    def write_sidecar(self, path=None, indent=2):
        """Sidecar ``<sname>.meta.jsonld`` inkl. Spalten-Metadaten; gibt den Pfad zurück."""
        from sdata import semantic
        return semantic.write_sidecar_doc(self.to_jsonld(), path, self.sname, indent=indent)

    @classmethod
    def from_dict(cls, d: Dict[str, Any], engine: str = "pyarrow") -> 'DataFrame':
        """
        Reconstruct a DataFrame from a dict produced by :meth:`to_dict`.

        Restores metadata and column_metadata and decodes the df from the
        embedded base64 Parquet payload.

        :param d: dict with ``metadata`` and ``data.{parquet_bytes,column_metadata}``.
        :param engine: Parquet engine for pandas (default ``"pyarrow"``).
        :return: a :class:`DataFrame` instance.
        """
        _require_parquet(engine)
        from sdata.format import ensure_compatible
        d = ensure_compatible(d)                     # RFC 0010: Version prüfen/migrieren
        metadata = Metadata.from_dict(d.get("metadata", {}))
        column_metadata_dict = d['data'].get('column_metadata', {})
        column_metadata = Metadata.from_dict(column_metadata_dict)

        instance = cls()
        instance.metadata = metadata
        instance._column_metadata = column_metadata
        instance.description = d.get("description", "")

        parquet_str = d['data'].get('parquet_bytes', '')
        parquet_bytes = base64.b64decode(parquet_str.encode("ascii"))
        instance.df = pd.read_parquet(io.BytesIO(parquet_bytes), engine=engine)
        return instance

    def to_dataframe(self):
        """Return a copy of the pandas DataFrame with sdata metadata in ``df.attrs``.

        Metadata, column_metadata and description are embedded under the
        ``"_sdata"`` key (same layout as :meth:`to_parquet`), so that a round-trip
        through pandas keeps the annotations discoverable.

        Returns:
            pandas.DataFrame: A copy of the DataFrame with ``attrs['_sdata']`` set.
        """
        df = self.df.copy()
        df.attrs["_sdata"] = {
            "metadata": self.metadata.to_dict(),
            "column_metadata": self.column_metadata.to_dict(),
            "description": self.description,
        }
        return df

    def to_parquet(self, path=None, filename=None, **kwargs):
        """
        Serialize this sdata.DataFrame to Parquet format, embedding metadata.

        This method will copy the internal pandas DataFrame, attach SData metadata
        (dataset‐level metadata, per‐column metadata, and description) to `df.attrs`,
        and then write the result as a Parquet file. If no output path is given,
        it will return the Parquet bytes buffer.

        Args:
            path (str, optional): Directory where the Parquet file will be saved.
                If provided (and `filename` is None), a file named
                `<sname>.spq` is created under this directory.
            filename (str, optional): Exact filename (without full path)
                for the output Parquet file. Defaults is `<sname>.spq`.
            **kwargs: Additional keyword arguments passed to `pandas.DataFrame.to_parquet`,
                e.g.:
                - engine (str): Parquet engine, defaults to "pyarrow".
                - compression (str): Compression codec, defaults to "zstd".

        Returns:
            str or bytes:
                - If `path` (or `filename`) is provided, returns the full file path (str)
                  where the Parquet file was written.
                - Otherwise, returns the in‐memory Parquet representation as bytes.

        Example:
            # Save to disk under /data/output/<sname>.spq with default naming:
            out_fp = sdf.to_parquet(path="/data/output")
            print("Saved to:", out_fp)

            # Get in‐memory Parquet bytes (no file on disk):
            parquet_bytes = sdf.to_parquet()
        """
        engine = kwargs.get("engine", "pyarrow")
        compression = kwargs.get("compression", "zstd")
        sidecar = kwargs.get("sidecar", False)
        _require_parquet(engine)

        df = self.df.copy()
        df.attrs["_sdata"] = {"metadata": self.metadata.to_dict(),
                              "column_metadata": self.column_metadata.to_dict(),
                              "description": self.description}

        if filename is None and path is not None:
            filename = self.sname + ".spq"
            filepath = os.path.join(path, filename)
            df.to_parquet(filepath, engine=engine, compression=compression)
            logger.info(f"DataFrame Parquet saved to {filepath}")
            if sidecar:
                self.write_sidecar(path)
            return filepath
        else:
            return df.to_parquet(engine=engine, compression=compression)

    def _restore_from_attrs(self, attrs):
        """Restore metadata/column_metadata/description from a ``_sdata`` attrs dict.

        :param attrs: the dict stored under ``df.attrs['_sdata']`` (may be ``None``
          or empty, in which case nothing is restored).
        """
        if not attrs:
            return
        from sdata.format import ensure_compatible
        attrs = ensure_compatible(attrs)             # RFC 0010: deckt Parquet/Arrow/Feather ab
        if "metadata" in attrs:
            self.metadata = Metadata.from_dict(attrs["metadata"])
        if "column_metadata" in attrs:
            self._column_metadata = Metadata.from_dict(attrs["column_metadata"])
        if "description" in attrs:
            self.description = attrs.get("description")

    @classmethod
    def from_parquet_bytes(cls, parquet_bytes, engine: str = "pyarrow"):
        """Load a DataFrame from in-memory Parquet bytes.

        :param parquet_bytes: Parquet file content as bytes.
        :param engine: Parquet engine for pandas (default ``"pyarrow"``).
        :return: a :class:`DataFrame` instance.
        """
        _require_parquet(engine)
        buffer = io.BytesIO(parquet_bytes)
        df = pd.read_parquet(buffer, engine=engine)
        tt = cls()
        tt.df = df
        tt._restore_from_attrs(df.attrs.get("_sdata"))
        return tt

    @classmethod
    def from_parquet(cls, filepath, engine: str = "pyarrow"):
        """Load a DataFrame from a Parquet file on disk.

        :param filepath: path to the ``.spq``/Parquet file.
        :param engine: Parquet engine for pandas (default ``"pyarrow"``).
        :return: a :class:`DataFrame` instance.
        :raises FileNotFoundError: if ``filepath`` does not exist.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"no DataFrame parquet file {filepath}")
        _require_parquet(engine)
        df = pd.read_parquet(filepath, engine=engine)
        tt = cls(name=filepath)
        tt.df = df
        logger.info(f"{tt}")
        attrs = df.attrs.get("_sdata")
        tt._restore_from_attrs(attrs)
        if attrs is not None:
            tt.df.attrs.pop("_sdata")
        return tt

    # ------------------------------------------------------------------ CSV
    def to_csv(self, path=None, filename=None, sidecar=False, **kwargs):
        """Serialize the df to CSV (pure pandas, no extra dependency).

        CSV carries data only; the qualifying metadata travels in the optional
        ``<sname>.meta.jsonld`` sidecar. The index is dropped by default
        (override via ``index=True``).

        :param path: directory to write ``<sname>.csv`` into (if given).
        :param filename: exact output filename (defaults to ``<sname>.csv``).
        :param sidecar: also write a JSON-LD metadata sidecar next to the file.
        :param kwargs: forwarded to :meth:`pandas.DataFrame.to_csv`.
        :return: the file path (if written to disk) or the CSV string.
        """
        kwargs.setdefault("index", False)
        if filename is None and path is not None:
            filename = self.sname + ".csv"
        if filename is not None:
            filepath = os.path.join(path, filename) if path else filename
            self.df.to_csv(filepath, **kwargs)
            logger.info(f"DataFrame CSV saved to {filepath}")
            if sidecar:
                # neben die CSV (<stem>.meta.jsonld), damit from_csv ihn findet;
                # beim Default-Dateinamen identisch zu <sname>.meta.jsonld
                self.write_sidecar(self._csv_sidecar_path(filepath))
            return filepath
        return self.df.to_csv(**kwargs)

    @staticmethod
    def _csv_sidecar_path(filepath):
        """Sidecar-Pfad zu einer CSV-Datei: ``<stem>.meta.jsonld`` daneben."""
        return os.path.splitext(filepath)[0] + ".meta.jsonld"

    @classmethod
    def from_csv(cls, filepath, sidecar=True, **kwargs):
        """Load a DataFrame from a CSV file (pure pandas).

        If a ``<stem>.meta.jsonld`` sidecar (written by ``to_csv(sidecar=True)``)
        exists next to the file, its dataset metadata and column annotations
        (unit/label/description) are merged back automatically — pass
        ``sidecar=False`` to load the data only.

        :param filepath: path to the CSV file.
        :param sidecar: consume an adjacent metadata sidecar if present (default True).
        :param kwargs: forwarded to :func:`pandas.read_csv`.
        :return: a :class:`DataFrame` instance.
        :raises FileNotFoundError: if ``filepath`` does not exist.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"no CSV file {filepath}")
        df = pd.read_csv(filepath, **kwargs)
        tt = cls(name=filepath)
        tt.df = df
        if sidecar:
            tt._load_csv_sidecar(cls._csv_sidecar_path(filepath))
        return tt

    def _load_csv_sidecar(self, sidecar_path):
        """Merge metadata from an adjacent ``<stem>.meta.jsonld`` sidecar, if present.

        Dataset-Metadaten kommen über :func:`sdata.semantic.from_jsonld`;
        die ``csvw:column``-Knoten (von :func:`sdata.semantic.column_node`)
        werden hier invertiert (unit aus ``symbol``, label, description).
        ``_sdata_class`` bleibt unangetastet (JSON-LD trägt nur den lokalen
        Klassennamen, nicht die importierbare Spec).
        """
        if not os.path.exists(sidecar_path):
            return
        from sdata import semantic
        try:
            with open(sidecar_path, "r") as fh:
                doc = json.load(fh)
            meta = semantic.from_jsonld(doc)
        except Exception as exp:
            logger.warning(f"CSV sidecar not loadable: {sidecar_path}: {exp}")
            return
        for attr in meta.attributes.values():
            if attr.name == self.SDATA_CLASS:
                continue
            self.metadata.set_attr(
                attr.name, attr.value, dtype=attr.dtype, unit=attr.unit,
                description=attr.description, label=attr.label,
                ontology=attr.ontology, required=attr.required)
        for node in doc.get("columns", []):
            name = node.get("name")
            if not name:
                continue
            self.set_column(
                name,
                unit=node.get("symbol"),
                label=node.get("label"),
                description=node.get("description"))
        logger.debug(f"merged CSV sidecar metadata from {sidecar_path}")

    # ---------------------------------------------------------------- Arrow
    def _field_metadata_for(self, colname):
        """Per-column annotations as an Arrow field-metadata ``bytes->bytes`` dict.

        :param colname: column name.
        :return: ``{b"unit": b"kg", ...}`` for the annotated keys, or ``None`` if the
          column has no (non-default) annotation.
        """
        attr = self._column_metadata.get(str(colname))
        if attr is None:
            return None
        md = {}
        for key in _COL_FIELD_KEYS:
            val = getattr(attr, key, "")
            if val not in (None, "", "-"):
                md[key.encode("utf-8")] = str(val).encode("utf-8")
        return md or None

    def to_arrow(self):
        """Return a :class:`pyarrow.Table` with sdata metadata in the schema.

        The dataset metadata, column_metadata and description are embedded as JSON
        under the ``b"_sdata"`` schema-metadata key. In addition, each column's
        ``unit``/``label``/``description``/``ontology`` are attached **natively** to
        that column's Arrow field metadata, so Arrow-aware tools (DuckDB, Polars,
        pyarrow) can read the per-column annotations without sdata.

        :return: a ``pyarrow.Table``.
        :raises ImportError: if pyarrow is not installed (``pip install sdata[parquet]``).
        """
        _require_parquet("pyarrow")
        import pyarrow as pa
        table = pa.Table.from_pandas(self.df)
        fields = []
        for field in table.schema:
            fmd = self._field_metadata_for(field.name)
            if fmd:
                merged = dict(field.metadata or {})
                merged.update(fmd)
                field = field.with_metadata(merged)
            fields.append(field)
        schema_meta = dict(table.schema.metadata or {})
        schema_meta[b"_sdata"] = json.dumps({
            "metadata": self.metadata.to_dict(),
            "column_metadata": self.column_metadata.to_dict(),
            "description": self.description,
        }).encode("utf-8")
        new_schema = pa.schema(fields, metadata=schema_meta)
        return pa.Table.from_arrays(list(table.columns), schema=new_schema)

    @classmethod
    def from_arrow(cls, table):
        """Build a DataFrame from a :class:`pyarrow.Table` written by :meth:`to_arrow`.

        The ``b"_sdata"`` schema blob is restored if present; per-column Arrow field
        metadata (``unit``/``label``/...) is also merged into ``column_metadata``, so
        tables produced by other Arrow-native tools keep their column annotations.

        :param table: a ``pyarrow.Table`` (sdata metadata restored if present).
        :return: a :class:`DataFrame` instance.
        :raises ImportError: if pyarrow is not installed.
        """
        _require_parquet("pyarrow")
        tt = cls()
        tt.df = table.to_pandas()
        raw = (table.schema.metadata or {}).get(b"_sdata")
        if raw is not None:
            tt._restore_from_attrs(json.loads(raw.decode("utf-8")))
        tt._merge_field_metadata(table.schema)
        return tt

    def _merge_field_metadata(self, schema):
        """Merge per-column Arrow field metadata into ``column_metadata`` (in-place).

        :param schema: a ``pyarrow.Schema``; fields carrying ``unit``/``label``/...
          metadata update the matching column's annotation.
        """
        cols = {str(c) for c in self._df.columns}
        for field in schema:
            if not field.metadata or field.name not in cols:
                continue
            kwargs = {key: field.metadata[key.encode("utf-8")].decode("utf-8")
                      for key in _COL_FIELD_KEYS
                      if key.encode("utf-8") in field.metadata}
            if kwargs:
                self.set_column(field.name, **kwargs)

    # -------------------------------------------------------------- Feather
    def to_feather(self, path=None, filename=None, sidecar=False, **kwargs):
        """Serialize to the Feather (Arrow IPC) format, embedding sdata metadata.

        :param path: directory to write ``<sname>.feather`` into (if given).
        :param filename: exact output filename (defaults to ``<sname>.feather``).
        :param sidecar: also write a JSON-LD metadata sidecar next to the file.
        :param kwargs: forwarded to :func:`pyarrow.feather.write_feather`.
        :return: the file path (if written to disk) or the Feather bytes.
        :raises ImportError: if pyarrow is not installed.
        """
        _require_parquet("pyarrow")
        import pyarrow.feather as feather
        table = self.to_arrow()
        if filename is None and path is not None:
            filename = self.sname + ".feather"
        if filename is not None:
            filepath = os.path.join(path, filename) if path else filename
            feather.write_feather(table, filepath, **kwargs)
            logger.info(f"DataFrame Feather saved to {filepath}")
            if sidecar:
                self.write_sidecar(path)
            return filepath
        sink = io.BytesIO()
        feather.write_feather(table, sink, **kwargs)
        return sink.getvalue()

    @classmethod
    def from_feather(cls, filepath):
        """Load a DataFrame from a Feather file written by :meth:`to_feather`.

        :param filepath: path to the ``.feather`` file.
        :return: a :class:`DataFrame` instance.
        :raises FileNotFoundError: if ``filepath`` does not exist.
        :raises ImportError: if pyarrow is not installed.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"no Feather file {filepath}")
        _require_parquet("pyarrow")
        import pyarrow.feather as feather
        return cls.from_arrow(feather.read_table(filepath))

    # ------------------------------------------- Blob composition (RFC 0004 C)
    #: Serialisierer je ``as_blob``-Format: ``fmt -> (builder, filetype, mime_type)``.
    #: Der Builder bekommt ``self`` und liefert ``bytes``. So wird eine Tabelle in
    #: **einem gewählten Format** zu einem binären Asset (hash-/signier-/übertragbar),
    #: ohne dass ``DataFrame`` von ``Blob`` erben muss (Komposition statt Vererbung).
    _BLOB_FORMATS = {
        "parquet": (lambda self: self.to_parquet(), "parquet",
                    "application/vnd.apache.parquet"),
        "csv": (lambda self: self.to_csv().encode("utf-8"), "csv", "text/csv"),
        "arrow": (lambda self: self.to_feather(), "arrow",
                  "application/vnd.apache.arrow.file"),
        "feather": (lambda self: self.to_feather(), "feather",
                    "application/vnd.apache.arrow.file"),
    }

    def as_blob(self, fmt: str = "parquet", **kwargs):
        """Render the table as a standalone :class:`~sdata.sclass.blob.Blob`.

        The df is serialized once (in the chosen ``fmt``) into a fixed
        ``bytes``-content Blob — a binary snapshot that can be hashed, signed,
        stored or transferred like any other asset. This is **composition**, not
        inheritance: a living, multi-format table is rendered into *one* chosen
        format on demand (RFC 0004, Option C). The Blob's ``checksum`` is filled
        (``update_checksum``), so ``blob.verify()`` works out of the box.

        :param fmt: serialization format — ``"parquet"`` (default), ``"csv"``,
          ``"arrow"`` or ``"feather"``.
        :param kwargs: forwarded to :class:`~sdata.sclass.blob.Blob` (``name`` and
          ``description`` default to this DataFrame's).
        :return: a :class:`~sdata.sclass.blob.Blob` with the serialized bytes.
        :raises ValueError: if ``fmt`` is not a supported format.
        :raises ImportError: if the format needs pyarrow and it is not installed.
        """
        from sdata.sclass.blob import Blob
        key = fmt.lower()
        if key not in self._BLOB_FORMATS:
            raise ValueError(f"unsupported blob format: {fmt!r} "
                             f"({'|'.join(self._BLOB_FORMATS)})")
        build, filetype, mime = self._BLOB_FORMATS[key]
        payload = build(self)
        kwargs.setdefault("name", self.name)
        kwargs.setdefault("description", self.description)
        blob = Blob(content_type="bytes", value=payload, filetype=filetype, **kwargs)
        blob.metadata.set_attr("mime_type", mime)
        blob.update_checksum()
        logger.info(f"DataFrame rendered as {key} Blob <{blob.sname}>")
        return blob

    # --------------------------------------------------------- Data Package
    def _frictionless_type(self, series):
        """Map a pandas dtype to a Frictionless Table Schema type."""
        return {"i": "integer", "u": "integer", "f": "number",
                "b": "boolean", "M": "datetime"}.get(series.dtype.kind, "string")

    def _datapackage_descriptor(self, data_path, fmt):
        """Build a Frictionless ``tabular-data-package`` descriptor.

        Emits standard Frictionless fields (so generic tooling can read it) plus a
        lossless ``"sdata"`` block (full metadata/column_metadata) for a perfect
        round-trip.
        """
        fields = []
        for col in self.df.columns:
            field = {"name": str(col), "type": self._frictionless_type(self.df[col])}
            attr = self.column_metadata.get(str(col))
            if attr is not None:
                if attr.label:
                    field["title"] = attr.label
                if attr.description:
                    field["description"] = attr.description
                if attr.unit not in ("-", "", None):
                    field["unit"] = attr.unit
                if attr.ontology:
                    field["rdfType"] = attr.ontology
            fields.append(field)
        resource = {"name": self.sname.lower(), "path": data_path, "format": fmt,
                    "profile": "tabular-data-resource", "schema": {"fields": fields}}
        return {"name": self.sname.lower(), "title": self.name,
                "description": self.description, "profile": "tabular-data-package",
                "resources": [resource],
                "sdata": {"metadata": self.metadata.to_dict(),
                          "column_metadata": self.column_metadata.to_dict(),
                          "description": self.description}}

    def to_datapackage(self, path=None, filename=None, fmt="csv", sidecar=True):
        """Write a Frictionless **Data Package** (``.zip``) — a portable bundle.

        The zip holds a standard ``datapackage.json`` descriptor (so generic
        Frictionless tooling can read it), the data as CSV or Parquet, and — for a
        lossless sdata round-trip — the full sdata metadata under the descriptor's
        ``"sdata"`` key. Optionally the ``<sname>.meta.jsonld`` JSON-LD sidecar.

        :param path: directory to write ``<sname>.zip`` into (if given).
        :param filename: exact output filename (defaults to ``<sname>.zip``).
        :param fmt: data format inside the package, ``"csv"`` (default) or ``"parquet"``.
        :param sidecar: also embed the JSON-LD sidecar in the zip (default ``True``).
        :return: the file path (if written to disk) or the zip bytes.
        :raises ValueError: if ``fmt`` is not ``"csv"``/``"parquet"``.
        """
        import zipfile
        if fmt == "csv":
            data_path = f"data/{self.sname}.csv"
            data_bytes = self.df.to_csv(index=False).encode("utf-8")
        elif fmt == "parquet":
            data_path = f"data/{self.sname}.spq"
            data_bytes = self.to_parquet()
        else:
            raise ValueError(f"unsupported data package format: {fmt!r} (csv|parquet)")

        descriptor = self._datapackage_descriptor(data_path, fmt)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(data_path, data_bytes)
            zf.writestr("datapackage.json", json.dumps(descriptor, indent=2))
            if sidecar:
                zf.writestr(f"{self.sname}.meta.jsonld",
                            json.dumps(self.to_jsonld(), indent=2))
        payload = buffer.getvalue()

        if filename is None and path is not None:
            filename = self.sname + ".zip"
        if filename is not None:
            filepath = os.path.join(path, filename) if path else filename
            with open(filepath, "wb") as fh:
                fh.write(payload)
            logger.info(f"DataFrame Data Package saved to {filepath}")
            return filepath
        return payload

    @classmethod
    def from_datapackage(cls, filepath):
        """Load a DataFrame from a Data Package ``.zip`` written by :meth:`to_datapackage`.

        Restores the data and — losslessly — metadata/column_metadata/description
        from the descriptor's ``"sdata"`` block.

        :param filepath: path to the ``.zip`` data package.
        :return: a :class:`DataFrame` instance.
        :raises FileNotFoundError: if ``filepath`` does not exist.
        """
        import zipfile
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"no Data Package {filepath}")
        with zipfile.ZipFile(filepath) as zf:
            descriptor = json.loads(zf.read("datapackage.json"))
            resource = descriptor["resources"][0]
            data_path = resource["path"]
            fmt = resource.get("format", "csv")
            data_bytes = zf.read(data_path)

        if fmt == "parquet":
            _require_parquet("pyarrow")
            df = pd.read_parquet(io.BytesIO(data_bytes))
        else:
            df = pd.read_csv(io.BytesIO(data_bytes))

        tt = cls()
        tt.df = df
        tt._restore_from_attrs(descriptor.get("sdata"))
        return tt

    # ------------------------------------------------------------------ HDF5
    # Optionales HDF5-Backend (h5py, Extra ``sdata[hdf]``), siehe RFC 0002.
    # Bewusst ``# pragma: no cover``: h5py ist nicht in der kanonischen CI
    # (installiert nur ``[did,parquet,blob,sql]``), also skippt die frische CI
    # den Pfad. Verifiziert über die ``importorskip("h5py")``-Tests in
    # ``tests/test_sclass_dataframe_hdf.py`` (laufen, sobald ``sdata[hdf]`` da ist).
    def to_hdf(self, path=None, filename=None, key=None, sidecar=False,
               compression=None, **kwargs):  # pragma: no cover
        """Serialize the df to HDF5 (h5py), embedding sdata metadata as group attrs.

        Each column is stored as its own native HDF5 dataset under a group named
        ``key`` (so other HDF5 tools can read the values); the sdata metadata
        (metadata/column_metadata/description) rides along as the group's ``_sdata``
        attribute. HDF5 has no in-memory bytes form, so a ``path``/``filename`` is
        required; several DataFrames can share one file via distinct ``key``.

        :param path: directory to write ``<sname>.h5`` into.
        :param filename: exact output filename (defaults to ``<sname>.h5``).
        :param key: HDF5 group name (default: ``self.sname``); rewritten if present.
        :param sidecar: also write a JSON-LD metadata sidecar next to the file.
        :param compression: h5py dataset compression (e.g. ``"gzip"``); ``None`` = off.
        :param kwargs: legacy PyTables kwargs (``format``/``complevel``/``complib``)
            are accepted for backward compatibility and ignored by the h5py backend.
        :return: the file path.
        :raises ImportError: if h5py is not installed (``pip install sdata[hdf]``).
        :raises ValueError: if neither ``path`` nor ``filename`` is given.
        """
        try:
            import h5py
        except ImportError as exp:
            raise ImportError("HDF5 support requires h5py. Install it, e.g. "
                              "`pip install sdata[hdf]`.") from exp
        for legacy in ("format", "complevel", "complib"):
            if kwargs.pop(legacy, None) is not None:
                logger.debug("to_hdf: PyTables kwarg %r is ignored by the h5py backend",
                             legacy)
        if filename is None and path is not None:
            filename = self.sname + ".h5"
        if filename is None:
            raise ValueError("to_hdf requires a path or filename (HDF5 has no bytes form)")
        filepath = os.path.join(path, filename) if path else filename
        key = key or self.sname
        columns = [str(c) for c in self.df.columns]
        with h5py.File(filepath, "a") as f:
            if key in f:
                del f[key]                       # mode="a" + rewrite same key
            grp = f.create_group(key)
            grp.attrs["_sdata"] = json.dumps({
                "metadata": self.metadata.to_dict(),
                "column_metadata": self.column_metadata.to_dict(),
                "description": self.description,
            })
            grp.attrs["_columns"] = json.dumps(columns)
            idx = self.df.index
            default_index = (isinstance(idx, pd.RangeIndex)
                             and idx.start == 0 and idx.step == 1)
            grp.attrs["_has_index"] = not default_index
            if not default_index:
                data, kind = _h5_encode(idx.to_numpy())
                ds = grp.create_dataset(
                    "_index", data=data,
                    dtype=_h5_string_dtype() if kind == "str" else None)
                ds.attrs["kind"] = kind
                grp.attrs["_index_name"] = "" if idx.name is None else str(idx.name)
            for i, col in enumerate(self.df.columns):
                data, kind = _h5_encode(self.df[col].to_numpy())
                ds = grp.create_dataset(
                    "col_{}".format(i), data=data,
                    dtype=_h5_string_dtype() if kind == "str" else None,
                    compression=compression)
                ds.attrs["kind"] = kind
        logger.info(f"DataFrame HDF5 saved to {filepath}")
        if sidecar:
            self.write_sidecar(path)
        return filepath

    @classmethod
    def from_hdf(cls, filepath, key=None):  # pragma: no cover
        """Load a DataFrame from an HDF5 file written by :meth:`to_hdf`.

        :param filepath: path to the ``.h5`` file.
        :param key: HDF5 group to read (default: the first group in the file).
        :return: a :class:`DataFrame` instance.
        :raises FileNotFoundError: if ``filepath`` does not exist.
        :raises ImportError: if h5py is not installed.
        :raises ValueError: if the file holds no group.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"no HDF5 file {filepath}")
        try:
            import h5py
        except ImportError as exp:
            raise ImportError("HDF5 support requires h5py. Install it, e.g. "
                              "`pip install sdata[hdf]`.") from exp
        with h5py.File(filepath, "r") as f:
            if key is None:
                groups = list(f.keys())
                if not groups:
                    raise ValueError(f"no DataFrame group in {filepath}")
                key = groups[0]
            grp = f[key]
            if "_columns" in grp.attrs:
                columns = json.loads(grp.attrs["_columns"])
                data = {col: _h5_decode(grp["col_{}".format(i)])
                        for i, col in enumerate(columns)}
                df = pd.DataFrame(data, columns=columns)
                if grp.attrs.get("_has_index"):
                    name = grp.attrs.get("_index_name") or None
                    df.index = pd.Index(_h5_decode(grp["_index"]), name=name)
            else:
                df = pd.DataFrame()
            raw = grp.attrs["_sdata"] if "_sdata" in grp.attrs else None
        tt = cls()
        tt.df = df
        tt._restore_from_attrs(json.loads(raw) if raw else None)
        return tt


if __name__ == '__main__':
    # Erstelle einen Pandas DataFrame
    import pandas as pd

    df = pd.DataFrame({
        'weight': [10, 20, 30],
        'height': [1.5, 1.6, 1.7]
    })

    # Erstelle eine DataFrame-Instanz mit Metadaten
    column_meta = {
        'weight': {'label': 'Gewicht', 'unit': 'kg'},
        'height': {'label': 'Höhe', 'unit': 'm'}
    }
    sdf = DataFrame(df=df, column_metadata=column_meta, name="MeinDataFrame", description="Beispieldaten")
