# -*- coding: utf-8 -*-
"""Vokabular & JSON-LD-``@context`` für die semantische Metadaten-Schicht.

Reine-Python-Tabellen (keine Abhängigkeit): Namespace-Präfixe, ein
``@context``-Builder, das XSD-Typ-Mapping (aus :mod:`sdata.dtypes`) und die
Auflösung von BFO-Topologieklassen sowie von Attribut-``ontology``-Annotationen.

Designentscheidungen (siehe Projektplan):

* **Identität**: ``@id`` eines Objekts ist seine DID ``did:suuid:<sname>:sdata``.
* **``ontology`` = immer ``@type``/Klasse** des Werts (z.B. ``bfo:Quality``); das
  Subjekt→Wert-**Prädikat** kommt NICHT aus ``ontology``, sondern ist
  ``sdata:<name>`` (bzw. ein gemappter schema.org/qudt-Term).
"""
import re

import sdata.dtypes as dtypes

__all__ = [
    "SDATA_NS", "NAMESPACES", "CONTEXT_TERMS", "CONTEXT_URL", "BFO_IRIS",
    "build_context", "xsd_for_dtype", "expand_curie", "bfo_iri",
    "safe_term", "predicate_for", "type_iri",
]

#: Default-Namespace-IRI des sdata-Vokabulars (Platzhalter – bei Bedarf anpassen).
SDATA_NS = "https://sdata.tools/ns#"
CONTEXT_URL = "https://sdata.tools/ns/context.jsonld"

NAMESPACES = {
    "sdata":   SDATA_NS,
    "schema":  "https://schema.org/",
    "dcterms": "http://purl.org/dc/terms/",
    "dcat":    "http://www.w3.org/ns/dcat#",
    "prov":    "http://www.w3.org/ns/prov#",
    "qudt":    "http://qudt.org/schema/qudt/",
    "unit":    "http://qudt.org/vocab/unit/",
    "xsd":     "http://www.w3.org/2001/XMLSchema#",
    "bfo":     "http://purl.obolibrary.org/obo/",
    "rdfs":    "http://www.w3.org/2000/01/rdf-schema#",
    "csvw":    "http://www.w3.org/ns/csvw#",
    "did":     "https://www.w3.org/ns/did#",
}

#: JSON-LD-Term-Definitionen (ergänzen die Präfixe im ``@context``).
CONTEXT_TERMS = {
    "name":            "schema:name",
    "description":     "schema:description",
    "generatedAtTime": {"@id": "prov:generatedAtTime", "@type": "xsd:dateTime"},
    "wasDerivedFrom":  {"@id": "prov:wasDerivedFrom", "@type": "@id"},
    "isPartOf":        {"@id": "dcterms:isPartOf", "@type": "@id"},
    "identifier":      "dcterms:identifier",
    "topologyClass":   {"@id": "sdata:topologyClass", "@type": "@id"},
    "value":           "qudt:value",
    "unitRef":         {"@id": "qudt:unit", "@type": "@id"},
    "symbol":          "qudt:symbol",
    "label":           "rdfs:label",
    "required":        {"@id": "sdata:required", "@type": "xsd:boolean"},
    # tabellarische Spalten (CSVW)
    "columns":         {"@id": "csvw:column", "@container": "@list"},
    "datatype":        {"@id": "csvw:datatype", "@type": "@id"},
}

#: BFO-2.0-Klassenname -> OBO-CURIE (für ``_sdata_topology_class``).
BFO_IRIS = {
    "Entity": "bfo:BFO_0000001",
    "Continuant": "bfo:BFO_0000002",
    "Occurrent": "bfo:BFO_0000003",
    "IndependentContinuant": "bfo:BFO_0000004",
    "SpatialRegion": "bfo:BFO_0000006",
    "Process": "bfo:BFO_0000015",
    "Disposition": "bfo:BFO_0000016",
    "RealizableEntity": "bfo:BFO_0000017",
    "Quality": "bfo:BFO_0000019",
    "SpecificallyDependentContinuant": "bfo:BFO_0000020",
    "Role": "bfo:BFO_0000023",
    "Site": "bfo:BFO_0000029",
    "GenericallyDependentContinuant": "bfo:BFO_0000031",
    "Function": "bfo:BFO_0000034",
    "MaterialEntity": "bfo:BFO_0000040",
    "ImmaterialEntity": "bfo:BFO_0000141",
    "RelationalQuality": "bfo:BFO_0000145",
}


def build_context(mode="inline", extra=None):
    """Liefere das JSON-LD-``@context`` (``inline`` = vollständige Term-Map) oder
    – bei ``mode="url"`` – die gehostete Context-URL.

    :param mode: ``"inline"`` (default) oder ``"url"``
    :param extra: optionale zusätzliche Term-Definitionen
    """
    if mode == "url":
        return CONTEXT_URL
    ctx = dict(NAMESPACES)
    ctx.update(CONTEXT_TERMS)
    if extra:
        ctx.update(extra)
    return ctx


def xsd_for_dtype(dtype):
    """XSD-Typ-CURIE für einen sdata-dtype (String oder Klasse)."""
    return dtypes.XSD.get(dtypes.resolve(dtype) or "str", "xsd:string")


def expand_curie(curie):
    """Expandiere eine CURIE (``schema:name``) zur vollen IRI; IRIs/Unbekanntes
    werden unverändert zurückgegeben."""
    if not isinstance(curie, str) or ":" not in curie:
        return curie
    prefix, _, local = curie.partition(":")
    if curie.startswith("http://") or curie.startswith("https://"):
        return curie
    base = NAMESPACES.get(prefix)
    return base + local if base else curie


def bfo_iri(topology_class):
    """Mappe einen Topologieklassen-String (``"sdata.sclass:IndependentContinuant"``)
    auf die BFO-CURIE oder ``None``, falls unbekannt/leer."""
    if not topology_class:
        return None
    local = str(topology_class).rsplit(":", 1)[-1]
    return BFO_IRIS.get(local)


def safe_term(name):
    """Normalisiere einen Attributnamen zu einem CURIE-tauglichen lokalen Teil."""
    local = re.sub(r"[^0-9A-Za-z_]", "_", str(name)).strip("_")
    return local or "attribute"


def predicate_for(attr_name):
    """Subjekt→Wert-Prädikat für ein User-Attribut: Default ``sdata:<safe_name>``."""
    return "sdata:" + safe_term(attr_name)


def type_iri(ontology):
    """``@type``/Klasse eines Werts aus dem ``ontology``-Feld (CURIE/IRI) oder
    ``None``. (``ontology`` ist per Projektentscheidung stets eine Klasse.)"""
    if not ontology:
        return None
    return str(ontology)
