"""Geordnete Sammlung benannter sdata-DataFrames (RFC 0011).

Anders als früher hält die Gruppe ihre Mitglieder als vollwertige
:class:`~sdata.sclass.dataframe.DataFrame` (mit reichem ``Metadata``/
``column_metadata`` — Einheit/Label/Ontologie/dtype, RFC 0006), nicht mehr als
rohe pandas-Frames mit einem ``{label, unit}``-dict. Die öffentliche API
(``add_dataframe``/``get_dataframe``/``get_column_metadata``/…) bleibt
abwärtskompatibel; ``from_dict`` liest **beide** Serialisierungs-Layouts (das alte
``{parquet, column_metadata}`` und das neue ``{sdata: <DataFrame.to_dict>}``).
"""
import base64
import io
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from sdata.base import Base

logger = logging.getLogger(__name__)


class DataFrameGroup(Base):
    """Sammlung benannter :class:`~sdata.sclass.dataframe.DataFrame` (eine flache Ebene).

    Die Mitglieder liegen in ``self.data['dataframes']`` als
    :class:`~sdata.sclass.dataframe.DataFrame`-Objekte; jedes trägt seine volle
    Spaltensemantik selbst (kein separates ``{label, unit}``-dict mehr).
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the group (forwards ``**kwargs`` to :class:`Base`)."""
        super().__init__(**kwargs)
        if 'dataframes' not in self.data:
            self.data['dataframes'] = {}

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _as_dataframe(df, key=None, column_metadata=None):
        """Wrap a pandas ``df`` (or pass a :class:`DataFrame` through) and annotate columns."""
        from sdata.sclass.dataframe import DataFrame
        sdf = df if isinstance(df, DataFrame) else DataFrame(df=df, name=key or "df")
        if column_metadata:
            for col, meta in column_metadata.items():
                sdf.set_column(col, label=meta.get('label'), unit=meta.get('unit'))
        return sdf

    # -------------------------------------------------------------- public API
    def add(self, df, key: Optional[str] = None, overwrite: bool = False):
        """Add a :class:`DataFrame` (or pandas ``df``); returns the stored member.

        :param df: a :class:`~sdata.sclass.dataframe.DataFrame` or a pandas ``DataFrame``.
        :param key: storage key (defaults to the member's ``sname``).
        :param overwrite: allow replacing an existing key.
        :raises ValueError: if the key exists and ``overwrite`` is False.
        """
        sdf = self._as_dataframe(df, key=key)
        key = key or sdf.sname
        if key in self.data['dataframes'] and not overwrite:
            raise ValueError(f"DataFrame with key '{key}' already exists. "
                             "Set overwrite=True to replace.")
        self.data['dataframes'][key] = sdf
        logger.debug("Added DataFrame '%s' to %s", key, self.sname)
        return sdf

    def add_dataframe(
            self,
            key: str,
            df: pd.DataFrame,
            column_metadata: Optional[Dict[str, Dict[str, str]]] = None,
            overwrite: bool = False,
    ) -> None:
        """Add a pandas ``df`` under ``key`` (backward-compatible API).

        :param column_metadata: optional ``{colname: {'label': ..., 'unit': ...}}``;
          if given, must cover **exactly** the df columns and each entry must have
          both ``label`` and ``unit``. The annotations are written through to the
          member's per-column :class:`~sdata.metadata.Metadata`.
        :raises ValueError: on key clash without ``overwrite`` or invalid metadata.
        """
        if key in self.data['dataframes'] and not overwrite:
            raise ValueError(f"DataFrame with key '{key}' already exists. "
                             "Set overwrite=True to replace.")
        if column_metadata is not None:
            if set(column_metadata.keys()) != set(df.columns):
                raise ValueError("column_metadata keys must match the DataFrame's columns exactly.")
            for meta in column_metadata.values():
                if not all(k in meta for k in ['label', 'unit']):
                    raise ValueError("Each column_metadata entry must have 'label' and 'unit' keys.")
        sdf = self._as_dataframe(df, key=key, column_metadata=column_metadata)
        self.data['dataframes'][key] = sdf
        logger.debug("Added DataFrame '%s' to %s", key, self.sname)

    def get(self, key: str):
        """Return the stored :class:`DataFrame` member (or ``None``)."""
        return self.data['dataframes'].get(key)

    def get_dataframe(self, key: str) -> Optional[pd.DataFrame]:
        """Return the member's pandas ``DataFrame`` (backward-compatible), or ``None``."""
        member = self.data['dataframes'].get(key)
        return member.df if member is not None else None

    def get_column_metadata(self, key: str) -> Optional[Dict[str, Dict[str, str]]]:
        """Return ``{colname: {'label': str, 'unit': str}}`` for a member (backward-compatible).

        Derived from the member's per-column :class:`~sdata.metadata.Metadata`.
        """
        member = self.data['dataframes'].get(key)
        if member is None:
            return None
        out: Dict[str, Dict[str, str]] = {}
        for col in member.df.columns:
            attr = member.get_column(str(col))
            out[str(col)] = {
                'label': attr.label if attr is not None else '',
                'unit': attr.unit if attr is not None else '',
            }
        return out

    def remove_dataframe(self, key: str) -> None:
        """Remove a member by key.

        :raises KeyError: if the key does not exist.
        """
        if key not in self.data['dataframes']:
            raise KeyError(f"DataFrame with key '{key}' not found.")
        del self.data['dataframes'][key]
        logger.debug("Removed DataFrame '%s' from %s", key, self.sname)

    def list_dataframes(self) -> List[str]:
        """List all member keys."""
        return list(self.data['dataframes'].keys())

    def items(self):
        """Iterate ``(key, DataFrame)`` over the members (order preserved)."""
        return self.data['dataframes'].items()

    # ------------------------------------------------------------ serialization
    def to_dict(self) -> Dict[str, Any]:
        """Serialize each member via its own lossless :meth:`DataFrame.to_dict`.

        Layout: ``data.dataframes[key] = {'sdata': <DataFrame.to_dict()>}`` — the
        member keeps its full metadata/column_metadata (RFC 0011, no lossy
        ``{label, unit}`` reduction).
        """
        data_copy = dict(self.data)
        data_copy['dataframes'] = {
            key: {'sdata': member.to_dict()}
            for key, member in self.data['dataframes'].items()
        }
        result = super().to_dict()
        result['data'] = data_copy
        return result

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'DataFrameGroup':
        """Reconstruct a group, reading **both** the new and the legacy layout.

        * new: ``{'sdata': <DataFrame.to_dict>}`` → :meth:`DataFrame.from_dict`;
        * legacy: ``{'parquet': <b64>, 'column_metadata': {col: {label, unit}}}``
          → decode the Parquet payload and lift the flat ``{label, unit}`` dict onto
          the member's per-column metadata.
        """
        from sdata.sclass.dataframe import DataFrame
        from sdata.format import ensure_compatible
        from sdata.metadata import Metadata
        # cls() statt super().from_dict: Base.from_dict baut über sdata_factory eine
        # dynamische Klasse ohne die Group-Methoden (wie DataFrame.from_dict).
        d = ensure_compatible(d)                                   # RFC 0010: Version prüfen
        instance = cls()
        instance.metadata = Metadata.from_dict(d.get("metadata", {}))
        instance.description = d.get("description", "")
        raw = dict(d.get("data", {}))
        members: Dict[str, Any] = {}
        for key, entry in raw.get('dataframes', {}).items():
            if isinstance(entry, dict) and 'sdata' in entry:
                members[key] = DataFrame.from_dict(entry['sdata'])
            elif isinstance(entry, dict) and 'parquet' in entry:   # Legacy-Layout
                df = pd.read_parquet(io.BytesIO(base64.b64decode(entry['parquet'])),
                                     engine='pyarrow')
                members[key] = cls._as_dataframe(
                    df, key=key, column_metadata=entry.get('column_metadata'))
            else:                                                   # bereits DataFrame
                members[key] = entry
        raw['dataframes'] = members
        instance.data = raw
        return instance
