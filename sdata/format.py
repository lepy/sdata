"""Format-Versionierung des serialisierten sdata-Objekts (RFC 0010).

Ein **monoton steigender Integer** ``_sdata_format_version`` beschreibt die Shape
des serialisierten Objekt-JSON — getrennt von der Paketversion
(``_sdata_version`` = ``sdata.__version__``, die bei jedem Release steigt, aber
kein Kompatibilitätssignal ist).

Beim Lesen läuft jedes Payload durch :func:`ensure_compatible` (ein Choke-Point in
:meth:`Base.from_dict`/:meth:`DataFrame.from_dict`/``_restore_from_attrs``):

* fehlt das Feld → **v1** (Objekte vor diesem RFC), still lesen;
* gleich → normal;
* älter → :func:`register_migration`-Treppe (v1→v2→…) anwenden;
* neuer → :class:`FormatVersionWarning` + best-effort (``strict=True`` →
  :class:`IncompatibleFormatError`).

Vorbild: das ``PRAGMA user_version`` + ``migrate()``-Muster des
:class:`~sdata.iolib.json1sqlitestore.JSON1SQLiteStore` (dort auf DB-Schema-Ebene).
"""
from __future__ import annotations

import logging
import warnings
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "SDATA_FORMAT_VERSION_KEY",
    "CURRENT_FORMAT_VERSION",
    "FormatVersionWarning",
    "IncompatibleFormatError",
    "read_format_version",
    "ensure_compatible",
    "register_migration",
]

#: Reservierter Metadaten-Schlüssel für die Formatversion.
SDATA_FORMAT_VERSION_KEY = "_sdata_format_version"

#: Aktuelle Formatversion; steigt **nur** bei einem Shape-Bruch des Objekt-JSON.
CURRENT_FORMAT_VERSION = 1


class FormatVersionWarning(UserWarning):
    """Ein gelesenes Objekt trägt eine **neuere** Formatversion als unterstützt."""


class IncompatibleFormatError(Exception):
    """Ein Objekt kann nicht auf die aktuelle Formatversion gebracht werden."""


#: Migrations-Treppe: ``{from_version: callable(payload) -> payload}``. Leer bis zum
#: ersten echten Shape-Bruch; jede Stufe hebt genau um eine Version an.
_MIGRATIONS: Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}


def register_migration(from_version: int):
    """Registriere eine Migration ``payload(v{from}) -> payload(v{from+1})``.

    :param from_version: die Ausgangs-Formatversion, die diese Stufe anhebt.
    """
    def deco(fn: Callable[[Dict[str, Any]], Dict[str, Any]]):
        _MIGRATIONS[from_version] = fn
        return fn
    return deco


def read_format_version(payload: Optional[Dict[str, Any]]) -> int:
    """Lies die Formatversion aus einem Objekt- oder ``attrs``-Payload.

    Toleriert beide Shapes (``{"metadata": {...}}`` aus ``to_dict`` **und** ein
    flaches Metadaten-Dict) sowie das genestete ``{"value": …}`` je Attribut.
    Fehlt das Feld oder ist es unparsebar, gilt **v1**.

    :param payload: Objekt-Dict, ``attrs['_sdata']``-Dict oder ``None``.
    :return: die Formatversion als ``int`` (Default 1).
    """
    if not isinstance(payload, dict):
        return 1
    meta = payload.get("metadata", payload)
    if not isinstance(meta, dict):
        return 1
    node = meta.get(SDATA_FORMAT_VERSION_KEY)
    if isinstance(node, dict):          # to_dict nestet {"value": …, "dtype": …}
        node = node.get("value")
    try:
        return int(node) if node is not None else 1
    except (TypeError, ValueError):
        return 1


def ensure_compatible(payload: Dict[str, Any], *,
                      current: int = CURRENT_FORMAT_VERSION,
                      strict: bool = False) -> Dict[str, Any]:
    """Prüfe/migriere ein Payload auf ``current`` — der Lese-Choke-Point (RFC 0010 §6).

    :param payload: das zu lesende Objekt-/attrs-Dict (wird bei Migration verändert
        zurückgegeben; ohne Migration unverändert durchgereicht).
    :param current: Zielversion (Default :data:`CURRENT_FORMAT_VERSION`).
    :param strict: bei einer **neueren** Version statt zu warnen hart scheitern.
    :raises IncompatibleFormatError: bei fehlender Migrationsstufe oder (mit
        ``strict``) bei einer neueren Version.
    :raises FormatVersionWarning: (als Warnung) bei einer neueren Version ohne ``strict``.
    """
    if not isinstance(payload, dict):
        return payload
    v = read_format_version(payload)
    if v == current:
        return payload
    if v > current:
        msg = f"sdata object format v{v} is newer than supported v{current}"
        if strict:
            raise IncompatibleFormatError(msg)
        warnings.warn(msg, FormatVersionWarning)
        return payload
    while v < current:
        step = _MIGRATIONS.get(v)
        if step is None:
            raise IncompatibleFormatError(
                f"no migration registered for sdata format v{v} -> v{v + 1}")
        payload = step(payload)
        logger.info("migrated sdata payload v%d -> v%d", v, v + 1)
        v += 1
    return payload
