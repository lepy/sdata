# -*- coding: utf-8 -*-
"""Interaktive Ergonomie für Metadaten: Jupyter-``_repr_html_``, Attribut-
Autocomplete (``m.a.force_x``) und Prefix-Filterung.

Reine Standardbibliothek; die Renderer bauen HTML manuell (keine pandas-Styler-/
tabulate-Abhängigkeit).
"""
import html as _html

__all__ = ["attribute_html", "metadata_html", "AttrAccessor"]


def _esc(value):
    return _html.escape("" if value is None else str(value))


def attribute_html(attr):
    """Einzeilige HTML-Tabelle für ein :class:`Attribute`."""
    return (
        "<table><tr><th>name</th><th>value</th><th>unit</th><th>dtype</th>"
        "<th>ontology</th></tr>"
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr></table>"
    ).format(_esc(attr.name), _esc(attr.value), _esc(attr.unit),
             _esc(attr.dtype), _esc(attr.ontology))


def metadata_html(metadata):
    """HTML-Darstellung einer :class:`Metadata` (Kopf + User-Attribut-Tabelle)."""
    sname_attr = metadata.get("_sdata_sname")
    sname = sname_attr.value if sname_attr is not None and sname_attr.value else ""
    cls_attr = metadata.get("_sdata_class")
    cls = cls_attr.value if cls_attr is not None and cls_attr.value else ""

    header = "<b>{}</b>".format(_esc(metadata.name))
    if cls:
        header += " <code>{}</code>".format(_esc(cls))
    if sname:
        header += " <small>did:suuid:{}:sdata</small>".format(_esc(sname))

    rows = ""
    for attr in metadata.user_attributes.values():
        rows += ("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td>"
                 "<td>{}</td><td>{}</td></tr>").format(
            _esc(attr.name), _esc(attr.value), _esc(attr.unit),
            _esc(attr.dtype), _esc(attr.ontology), _esc(attr.description))
    table = ("<table><tr><th>name</th><th>value</th><th>unit</th><th>dtype</th>"
             "<th>ontology</th><th>description</th></tr>{}</table>".format(rows))
    return "<div>{}{}</div>".format(header, table)


class AttrAccessor:
    """Attribut-Autocomplete-Helfer: ``m.a.force_x`` liefert/setzt ein Attribut.

    Liegt bewusst auf einem eigenen Objekt (nicht auf :class:`Metadata`), damit
    Tab-Completion nur Attributnamen zeigt und keine Methoden überschattet.
    """

    def __init__(self, metadata):
        object.__setattr__(self, "_md", metadata)

    def __getattr__(self, name):
        attr = self._md.get(name)
        if attr is None:
            raise AttributeError(name)
        return attr

    def __setattr__(self, name, value):
        self._md.set_attr(name, value)

    def __dir__(self):
        return [a.name for a in self._md.user_attributes.values()
                if a.name.isidentifier()]

    def __repr__(self):
        return "AttrAccessor({})".format(self.__dir__())
