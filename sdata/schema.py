# -*- coding: utf-8 -*-
"""Metadaten-Schemata / Templates zum *Vollqualifizieren* von Metadaten.

Ein :class:`MetadataSchema` deklariert die erwarteten Attribute einer Datenklasse
(Name, dtype, Einheit, required, ontology, …) und kann Metadaten dagegen
*validieren* sowie *vervollständigen* (Defaults/Einheiten/Ontologie auffüllen).

Reine-Python-Validierung ist immer verfügbar; mit dem optionalen Extra
``[schema]`` (jsonschema) lässt sich zusätzlich gegen ein generiertes JSON Schema
prüfen.
"""
from dataclasses import dataclass, field
from typing import Any, List, Optional

import numpy as np

import sdata.dtypes as dtypes
from sdata import units

try:  # optionales Backend ([schema]=jsonschema)
    import jsonschema as _jsonschema
except ImportError:  # pragma: no cover - abhängig vom Environment
    _jsonschema = None

__all__ = ["AttrSpec", "MetadataSchema", "ValidationReport"]

# sdata-dtype -> JSON-Schema-Typ
_JSON_TYPE = {
    "str": "string", "uri": "string", "bytes": "string", "timestamp": "string",
    "int": "integer", "float": "number", "bool": "boolean",
    "list": "array", "json": "object",
}


def _is_empty(value):
    if value is None or value == "":
        return True
    try:
        return bool(np.isnan(value))
    except (TypeError, ValueError):
        return False


@dataclass
class AttrSpec:
    """Spezifikation eines erwarteten Attributs."""
    name: str
    dtype: str = "str"
    unit: str = "-"
    required: bool = False
    ontology: str = ""
    description: str = ""
    default: Any = None
    allowed: Optional[List[Any]] = None

    def to_dict(self):
        return {"name": self.name, "dtype": self.dtype, "unit": self.unit,
                "required": self.required, "ontology": self.ontology,
                "description": self.description, "default": self.default,
                "allowed": self.allowed}

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: d[k] for k in d if k in cls.__dataclass_fields__})


@dataclass
class ValidationReport:
    """Ergebnis einer Schema-Validierung (truthy, wenn ``ok``)."""
    ok: bool
    missing: List[str] = field(default_factory=list)
    type_errors: List[tuple] = field(default_factory=list)
    unit_errors: List[str] = field(default_factory=list)
    enum_errors: List[str] = field(default_factory=list)
    extra: List[str] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)

    def __bool__(self):
        return self.ok

    def _repr_html_(self):
        color = "#2e7d32" if self.ok else "#c62828"
        status = "OK" if self.ok else "INVALID"
        rows = ""
        for label, items in [("missing", self.missing), ("type", self.type_errors),
                             ("unit", self.unit_errors), ("enum", self.enum_errors),
                             ("extra", self.extra), ("messages", self.messages)]:
            if items:
                rows += "<tr><td><b>{}</b></td><td>{}</td></tr>".format(label, items)
        return ("<div><b style='color:{}'>ValidationReport: {}</b>"
                "<table>{}</table></div>").format(color, status, rows)


class MetadataSchema:
    """Sammlung von :class:`AttrSpec` für eine Datenklasse."""

    def __init__(self, name, specs, topology_class=None, sdata_class=None):
        self.name = name
        self.specs = list(specs)
        self.topology_class = topology_class
        self.sdata_class = sdata_class

    @property
    def _by_name(self):
        return {s.name: s for s in self.specs}

    def to_dict(self):
        return {"name": self.name,
                "topology_class": self.topology_class,
                "sdata_class": self.sdata_class,
                "specs": [s.to_dict() for s in self.specs]}

    @classmethod
    def from_dict(cls, d):
        return cls(name=d.get("name", "N.N."),
                   specs=[AttrSpec.from_dict(s) for s in d.get("specs", [])],
                   topology_class=d.get("topology_class"),
                   sdata_class=d.get("sdata_class"))

    def validate(self, metadata):
        """Prüfe ``metadata`` gegen das Schema (wirft nie; liefert ValidationReport)."""
        report = ValidationReport(ok=True)
        specs = self._by_name
        for name, spec in specs.items():
            attr = metadata.get(name)
            if spec.required and (attr is None or _is_empty(attr.value)):
                report.missing.append(name)
            if attr is None:
                continue
            if dtypes.resolve(attr.dtype) != dtypes.resolve(spec.dtype):
                report.type_errors.append((name, spec.dtype))
            if spec.unit not in ("-", "") and \
                    units.normalize_symbol(attr.unit) != units.normalize_symbol(spec.unit):
                report.unit_errors.append(name)
            if spec.allowed is not None and attr.value not in spec.allowed:
                report.enum_errors.append(name)
        for name in metadata.user_attributes.keys():
            if name not in specs:
                report.extra.append(name)
        report.ok = not (report.missing or report.type_errors
                         or report.unit_errors or report.enum_errors)
        return report

    def apply(self, metadata):
        """Vervollständige ``metadata`` in-place: fehlende Attribute aus Defaults
        anlegen, vorhandene um Einheit/Ontologie/Beschreibung ergänzen. Gibt
        ``metadata`` zurück (für nicht-destruktiv: ``schema.apply(md.copy())``)."""
        for spec in self.specs:
            attr = metadata.get(spec.name)
            if attr is None:
                metadata.set_attr(spec.name, spec.default, dtype=spec.dtype,
                                  unit=spec.unit, ontology=spec.ontology,
                                  description=spec.description)
                continue
            if attr.unit in ("-", "", None) and spec.unit not in ("-", ""):
                attr.unit = spec.unit
            if not attr.ontology and spec.ontology:
                attr.ontology = spec.ontology
            if not attr.description and spec.description:
                attr.description = spec.description
        return metadata

    def to_json_schema(self):
        """Generiere ein JSON Schema (Draft 2020-12) für ``metadata.get_udict()``."""
        properties = {}
        required = []
        for spec in self.specs:
            prop = {"type": _JSON_TYPE.get(dtypes.resolve(spec.dtype), "string")}
            if spec.description:
                prop["description"] = spec.description
            if spec.allowed is not None:
                prop["enum"] = spec.allowed
            properties[spec.name] = prop
            if spec.required:
                required.append(spec.name)
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
                  "type": "object", "properties": properties}
        if required:
            schema["required"] = required
        return schema

    def validate_jsonschema(self, metadata):
        """Validiere via ``jsonschema`` (falls installiert), sonst native ``validate``."""
        if _jsonschema is None:
            return self.validate(metadata)
        try:
            _jsonschema.validate(metadata.get_udict(), self.to_json_schema())
            return ValidationReport(ok=True)
        except _jsonschema.ValidationError as exp:
            return ValidationReport(ok=False, messages=[str(exp).splitlines()[0]])
