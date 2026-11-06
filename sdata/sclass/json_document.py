# -*- coding: utf-8 -*-
"""JSON-Dokument als eigene sdata-Klasse (RFC 0018).

:class:`JsonDocument` legt einen JSON-Wert (Baum aus Objekten und Listen) direkt in
``data['content']`` ab: ohne base64, ohne ``uri``-Pfad, lesbar im Container.
Prüfsumme und ``verify`` laufen über die kanonische Form :attr:`content_bytes`
(:class:`~sdata.sclass.content.ContentIntegrityMixin`, RFC 0004).
"""
import json
import math
from typing import Any, Optional

from sdata.base import Base
from sdata.format import ensure_compatible
from sdata.metadata import Metadata
from sdata.sclass.content import ContentIntegrityMixin


def _check_json(value: Any) -> None:
    """Prüfe, dass ``value`` ein reiner JSON-Wert ist (iterativ, beliebige Tiefe).

    Erlaubt sind ``dict`` mit ``str``-Schlüsseln, ``list``, ``str``, ``int``,
    ``float`` (endlich), ``bool`` und ``None``. ``json.dumps`` allein genügt nicht:
    es wandelt int-Schlüssel und Tupel still um, sodass der Inhalt nach einer
    Rundreise ein anderer wäre. Die Prüfung nutzt einen expliziten Stack, damit
    tiefe Strukturen kein ``RecursionError`` auslösen.

    :param value: der zu prüfende Wert.
    :raises ValueError: bei NaN/Infinity, Nicht-String-Schlüsseln oder Nicht-JSON-Typen.
    """
    stack = [(value, "$")]
    while stack:
        item, path = stack.pop()
        if item is None or isinstance(item, (str, bool, int)):
            continue
        if isinstance(item, float):
            if not math.isfinite(item):
                raise ValueError(f"JsonDocument: {path}: NaN/Infinity ist kein JSON-Wert")
        elif isinstance(item, list):
            stack.extend((v, f"{path}[{i}]") for i, v in enumerate(item))
        elif isinstance(item, dict):
            for key, v in item.items():
                if not isinstance(key, str):
                    raise ValueError(
                        f"JsonDocument: {path}: Schlüssel {key!r} ist kein str")
                stack.append((v, f"{path}.{key}"))
        else:
            raise ValueError(
                f"JsonDocument: {path}: Typ {type(item).__name__} ist kein JSON-Wert")


class JsonDocument(ContentIntegrityMixin, Base):
    """JSON-Dokument; der Inhalt liegt als JSON-Wert direkt in ``data['content']``.

    Der Inhalt wird **per Referenz** gehalten (keine Kopie). Prüfung beim Setzen
    von :attr:`content` und in :meth:`from_dict`; eine spätere Mutation des
    übergebenen Objekts oder eine Zuweisung an ``data`` umgeht sie. Deshalb
    prüft :attr:`content_bytes` (Hash-Basis) erneut, bevor serialisiert wird.
    """

    SDATA_JSON_FORMAT = "json_format"

    def __init__(self, content: Any = None, *, json_format: Optional[str] = None,
                 **kwargs: Any) -> None:
        """
        :param content: JSON-Wert (dict, list, str, int, float, bool, None).
        :param json_format: optionaler Bezeichner des Inhaltsformats, z. B.
          ``"scale-board/1"``; sdata deutet ihn nicht.
        :param kwargs: an :class:`~sdata.base.Base` weitergereicht (``name`` usw.).
        :raises ValueError: wenn ``content`` kein reiner JSON-Wert ist.
        """
        super().__init__(**kwargs)
        self.content = content
        if json_format is not None:
            self.json_format = json_format

    @property
    def content(self) -> Any:
        """Der JSON-Wert des Dokuments (``None``, solange keiner gesetzt ist)."""
        return self._data.get("content")

    @content.setter
    def content(self, value: Any) -> None:
        _check_json(value)
        self._data["content"] = value

    @property
    def json_format(self) -> Optional[str]:
        """Bezeichner des Inhaltsformats (Metadatenattribut ``json_format``) oder ``None``."""
        attr = self.metadata.get(self.SDATA_JSON_FORMAT)
        return None if attr is None else attr.value

    @json_format.setter
    def json_format(self, value: Optional[str]) -> None:
        if value is None:
            if self.SDATA_JSON_FORMAT in self.metadata:
                self.metadata.pop(self.SDATA_JSON_FORMAT)
            return
        self.metadata.set_attr(
            self.SDATA_JSON_FORMAT, value, dtype="str",
            label="JSON format", description="Schema-Bezeichner des JSON-Inhalts")

    @property
    def content_bytes(self) -> bytes:
        """Kanonische Bytefolge des Inhalts, Hash-Basis (RFC 0004/0018).

        Schlüssel sortiert, ohne Leerraum, UTF-8 (``ensure_ascii=False``): die
        Prüfsumme hängt nur am logischen Inhalt, nicht an Schlüsselreihenfolge
        oder Formatierung.
        """
        content = self.content
        _check_json(content)
        try:
            return json.dumps(content, sort_keys=True, ensure_ascii=False,
                              separators=(",", ":"), allow_nan=False).encode("utf-8")
        except RecursionError as exp:
            raise ValueError("JsonDocument: Inhalt zu tief verschachtelt") from exp

    @classmethod
    def from_dict(cls, d: dict, *, strict: bool = False) -> "JsonDocument":
        """Rekonstruiere ein JsonDocument aus :meth:`to_dict`.

        ``Base.from_dict`` erzeugt nur eine generische Unterklasse von ``Base``
        mit dem Klassennamen; hier entsteht die echte Klasse (Muster
        :class:`~sdata.sclass.dataframe.DataFrame`). Der Inhalt wird wie beim
        Setzen auf reine JSON-Werte geprüft.

        :param d: dict mit ``metadata``, ``data`` und ``description``.
        :param strict: bei neuerer Formatversion hart scheitern (RFC 0010).
        :raises ValueError: wenn ``_sdata_class`` nicht auf dieses JsonDocument zeigt
          oder ``data['content']`` kein reiner JSON-Wert ist.
        """
        d = ensure_compatible(d, strict=strict)      # RFC 0010: Version prüfen/migrieren
        metadata = Metadata.from_dict(d.get("metadata", {}))
        attr = metadata.get(cls.SDATA_CLASS)
        spec = attr.value if attr is not None else None
        allowed = {"sdata.sclass.json_document:JsonDocument",
                   f"{cls.__module__}:{cls.__qualname__}"}
        if spec not in allowed:
            raise ValueError(
                f"JsonDocument.from_dict: _sdata_class {spec!r} ist kein JsonDocument")
        instance = cls()
        instance.metadata = metadata
        data = dict(d.get("data", {}))
        instance.data = data
        instance.content = data.get("content")
        instance.description = d.get("description", "")
        return instance

    def __repr__(self) -> str:
        return f"({self.__class__.__name__} <{self.sname}>)"
