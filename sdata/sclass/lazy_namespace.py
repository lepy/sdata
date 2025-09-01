# lazy_namespace.py
from __future__ import annotations
from dataclasses import dataclass
from importlib import import_module
from threading import RLock
from types import ModuleType
from typing import Any, Dict, Mapping, Tuple
import sys

Spec = str  # z.B. "sdata.suuid:SUUID" oder "pkg.mod:Outer.Inner"

def _split_spec(spec: Spec) -> Tuple[str, str]:
    """Zerlegt 'package.module:QualName' in (module, qualname)."""
    if ":" not in spec:
        raise ValueError(f"Ungültige Spec (':' fehlt): {spec!r}")
    mod, qual = spec.split(":", 1)
    if not mod or not qual:
        raise ValueError(f"Ungültige Spec: {spec!r}")
    return mod, qual

def _resolve_attr(mod: ModuleType, qualname: str) -> Any:
    """Auflösen von 'Outer.Inner.Class' in verschachtelten Attributen."""
    obj: Any = mod
    for part in qualname.split("."):
        obj = getattr(obj, part)
    return obj

@dataclass(frozen=True)
class ExportItem:
    name: str          # Attributname im Package (z.B. "SUUID")
    spec: Spec         # Ziel "mod:QualName" (z.B. "sdata.suuid:SUUID")

class LazyRegistry:
    """
    Registry verwaltet Name->Spec und hängt sich an ein Package-Modul.
    - __getattr__ lädt Zielklasse on-demand und cached sie ins Modul.
    - __dir__ gibt alle dynamischen Namen zurück (IDE-Autocomplete).
    - register() / register_many() erweitern zur Laufzeit.
    """
    def __init__(self, pkg_name: str):
        self.pkg_name = pkg_name
        self._exports: Dict[str, Spec] = {}
        self._lock = RLock()
        self._attached = False

    # -------- öffentliche API --------
    def attach(self) -> None:
        """Bindet __getattr__/__dir__ ans Ziel-Package."""
        with self._lock:
            if self._attached:
                return
            pkg = self._get_pkg()
            # bestehende __getattr__/__dir__ respektieren? (hier überschreiben)
            def _lazy_getattr(name: str) -> Any:
                # Fallback auf normales Attribut
                if name not in self._exports:
                    raise AttributeError(f"no lazy import for '{name}'")
                spec = self._exports[name]
                mod_name, qual = _split_spec(spec)
                mod = import_module(mod_name)           # lazy import
                obj = _resolve_attr(mod, qual)
                setattr(pkg, name, obj)                 # Cache im Package
                return obj

            def _lazy_dir() -> list[str]:
                # Kombiniere vorhandene und dynamische Namen
                base = set(pkg.__dict__.keys())
                return sorted(base.union(self._exports.keys()))

            pkg.__getattr__ = _lazy_getattr            # PEP 562
            pkg.__dir__ = _lazy_dir                    # für Autocomplete
            # __all__ optional pflegen
            all_items = set(getattr(pkg, "__all__", ()))
            pkg.__all__ = tuple(sorted(all_items.union(self._exports.keys())))
            self._attached = True

    def register(self, name: str, spec: Spec) -> None:
        """Fügt/überschreibt einen Export."""
        with self._lock:
            self._exports[name] = spec
            if self._attached:
                # __all__ aktualisieren
                pkg = self._get_pkg()
                all_items = set(getattr(pkg, "__all__", ()))
                pkg.__all__ = tuple(sorted(all_items.union({name})))

    def register_many(self, mapping: Mapping[str, Spec]) -> None:
        with self._lock:
            for k, v in mapping.items():
                self._exports[k] = v
            if self._attached:
                pkg = self._get_pkg()
                all_items = set(getattr(pkg, "__all__", ()))
                pkg.__all__ = tuple(sorted(all_items.union(mapping.keys())))

    def exports(self) -> Dict[str, Spec]:
        with self._lock:
            return dict(self._exports)

    # -------- Hilfen --------
    def _get_pkg(self) -> ModuleType:
        try:
            return sys.modules[self.pkg_name]
        except KeyError as e:
            raise RuntimeError(f"Package {self.pkg_name!r} ist nicht importiert.") from e


# -------- Hilfsfunktionen für (De-)Serialisierung --------

TYPE_FIELD = "__type__"     # z.B. "SUUID" oder "pkg.SUUID"
SPEC_FIELD = "__spec__"     # optional absoluter "mod:QualName"-Fallback

def resolve_by_string(name_or_spec: str, registry: LazyRegistry | None = None) -> type:
    """
    Löst entweder einen Registry-Namen (z.B. 'SUUID') ODER eine absolute Spec
    (z.B. 'sdata.suuid:SUUID') in eine Klasse auf.
    """
    if ":" in name_or_spec:
        mod, qual = _split_spec(name_or_spec)
        return _resolve_attr(import_module(mod), qual)
    if registry is None:
        raise ValueError("Registry erforderlich für Kurzname ohne Modul-Spec.")
    pkg = sys.modules[registry.pkg_name]
    return getattr(pkg, name_or_spec)  # triggert __getattr__ → lazy import

def to_json(obj: Any, type_name: str | None = None, *, include_spec: bool = False) -> dict:
    """
    Serialisiert ein Objekt mit Typ-Metadaten.
    - type_name: expliziter Schlüssel in der Registry, sonst obj.__class__.__name__
    - include_spec=True ergänzt absolute 'mod:QualName' (robuster gegen Umbenennungen).
    """
    cls = obj.__class__
    payload = getattr(obj, "to_dict", lambda: obj.__dict__)()
    meta = {TYPE_FIELD: type_name or cls.__name__}
    if include_spec:
        meta[SPEC_FIELD] = f"{cls.__module__}:{cls.__qualname__}"
    return {**meta, **payload}

def from_json(data: dict, registry: LazyRegistry | None = None) -> Any:
    """
    Rekonstruiert Objekt:
    - bevorzugt __spec__, sonst __type__ via Registry.
    Erwartet Klassenmethode `from_dict(d: dict)` oder init(**d).
    """
    if SPEC_FIELD in data:
        cls = resolve_by_string(data[SPEC_FIELD])
    elif TYPE_FIELD in data and registry is not None:
        cls = resolve_by_string(data[TYPE_FIELD], registry)
    else:
        raise ValueError(f"Kein {TYPE_FIELD}/{SPEC_FIELD} in Daten.")
    # Metafelder entfernen
    clean = {k: v for k, v in data.items() if k not in (TYPE_FIELD, SPEC_FIELD)}
    if hasattr(cls, "from_dict"):
        return cls.from_dict(clean)
    return cls(**clean)
