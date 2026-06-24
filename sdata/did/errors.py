# -*- coding: utf-8 -*-
"""Ausnahmehierarchie für das :mod:`sdata.did`-Subpackage.

Bibliotheksfunktionen werfen ausschließlich diese Ausnahmen (nie ``SystemExit``),
damit Aufrufer sie gezielt behandeln können::

    from sdata.did import verify_presentation, VerificationError
    try:
        verify_presentation(vp_jws)
    except VerificationError as exc:
        ...

Hierarchie::

    DidError                     # Basisklasse für alles in sdata.did
    ├── EncodingError            # ungültiges Format (JWK, Multibase, JWS-Struktur)
    ├── ResolutionError          # DID/Schlüssel konnte nicht aufgelöst werden
    └── VerificationError        # Signatur, Hash oder Claims ungültig

``EncodingError`` erbt zusätzlich von :class:`ValueError`, damit bestehender Code,
der ``ValueError`` abfängt, weiterhin funktioniert.
"""

__all__ = ["DidError", "EncodingError", "ResolutionError", "VerificationError"]


class DidError(Exception):
    """Basisklasse aller Fehler des ``sdata.did``-Subpackages."""


class EncodingError(DidError, ValueError):
    """Ein Wert hat ein ungültiges/unerwartetes Format (JWK, Multibase, JWS …)."""


class ResolutionError(DidError):
    """Eine DID oder ein Schlüssel konnte nicht aufgelöst werden."""


class VerificationError(DidError):
    """Eine Signatur, ein Hash oder eine Claim-Prüfung ist fehlgeschlagen."""
