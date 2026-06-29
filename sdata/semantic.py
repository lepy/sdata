# -*- coding: utf-8 -*-
"""JSON-LD-/Linked-Data-Serialisierung für sdata-Metadaten + Sidecar-Dateien.

Wandelt eine :class:`sdata.metadata.Metadata` in ein selbstbeschreibendes
JSON-LD-Dokument (und zurück) und schreibt/liest optionale Sidecar-Dateien
``<sname>.meta.jsonld`` neben einem Datenblob.

Modellierung (siehe Projektentscheidungen):

* ``@id`` = DID des Objekts ``did:suuid:<sname>:sdata``.
* ``@type`` = ``[sdata:<Klasse>, <BFO-IRI der Topologieklasse>]``.
* Reservierte ``_sdata_*``-Felder -> schema.org/DCAT/PROV-Terme (name,
  identifier, generatedAtTime, wasDerivedFrom, isPartOf, …).
* **Hybrid** für User-Attribute: mit echter Einheit -> ``qudt:Quantity``-Knoten;
  ohne Einheit aber mit ``ontology`` -> getypter Knoten; sonst einfaches
  typisiertes Literal. ``ontology`` ist stets ein ``@type``/Klasse des Werts;
  das Prädikat ist ``sdata:<name>``.

Pure-Python; keine Pflicht-Dependency.
"""
import json
import os

import sdata.dtypes as dtypes
from sdata import vocab, units

try:  # optionales RDF-Backend ([rdf]=rdflib)
    import rdflib as _rdflib
except ImportError:  # pragma: no cover - abhängig vom Environment
    _rdflib = None

__all__ = [
    "to_jsonld", "from_jsonld", "to_rdf", "to_turtle", "rdf_from_doc",
    "column_node", "write_sidecar", "read_sidecar",
    "to_verifiable_credential", "verify_credential", "SIDECAR_SUFFIX",
]

SIDECAR_SUFFIX = ".meta.jsonld"

# reserviertes Feld -> JSON-LD-Term (für Top-Level-Mapping & Rück-Parsing)
_RESERVED_TERMS = {
    "_sdata_name": "name",
    "_sdata_suuid": "identifier",
    "_sdata_ctime": "generatedAtTime",
    "_sdata_topology_class": "topologyClass",
    "_sdata_version": "sdata:version",
}
_TERMS_RESERVED = {v: k for k, v in _RESERVED_TERMS.items()}

# XSD-CURIE -> dtype (eindeutige Rückabbildung; list/json kommen über JSON-Typ)
_DTYPE_FROM_XSD = {
    "xsd:string": "str", "xsd:integer": "int", "xsd:double": "float",
    "xsd:boolean": "bool", "xsd:dateTime": "timestamp",
    "xsd:base64Binary": "bytes", "xsd:anyURI": "uri",
    "xsd:date": "date", "xsd:time": "time",
    "xsd:duration": "duration", "xsd:decimal": "decimal",
    "sdata:complex": "complex",
}


def _did(sname):
    return "did:suuid:{}:sdata".format(sname)


def _sname_from_did(ref):
    """Extrahiere den sname aus ``did:suuid:<sname>:sdata`` (oder aus {'@id':…})."""
    if isinstance(ref, dict):
        ref = ref.get("@id", "")
    parts = str(ref).split(":")
    if len(parts) >= 4 and parts[0] == "did" and parts[1] == "suuid":
        return parts[2]
    return str(ref)


def _class_local(class_spec):
    """``"sdata.sclass.dataframe:DataFrame"`` -> ``"DataFrame"``."""
    return str(class_spec).split(":")[-1].split(".")[-1]


def _value_literal(attr):
    """Typisiertes JSON-LD-Literal ``{"@value": …, "@type": xsd}`` für ein Attribut."""
    spec = dtypes.get(attr.dtype) or dtypes.get("str")
    return {"@value": spec.to_json(attr.value), "@type": vocab.xsd_for_dtype(attr.dtype)}


def _attr_node(attr):
    """Hybrid-Repräsentation eines User-Attributs (Knoten oder Literal)."""
    has_unit = attr.unit not in (None, "", "-")
    types = []
    if has_unit:
        types.append("qudt:Quantity")
    type_of = vocab.type_iri(attr.ontology)
    if type_of:
        types.append(type_of)
    # ohne Einheit und ohne ontology -> einfaches Literal
    if not types:
        return _value_literal(attr)
    node = {"@type": types if len(types) > 1 else types[0],
            "name": attr.name,
            "value": _value_literal(attr)}
    if has_unit:
        node.update(units.unit_node(attr.unit))
    if attr.description:
        node["description"] = attr.description
    if attr.label:
        node["label"] = attr.label
    if attr.required:
        node["required"] = bool(attr.required)
    return node


def column_node(attr):
    """JSON-LD-Knoten (CSVW) für eine Tabellenspalte aus ``column_metadata``.

    ``attr.name`` = Spaltenname, ``attr.value`` = pandas-dtype-Name (z.B.
    ``float64``); optional ``unit``/``label``/``description``.
    """
    node = {"name": attr.name, "datatype": vocab.xsd_for_dtype(attr.value)}
    if attr.unit not in (None, "", "-"):
        node.update(units.unit_node(attr.unit))
    if attr.label:
        node["label"] = attr.label
    if attr.description:
        node["description"] = attr.description
    return node


def to_jsonld(metadata, context_mode="inline", columns=None):
    """Serialisiere ``metadata`` als JSON-LD-Dokument (dict).

    :param columns: optionale, **geordnete** Iterable von Spalten-``Attribute``s
        (DataFrame, in df-Spaltenreihenfolge); wird als ``csvw:column``-Liste ergänzt.
    """
    doc = {"@context": vocab.build_context(mode=context_mode)}

    sname = metadata.get("_sdata_sname")
    if sname is not None and sname.value:
        doc["@id"] = _did(sname.value)

    types = []
    cls = metadata.get("_sdata_class")
    if cls is not None and cls.value:
        types.append("sdata:" + _class_local(cls.value))
    topo = metadata.get("_sdata_topology_class")
    bfo = vocab.bfo_iri(topo.value) if topo is not None else None
    if bfo:
        types.append(bfo)
    if types:
        doc["@type"] = types if len(types) > 1 else types[0]

    # bekannte reservierte Felder -> Terme
    for key, term in _RESERVED_TERMS.items():
        attr = metadata.get(key)
        if attr is None or attr.value in (None, ""):
            continue
        doc[term] = attr.value
    # Relationen als DID-Referenzen
    parent = metadata.get("_sdata_parent_sname")
    if parent is not None and parent.value:
        doc["wasDerivedFrom"] = {"@id": _did(parent.value)}
    project = metadata.get("_sdata_project_sname")
    if project is not None and project.value:
        doc["isPartOf"] = {"@id": _did(project.value)}

    # User-Attribute -> sdata:<name>
    for attr in metadata.user_attributes.values():
        doc[vocab.predicate_for(attr.name)] = _attr_node(attr)

    # tabellarische Spalten (DataFrame) als geordnete csvw:column-Liste
    if columns:
        doc["columns"] = [column_node(a) for a in columns]
    return doc


def _set_from_node(metadata, name, node):
    """Rekonstruiere ein User-Attribut aus Knoten/Literal."""
    unit = "-"
    ontology = ""
    if isinstance(node, dict) and "@value" in node:
        raw, xsd = node.get("@value"), node.get("@type")
    elif isinstance(node, dict):
        literal = node.get("value", {})
        raw = literal.get("@value") if isinstance(literal, dict) else literal
        xsd = literal.get("@type") if isinstance(literal, dict) else None
        unit = node.get("symbol", "-") or "-"
        type_list = node.get("@type", [])
        if isinstance(type_list, str):
            type_list = [type_list]
        ontology = next((t for t in type_list if t != "qudt:Quantity"), "")
    else:
        raw, xsd = node, None
    # dtype bestimmen: JSON-Typ hat Vorrang (list/json), sonst XSD-Rückabbildung
    if isinstance(raw, list):
        dtype = "floatlist" if xsd == "sdata:floatlist" else "list"
    elif isinstance(raw, dict):
        dtype = "json"
    else:
        dtype = _DTYPE_FROM_XSD.get(xsd, "str")
    metadata.set_attr(name, raw, dtype=dtype, unit=unit, ontology=ontology)


def from_jsonld(doc):
    """Rekonstruiere eine :class:`Metadata` aus einem JSON-LD-Dokument (dict oder str)."""
    from sdata.metadata import Metadata
    if isinstance(doc, str):
        doc = json.loads(doc)
    m = Metadata()

    if "@id" in doc:
        m.set_attr("_sdata_sname", _sname_from_did(doc["@id"]))
    type_list = doc.get("@type", [])
    if isinstance(type_list, str):
        type_list = [type_list]
    for t in type_list:
        if isinstance(t, str) and t.startswith("sdata:"):
            m.set_attr("_sdata_class", t.split(":", 1)[1])
    for term, key in _TERMS_RESERVED.items():
        if term in doc:
            m.set_attr(key, doc[term])
    if "wasDerivedFrom" in doc:
        m.set_attr("_sdata_parent_sname", _sname_from_did(doc["wasDerivedFrom"]))
    if "isPartOf" in doc:
        m.set_attr("_sdata_project_sname", _sname_from_did(doc["isPartOf"]))

    reserved_terms = set(_TERMS_RESERVED) | {
        "@context", "@id", "@type", "wasDerivedFrom", "isPartOf"}
    for key, val in doc.items():
        if key in reserved_terms:
            continue
        if key.startswith("sdata:"):
            _set_from_node(m, key.split(":", 1)[1], val)
    return m


def to_rdf(metadata, fmt="turtle"):
    """Serialisiere die Metadaten als RDF.

    Mit installiertem ``rdflib`` (``[rdf]``) wird das JSON-LD nach ``fmt``
    (turtle/nt/xml/…) serialisiert. Ohne rdflib wird das JSON-LD selbst
    zurückgegeben – ``application/ld+json`` ist bereits gültiges RDF.
    """
    return rdf_from_doc(to_jsonld(metadata), fmt=fmt)


def rdf_from_doc(doc, fmt="turtle"):
    """Serialisiere ein bereits gebautes JSON-LD-Dokument als RDF (siehe :func:`to_rdf`)."""
    data = json.dumps(doc, default=dtypes.json_default)
    if _rdflib is not None:
        graph = _rdflib.Graph()
        graph.parse(data=data, format="json-ld")
        return graph.serialize(format=fmt)
    return json.dumps(doc, indent=2, default=dtypes.json_default)


def to_turtle(metadata):
    """Convenience: RDF im Turtle-Format (siehe :func:`to_rdf`)."""
    return to_rdf(metadata, fmt="turtle")


def to_verifiable_credential(metadata, issuer_did, issuer_priv_jwk,
                             kid=None, extra_claims=None):
    """Signiere die Metadaten als W3C Verifiable Credential (Compact-JWS, EdDSA).

    Wickelt :func:`to_jsonld` als ``credentialSubject`` und signiert über den
    pure-Python-EdDSA-Stack (:mod:`sdata.did.jose`) – keine externe Krypto.

    :return: Compact-JWS-String (``header.payload.signature``)
    """
    from sdata.did import jose
    subject = to_jsonld(metadata)
    payload = {
        "iss": issuer_did,
        "vc": {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "SdataMetadataCredential"],
            "credentialSubject": subject,
        },
    }
    if subject.get("@id"):
        payload["sub"] = subject["@id"]
    if extra_claims:
        payload.update(extra_claims)
    return jose.sign_compact(payload, issuer_priv_jwk,
                             kid=kid or (issuer_did + "#key-1"), typ="vc+ld+jwt")


def verify_credential(vc_jws, pub_jwk):
    """Verifiziere ein VC (Compact-JWS) und gib das ``credentialSubject`` (JSON-LD) zurück.

    :raises sdata.did.errors.VerificationError: bei ungültiger Signatur.
    """
    from sdata.did import jose
    payload = jose.verify_compact(vc_jws, pub_jwk)
    return payload["vc"]["credentialSubject"]


def _sidecar_path(path, sname):
    """Ziel-Dateipfad: Verzeichnis -> ``<dir>/<sname>.meta.jsonld``; sonst ``path``."""
    if path is None or os.path.isdir(path):
        directory = path or "."
        return os.path.join(directory, "{}{}".format(sname, SIDECAR_SUFFIX))
    return path


def write_sidecar(metadata, path=None, indent=2):
    """Schreibe ``<sname>.meta.jsonld`` (JSON-LD) neben einen Blob; gibt den Pfad zurück."""
    sname_attr = metadata.get("_sdata_sname")
    sname = sname_attr.value if sname_attr is not None and sname_attr.value else "metadata"
    return write_sidecar_doc(to_jsonld(metadata), path, sname, indent=indent)


def write_sidecar_doc(doc, path, sname, indent=2):
    """Schreibe ein bereits gebautes JSON-LD-Dokument als ``<sname>.meta.jsonld``."""
    target = _sidecar_path(path, sname)
    with open(target, "w") as fh:
        json.dump(doc, fh, indent=indent, default=dtypes.json_default)
    return target


def read_sidecar(path):
    """Lade eine ``.meta.jsonld``-Sidecar-Datei und rekonstruiere die Metadata."""
    with open(path, "r") as fh:
        return from_jsonld(json.load(fh))
