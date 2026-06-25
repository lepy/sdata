"""sdata.suuid — Adapter auf das eigenständige ``suuid``-Package.

Ab jetzt ist **``suuid``** (``pip install "suuid>=0.2.0"``) die Single Source of
Truth für semantische, S3-sichere IDs der Form ``Class__safe_name__huuid``.
Dieses Modul ist ein dünner Rückwärtskompatibilitäts-Adapter: es bildet die
historisch in sdata genutzte SUUID-API auf das ``suuid``-Package ab.

Mapping (sdata → suuid):
  ``suuid_str`` / ``suuid_bytes``        → :attr:`suuid.SUUID.compact_token`
  ``uuid`` / ``get_uuid()``              → :meth:`suuid.SUUID.as_uuid`
  ``from_name(ns_name=…)``               → :meth:`suuid.SUUID.from_name` (``ns=…``)
  ``from_suuid_sname(strict=False)``     → :meth:`suuid.SUUID.from_sname`
  ``from_suuid_str`` / ``from_suuid_bytes`` → :meth:`suuid.SUUID.from_compact_token`
  ``generate_safe_filename``             → :func:`suuid.safe_name`

Damit gilt durchgängig die in ``suuid`` eingefrorene, 100% S3-sichere
Normalisierung (kein führendes ``_``, kein ``@``, ``sname`` ∈ ``[A-Za-z0-9_]``).
"""
from __future__ import annotations

import uuid as _uuid
from typing import Optional

from suuid import SUUID as _SUUID, OID_NAMESPACE, safe_name  # noqa: F401
from suuid.core import clean_class_name

__all__ = ["SUUID"]


class SUUID(_SUUID):
    """sdata-Adapter um :class:`suuid.SUUID` mit Kompatibilitäts-Aliassen.

    Erbt Immutabilität, Wertgleichheit und die S3-sichere Normalisierung von
    :class:`suuid.SUUID`; ergänzt nur die in sdata genutzten Alias-Namen.
    """

    #: Separator (Kompat-Konstante; identisch zu ``suuid`` ``SEP``).
    SEP = "__"

    # --- Property-Aliasse ------------------------------------------------
    @property
    def suuid_str(self) -> str:
        """Kompakter Base64-Token (Alias auf :attr:`compact_token`)."""
        return self.compact_token

    @property
    def suuid_bytes(self) -> bytes:
        """:attr:`suuid_str` als UTF-8-Bytes."""
        return self.compact_token.encode()

    @property
    def uuid(self) -> _uuid.UUID:
        """Das :class:`uuid.UUID`-Objekt hinter ``huuid``."""
        return self.as_uuid()

    def get_uuid(self) -> _uuid.UUID:
        """Wie :attr:`uuid`."""
        return self.as_uuid()

    def to_list(self) -> list:
        """``[sname, suuid_str, class_name, name, huuid]`` (sdata-Kompat)."""
        return [self.sname, self.suuid_str, self.class_name, self.name, self.huuid]

    def to_dict(self) -> dict:
        """Wie :meth:`suuid.SUUID.to_dict`, plus sdata-Alias ``suuid``."""
        d = super().to_dict()
        d["suuid"] = self.suuid_str
        return d

    # --- Konstruktoren mit sdata-Signaturen ------------------------------
    @classmethod
    def from_name(cls, class_name: str, name: str = "",
                  ns_name: Optional[str] = None) -> "SUUID":
        """Deterministische SUUID; ``ns_name`` (String) scoped die ID."""
        ns = OID_NAMESPACE if not ns_name else ns_name
        return super().from_name(class_name, name, ns=ns)

    @classmethod
    def from_suuid_sname(cls, s, strict: bool = False):
        """Parse einen ``sname``; ``strict=False`` (Default) → ``None`` bei Fehler."""
        return super().from_sname(s, strict=strict)

    @classmethod
    def from_suuid_str(cls, s: str) -> "SUUID":
        """Aus :attr:`suuid_str`/compact-token rekonstruieren."""
        return super().from_compact_token(s)

    @classmethod
    def from_suuid_bytes(cls, b) -> "SUUID":
        """Aus :attr:`suuid_bytes` rekonstruieren."""
        token = b.decode() if isinstance(b, (bytes, bytearray)) else b
        return super().from_compact_token(token)

    @classmethod
    def from_file(cls, class_name: str, filepath, ns_name: Optional[str] = None) -> "SUUID":
        """Content-adressierte SUUID aus Dateiinhalt (``name`` = Basename)."""
        ns = OID_NAMESPACE if not ns_name else ns_name
        return super().from_file(class_name, filepath, ns=ns)

    @classmethod
    def from_str(cls, class_name: str, s: str, ns_name: Optional[str] = None) -> "SUUID":
        """Content-adressierte SUUID aus einem String."""
        ns = OID_NAMESPACE if not ns_name else ns_name
        return super().from_content(class_name, "", s.encode("utf-8"), ns=ns)

    @classmethod
    def from_uuid(cls, class_name: str, uuid_obj: _uuid.UUID) -> "SUUID":
        """SUUID aus ``class_name`` und einem :class:`uuid.UUID` (ohne Name)."""
        return cls(class_name=clean_class_name(class_name), name="", huuid=uuid_obj.hex)

    @classmethod
    def from_obj(cls, obj, class_name: Optional[str] = None):
        """Koerziere ein Base-artiges Objekt, einen ``sname`` oder String zu SUUID."""
        if obj is None:
            return None
        if hasattr(obj, "sname"):
            return cls.from_suuid_sname(obj.sname, strict=False)
        if isinstance(obj, str):
            parsed = cls.from_suuid_sname(obj, strict=False)
            return parsed if parsed is not None else cls.from_name(class_name or cls.__name__, obj)
        return None

    # --- Statics ---------------------------------------------------------
    @staticmethod
    def generate_safe_filename(name: str) -> str:
        """100% S3-sichere Normalisierung (Alias auf :func:`suuid.safe_name`)."""
        return safe_name(name)

    @staticmethod
    def is_valid_suuid_str(s: str) -> bool:
        """``True``, wenn ``s`` ein gültiger :attr:`suuid_str` ist."""
        try:
            _SUUID.from_compact_token(s)
            return True
        except Exception:
            return False
