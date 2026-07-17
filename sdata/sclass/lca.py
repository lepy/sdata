# -*- coding: utf-8 -*-
"""Kanonisches LCA-Systemformat: Tabellen-Schemas + :class:`LCASystem`-Container.

sdata pflegt hier die *kanonischen* Tabellen-Schemas eines matrixbasierten
LCA-Systems (Heijungs & Suh 2002): die sechs Teiltabellen ``flows``,
``processes``, ``elementary_flows``, ``exchanges_a``, ``exchanges_b`` und
``uncertainty`` samt der Verteilungs-Parametrisierungs-Spaltenliste. Konsumenten
(z. B. lepus-lca) pinnen dieses Schema und konvertieren an ihrer Datengrenze zu
numpy/scipy — sdata selbst rechnet nicht, sondern hält Format und Integrität.

**Matrix-Konvention (Format-Vertrag).** Die Vorzeichen der Austauschkoeffizienten
tragen die Semantik: **Outputs positiv (+), Inputs negativ (−)**. Es gibt im
nativen Format *keine* ``flip``-/``negative``-Flags — deren Übersetzung wandert in
eine spätere bw_processing-Interop-Brücke (sdata-RFC 0015). Ein Gut ist Output,
wo sein Koeffizient positiv ist; ein Abfall ist Behandlungs-Output, wo sein
Koeffizient negativ ist.

**Zeilenordnung ist normativ.** Die Reihenfolge der Zeilen in ``flows`` /
``processes`` / ``elementary_flows`` *ist* die Index-/Matrixordnung des
Rechenkerns (RFC-002 D7: keine hash-abhängige Iteration). Sie ist damit
identitätsstiftend und geht nachweislich in :meth:`LCASystem.content_checksum`
ein: eine Zeilen-Permutation liefert eine **andere** Content-Prüfsumme, obwohl
die Zeilenmenge unverändert bleibt (siehe Tests).

Die ``uncertainty``-Tabelle ist ein Format-Vorgriff **ohne Arithmetik**: sie
parametrisiert Zellen-Unschärfe *explizit* — getrennte Spaltensätze je Lesart
(z. B. ``lognormal_underlying_mu``/``lognormal_underlying_sigma`` **oder**
``lognormal_geometric_gmean``/``lognormal_geometric_gsd``), statt der vier
verwechselbaren ``stats_arrays``-Parametrisierungen (Heijungs 2024, S. 915–922).
Konsumenten reichen die Datensätze unangetastet durch, bis sie sie brauchen.
"""
import hashlib
import os
from typing import Any, Dict, List, Optional

from sdata.schema import AttrSpec, TableSchema, ValidationReport
from sdata.sclass.dataframe import DataFrame
from sdata.sclass.dataframegroup import DataFrameGroup

__all__ = [
    "CSV_DIALECT",
    "ELEMENTARY_FLOWS_SCHEMA",
    "EXCHANGES_A_SCHEMA",
    "EXCHANGES_B_SCHEMA",
    "FLOWS_SCHEMA",
    "FLOW_KINDS",
    "FLOW_KIND_GOOD",
    "FLOW_KIND_WASTE",
    "LCASystem",
    "LCA_SCHEMAS",
    "LCA_TABLE_ORDER",
    "MATRICES",
    "MATRIX_A",
    "MATRIX_B",
    "PROCESSES_SCHEMA",
    "UNCERTAINTY_DIST_COLUMNS",
    "UNCERTAINTY_SCHEMA",
]

#: **CSV-Dialekt-Vertrag** von :meth:`LCASystem.to_csv_dir` / :meth:`from_csv_dir`.
#: Feldtrenner ``","``, Dezimalpunkt ``"."``, Kodierung UTF-8. NaN-Politik: eine
#: leere Zelle *ist* der fehlende Wert (``na_rep=""`` beim Schreiben, leere Zelle
#: → NaN beim Lesen). Der Dialekt ist **gepinnt** und nicht überschreibbar: die
#: Ordnungs- und :meth:`content_checksum`-Garantien gelten ausschliesslich für
#: genau diesen Dialekt. Fremde Dialekte (z. B. ``;``-getrennt, Dezimalkomma)
#: werden **nicht** still korrekt gelesen — sie fallen als falsche Spaltenform
#: auf, statt lautlos fehlzuinterpretieren.
CSV_DIALECT: Dict[str, str] = {"sep": ",", "decimal": ".", "encoding": "utf-8"}

# --- Konvention (Vertrag) ---------------------------------------------------
#: Gut/Abfall-Label eines ökonomischen Flusses (Definition 6/7, S. 90).
FLOW_KIND_GOOD = "GOOD"
FLOW_KIND_WASTE = "WASTE"
FLOW_KINDS = [FLOW_KIND_GOOD, FLOW_KIND_WASTE]

#: Bezeichner der beiden Systemmatrizen in ``uncertainty.matrix``.
MATRIX_A = "A"
MATRIX_B = "B"
MATRICES = [MATRIX_A, MATRIX_B]

#: Explizite Verteilungs-Parametrisierungs-Spalten der ``uncertainty``-Tabelle.
#: Getrennte Spaltensätze je Lesart — nie eine mehrdeutige Sammelspalte. Alle
#: sind optional; je Zeile werden genau die zur ``dist``-Familie passenden
#: Spalten gefüllt (der Konsument liest die zu seiner Lesart gehörigen).
UNCERTAINTY_DIST_COLUMNS: List[AttrSpec] = [
    # Normal
    AttrSpec("normal_mean", dtype="float", description="Normal: Mittelwert μ"),
    AttrSpec("normal_sd", dtype="float", description="Normal: Standardabweichung σ"),
    # Lognormal — Lesart 1: Parameter der zugrundeliegenden Normalverteilung
    AttrSpec("lognormal_underlying_mu", dtype="float",
             description="Lognormal: μ der zugrundeliegenden Normalverteilung (log-Raum)"),
    AttrSpec("lognormal_underlying_sigma", dtype="float",
             description="Lognormal: σ der zugrundeliegenden Normalverteilung (log-Raum)"),
    # Lognormal — Lesart 2: geometrische Kenngrößen im Datenraum
    AttrSpec("lognormal_geometric_gmean", dtype="float",
             description="Lognormal: geometrischer Mittelwert (Datenraum)"),
    AttrSpec("lognormal_geometric_gsd", dtype="float",
             description="Lognormal: geometrische Standardabweichung (Datenraum)"),
    # Uniform
    AttrSpec("uniform_min", dtype="float", description="Uniform: untere Grenze"),
    AttrSpec("uniform_max", dtype="float", description="Uniform: obere Grenze"),
    # Triangular
    AttrSpec("triangular_min", dtype="float", description="Triangular: untere Grenze"),
    AttrSpec("triangular_mode", dtype="float", description="Triangular: Modus"),
    AttrSpec("triangular_max", dtype="float", description="Triangular: obere Grenze"),
]

# --- Tabellen-Schemas (Pflichtspalten: required=True) -----------------------
FLOWS_SCHEMA = TableSchema("flows", [
    AttrSpec("id", dtype="str", required=True,
             description="eindeutige Fluss-ID (Zeilenordnung = Zeilen von A)"),
    AttrSpec("unit", dtype="str", required=True, description="Einheit des Flusses"),
    AttrSpec("kind", dtype="str", required=True, allowed=FLOW_KINDS,
             description="GOOD (Gut) | WASTE (Abfall) — Cut-off/Multifunktionalität"),
    AttrSpec("name", dtype="str", description="lesbarer Name"),
    AttrSpec("region", dtype="str", description="Region (optional)"),
    AttrSpec("time_slice", dtype="str", description="Zeitscheibe (optional)"),
])

PROCESSES_SCHEMA = TableSchema("processes", [
    AttrSpec("id", dtype="str", required=True,
             description="eindeutige Prozess-ID (Spaltenordnung = Spalten von A/B)"),
    AttrSpec("name", dtype="str", description="lesbarer Name"),
    AttrSpec("reference_output", dtype="str",
             description="Fluss-ID des Referenz-/Funktionsoutputs (optional)"),
])

ELEMENTARY_FLOWS_SCHEMA = TableSchema("elementary_flows", [
    AttrSpec("id", dtype="str", required=True,
             description="eindeutige Elementarfluss-ID (Zeilenordnung = Zeilen von B)"),
    AttrSpec("unit", dtype="str", required=True, description="Einheit"),
    AttrSpec("compartment", dtype="str", required=True,
             description="Kompartiment (z. B. to air / from ground)"),
    AttrSpec("name", dtype="str", description="lesbarer Name"),
])

EXCHANGES_A_SCHEMA = TableSchema("exchanges_a", [
    AttrSpec("row_id", dtype="str", required=True, description="Fluss-ID (Zeile von A)"),
    AttrSpec("col_id", dtype="str", required=True, description="Prozess-ID (Spalte von A)"),
    AttrSpec("value", dtype="float", required=True,
             description="Koeffizient — Output +, Input − (COO; Duplikat (i,j) verboten)"),
])

EXCHANGES_B_SCHEMA = TableSchema("exchanges_b", [
    AttrSpec("row_id", dtype="str", required=True,
             description="Elementarfluss-ID (Zeile von B)"),
    AttrSpec("col_id", dtype="str", required=True, description="Prozess-ID (Spalte von B)"),
    AttrSpec("value", dtype="float", required=True,
             description="Koeffizient — Emission +, Ressourcenentnahme − (COO)"),
])

UNCERTAINTY_SCHEMA = TableSchema("uncertainty", [
    AttrSpec("matrix", dtype="str", required=True, allowed=MATRICES,
             description="A | B — welche Systemmatrix die Zelle trägt"),
    AttrSpec("row_id", dtype="str", required=True, description="Zeilen-Fluss-ID der Zelle"),
    AttrSpec("col_id", dtype="str", required=True, description="Spalten-Prozess-ID der Zelle"),
    AttrSpec("dist", dtype="str", required=True,
             description="Verteilungsfamilie (normal | lognormal | uniform | triangular | …)"),
    *UNCERTAINTY_DIST_COLUMNS,
])

#: Kanonische Reihenfolge der Teiltabellen (bestimmt die Prüfsummen-Reihenfolge).
LCA_TABLE_ORDER = (
    "flows", "processes", "elementary_flows",
    "exchanges_a", "exchanges_b", "uncertainty",
)

#: Tabellenname → :class:`~sdata.schema.TableSchema`.
LCA_SCHEMAS: Dict[str, TableSchema] = {
    "flows": FLOWS_SCHEMA,
    "processes": PROCESSES_SCHEMA,
    "elementary_flows": ELEMENTARY_FLOWS_SCHEMA,
    "exchanges_a": EXCHANGES_A_SCHEMA,
    "exchanges_b": EXCHANGES_B_SCHEMA,
    "uncertainty": UNCERTAINTY_SCHEMA,
}


class LCASystem(DataFrameGroup):
    """Container eines matrixbasierten LCA-Systems (sechs benannte Teiltabellen).

    Erbt von :class:`~sdata.sclass.dataframegroup.DataFrameGroup`: die Teiltabellen
    liegen als vollwertige :class:`~sdata.sclass.dataframe.DataFrame` (mit
    Spalten-Metadaten) unter ihren kanonischen Schlüsseln
    (:data:`LCA_TABLE_ORDER`). Serialisierung (``to_dict``/``from_dict``,
    ``to_json``/``from_json``) und die volle DataFrameGroup-API bleiben erhalten.

    Zusätzlich:

    * :meth:`set_table` legt eine Tabelle unter Schema an (vervollständigt die
      Spalten-Metadaten aus dem passenden :class:`TableSchema`);
    * :meth:`content_checksum` bildet eine deterministische Prüfsumme **über alle
      Teiltabellen** — die kanonische CSV-Form je Tabelle geht in Zeilen- und
      Spaltenordnung ein (Zeilen-Permutation ⇒ andere Prüfsumme);
    * :meth:`validate_tables` prüft jede vorhandene Tabelle gegen ihr Schema;
    * :meth:`to_csv_dir` / :meth:`from_csv_dir` sind ein verlustfreier
      CSV-Roundtrip (eine Datei je Tabelle, Ordnung und Werte erhalten) — mit
      **gepinntem** Dialekt (:data:`CSV_DIALECT`: ``,``-getrennt, Dezimalpunkt,
      UTF-8); die Roundtrip-/Prüfsummen-Garantie gilt nur für diesen Dialekt.
    """

    SDATA_CLS = "sdata.sclass.lca.LCASystem"

    #: Kanonische Tabellenreihenfolge (bestimmt die Prüfsummen-Reihenfolge).
    TABLE_ORDER = LCA_TABLE_ORDER
    #: Tabellenname → :class:`TableSchema`.
    SCHEMAS = LCA_SCHEMAS

    # ------------------------------------------------------------- public API
    def set_table(self, key: str, df: Any, *, overwrite: bool = True) -> DataFrame:
        """Lege die Teiltabelle ``key`` unter ihrem Schema an (oder überschreibe sie).

        :param key: einer der kanonischen Namen (:data:`LCA_TABLE_ORDER`).
        :param df: ein :class:`DataFrame` oder ein pandas ``DataFrame``.
        :param overwrite: bestehende Tabelle ersetzen (Default True).
        :return: die gespeicherte :class:`DataFrame`.
        :raises ValueError: bei unbekanntem ``key``.
        """
        if key not in self.SCHEMAS:
            raise ValueError(
                f"unbekannte LCA-Tabelle {key!r}; erlaubt: {sorted(self.SCHEMAS)}")
        sdf = df if isinstance(df, DataFrame) else DataFrame(df=df, name=key)
        self.SCHEMAS[key].apply(sdf)                       # Spalten-Metadaten füllen
        self.add(sdf, key=key, overwrite=overwrite)
        return sdf

    def table(self, key: str) -> Optional[DataFrame]:
        """Die gespeicherte :class:`DataFrame` der Teiltabelle ``key`` (oder ``None``)."""
        return self.get(key)

    def content_checksum(self) -> str:
        """SHA-256 über **alle** Teiltabellen — die Quell-Identität des Systems.

        Gehasht wird je vorhandener Tabelle (in :data:`LCA_TABLE_ORDER`) der
        Tabellenname plus die kanonische CSV-Form der Daten
        (:attr:`DataFrame.content_bytes` — Header + Werte in Zeilenordnung, ohne
        Index, UTF-8). Damit gehen **Zeilenordnung und Spaltenordnung** in die
        Prüfsumme ein: eine Zeilen-Permutation ergibt eine andere Prüfsumme,
        obwohl die Zeilenmenge identisch bleibt (Zeilenordnung ist normativ).

        Reine Datenprüfsumme (keine Metadaten): stabil, wenn sich nur
        Annotationen ändern — konsistent mit RFC 0004 (``DataFrame.content_bytes``).

        :return: Hex-Digest (64 Zeichen).
        """
        h = hashlib.sha256()
        for key in self.TABLE_ORDER:
            member = self.get(key)
            if member is None:
                continue
            h.update(key.encode("utf-8"))
            h.update(b"\x00")
            h.update(member.content_bytes)
            h.update(b"\x00")
        return h.hexdigest()

    def validate_tables(self, *, only_present: bool = True) -> Dict[str, ValidationReport]:
        """Validiere jede Teiltabelle gegen ihr :class:`TableSchema`.

        Reicht die :class:`~sdata.schema.TableSchema`-Validierung durch (Spalten,
        dtypes, Einheiten-Annotation), rechnet ``ok`` aber gegen die **Pflicht**-
        spalten (``required``): eine fehlende Pflichtspalte macht die Tabelle
        ungültig, eine fehlende *optionale* Spalte (``name``/``region``/
        ``time_slice``/``reference_output``, ungenutzte ``uncertainty``-
        Parametrisierungen) bleibt gültig. Absente Spalten werden weiterhin in
        ``missing`` gelistet (informativ).

        :param only_present: nur die tatsächlich vorhandenen Tabellen prüfen
          (Default). Mit ``False`` liefern fehlende Tabellen einen Report, dessen
          Pflichtspalten alle als ``missing`` gemeldet werden.
        :return: ``{tabellenname: ValidationReport}`` (Report ist truthy, wenn ok).
        """
        reports: Dict[str, ValidationReport] = {}
        for key, schema in self.SCHEMAS.items():
            member = self.get(key)
            required = {c.name for c in schema.columns if c.required}
            if member is None:
                if only_present:
                    continue
                reports[key] = ValidationReport(ok=False, missing=sorted(required))
                continue
            report = schema.validate(member)
            missing_required = [m for m in report.missing if m in required]
            report.ok = not (missing_required or report.type_errors or report.unit_errors)
            reports[key] = report
        return reports

    def is_valid(self, **kwargs: Any) -> bool:
        """``True``, wenn alle geprüften Teiltabellen ihr Schema erfüllen."""
        return all(self.validate_tables(**kwargs).values())

    # ------------------------------------------------------------ CSV-Roundtrip
    def to_csv_dir(self, path: str) -> List[str]:
        """Schreibe je Teiltabelle eine ``<key>.csv`` nach ``path`` (Daten, kein Index).

        Ordnung (Zeilen und Spalten) und Werte bleiben erhalten; die qualifizierende
        Spalten-Semantik lebt im Schema, nicht in der CSV.

        **Dialekt-Vertrag (:data:`CSV_DIALECT`).** Geschrieben wird fest mit
        Feldtrenner ``","``, Dezimalpunkt ``"."`` und UTF-8; NaN als leere Zelle
        (``na_rep=""``). Die Roundtrip- und :meth:`content_checksum`-Garantien
        gelten **nur** für diesen Dialekt (siehe :data:`CSV_DIALECT`); er ist
        bewusst nicht konfigurierbar, damit die Prüfsumme stabil bleibt.

        :param path: Zielverzeichnis (wird bei Bedarf angelegt).
        :return: Liste der geschriebenen Dateipfade (in :data:`LCA_TABLE_ORDER`).
        """
        os.makedirs(path, exist_ok=True)
        written: List[str] = []
        for key in self.TABLE_ORDER:
            member = self.get(key)
            if member is None:
                continue
            filepath = os.path.join(path, f"{key}.csv")
            member.df.to_csv(
                filepath, index=False, na_rep="",
                sep=CSV_DIALECT["sep"], decimal=CSV_DIALECT["decimal"],
                encoding=CSV_DIALECT["encoding"])
            written.append(filepath)
        return written

    @classmethod
    def from_csv_dir(cls, path: str, *, name: str = "lca_system") -> "LCASystem":
        """Lese ein per :meth:`to_csv_dir` geschriebenes Verzeichnis zurück.

        Es werden genau die kanonischen ``<key>.csv`` (:data:`LCA_TABLE_ORDER`)
        geladen, die vorhanden sind; jede wird unter ihrem Schema abgelegt.

        **Dialekt-Vertrag (:data:`CSV_DIALECT`).** Gelesen wird fest mit
        Feldtrenner ``","``, Dezimalpunkt ``"."`` und UTF-8 — passend zu
        :meth:`to_csv_dir`. Der Dialekt ist **nicht** überschreibbar (kein
        ``**read_csv_kwargs``-Durchgriff): eine Datei in fremdem Dialekt (z. B.
        ``;``-getrennt oder mit Dezimalkomma) wird dadurch nicht still korrekt
        gelesen, sondern fällt als falsche Spaltenform auf — der Vertrag schützt
        die Ordnungs-/Prüfsummen-Garantie vor lautlosem Fehllesen.

        :param path: Quellverzeichnis.
        :param name: Name des rekonstruierten Systems.
        :return: eine :class:`LCASystem`.
        """
        import pandas as pd
        system = cls(name=name)
        for key in cls.TABLE_ORDER:
            filepath = os.path.join(path, f"{key}.csv")
            if os.path.exists(filepath):
                system.set_table(key, pd.read_csv(
                    filepath, sep=CSV_DIALECT["sep"], decimal=CSV_DIALECT["decimal"],
                    encoding=CSV_DIALECT["encoding"]))
        return system
