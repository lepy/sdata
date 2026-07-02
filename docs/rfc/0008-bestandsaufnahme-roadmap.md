# RFC 0008 — Bestandsaufnahme und Verbesserungs-Roadmap

| Feld        | Wert                                                                                     |
|-------------|------------------------------------------------------------------------------------------|
| Status      | Draft                                                                                     |
| Datum       | 2026-07-02                                                                                |
| Autor       | lepy <lepy@tuta.io>                                                                       |
| Komponente  | paketweit: `sdata/` (Kern, `sclass/`, `iolib/`), Packaging, Docs, CI, Repo-Hygiene        |
| Betrifft    | keine einzelne API — dieses RFC ist ein **Meta-RFC**: Ist-Analyse + priorisierte Roadmap  |
| Vorgeschichte | RFC 0001–0007 (Store, HDF5, Blob, DataFrame/Blob, Bild-Metadaten, Einheiten, Writer)   |
| Validierung | entfällt (Meta-RFC); jede Maßnahme wird im jeweiligen Folge-RFC bzw. PR validiert         |

> **Zweck.** Nach sieben Einzel-RFCs und der Umstellung auf die `sclass`-Generation ist es
> Zeit für eine ehrliche Gesamtschau: **Was ist gut** (und soll so bleiben bzw. Vorbild
> für den Rest sein), **was kann verbessert werden** (mit Beleg, Priorität und
> Maßnahmenpfad). Grundlage ist eine vollständige Durchsicht der Kernmodule, der
> I/O-Schicht, der Projekt-Infrastruktur sowie der offenen Punkte aus RFC 0001–0007.

## 1. Zusammenfassung

sdata besteht heute aus **zwei Generationen**: einer architektonisch reifen neuen
Generation (`base.py` + `sclass/*` + Funktionskern `dtypes`/`schema`/`semantic`/`vocab`/
`units`, Stores und Writer in `iolib/`) und einer Alt-Generation (`deprecated.Data` mit
Anhang), die **weiterhin exportiert und load-bearing** ist. Die neue Generation löst die
Kernversprechen des Formats ein — selbstbeschreibende Daten, verlustfreie
Metadaten-Roundtrips, semantisches Rückgrat (JSON-LD/QUDT/BFO/PROV/CSVW/DID/VC) — und ist
gut getestet (100 % Coverage auf der Kernmenge, ~665 Tests).

Die Hauptlasten sind: (a) die **Doppel-API** alt/neu ohne Entfernungsplan, (b) eine
**Lese-Lücke** (Writer ohne Reader, RFC 0007 §11), (c) **keine Format-Versionierung**
trotz README-Designziel, (d) **Duplikation** (Store-Zwillinge, fünf Klassen-Factories,
drei dtype-Rater, zwei Spalten-Metadaten-Modelle), (e) zwei echte
**Bibliotheks-Anti-Patterns** (`logging.basicConfig` auf Modulebene, ein latenter
`UnboundLocalError`) sowie (f) **Packaging-/Repo-Altlasten** (Extras nur in `setup.py`,
kaputte `tox.ini`, eingecheckte Scratch-/Checkpoint-Dateien, u. a. zwei Dateien namens
`t/secret*`).

Dieses RFC priorisiert die Befunde (P1–P3), bündelt sie in **drei Maßnahmenpakete**
(Quick-Fixes ohne RFC, Folge-RFCs, Deklarationsentscheidungen) und schlägt die
Reihenfolge vor.

## 2. Methodik

* Vollständige Lektüre der Kernmodule (`base.py`, `metadata.py`, `dtypes.py`,
  `schema.py`, `semantic.py`, `vocab.py`, `units.py`, `timestamp.py`, `suuid.py`,
  `node.py`, `sclass/*`, `iolib/*`) plus Metrik-Scans über das Gesamtpaket.
* Abgleich der **README-Designziele** (README.md:11–31) mit dem Umsetzungsstand.
* Sammlung der Abschnitte „Risiken / offene Punkte" aus RFC 0001–0007.
* Prüfung von Packaging (`setup.py`/`pyproject.toml`/`requirements.txt`/`tox.ini`),
  CI (`ci/local-ci.sh`, `Makefile`, `.github/workflows/`), Docs (`mkdocs.yml`,
  `docs/source/`) und `git ls-files` (Repo-Hygiene).

## 3. Was ist gut (Stärken — bewahren und als Vorbild nutzen)

**S1 — Metadaten als semantisches Rückgrat.** `Metadata`/`Attribute` mit
`dtype`/`unit`/`ontology`/`label` je Attribut, dazu die pure-Python-Semantikschicht
(QUDT-Quantities, BFO-`@type`, PROV/DCAT, CSVW-Spalten, DID-Identität, Verifiable
Credentials) in `semantic.py`/`vocab.py`/`did/`. Das ist das Alleinstellungsmerkmal des
Formats und durchgängig ohne harte Abhängigkeiten realisiert.

**S2 — Verlustfreie Roundtrips über 7 Formatfamilien.** dict/JSON, Parquet (Datei und
Bytes), Arrow, Feather, Data Package, HDF5 tragen die Metadaten unter dem einheitlichen
`_sdata`-Schlüssel und restaurieren sie zentral über `_restore_from_attrs`
(`sclass/dataframe.py:557`). `to_arrow` hängt `unit`/`label`/`ontology` zusätzlich
**nativ** an jedes Arrow-Feld (`dataframe.py:653–700`) — DuckDB/Polars lesen die
Spaltensemantik ohne sdata. Kein proprietärer Silo.

**S3 — Der Funktionskern der neuen Generation ist vorbildlich.**
`dtypes.py` als Registry-Single-Source-of-Truth (`resolve`/`coerce`/`json_default`,
`dtypes.py:450–502`), `schema.py` mit nie werfendem `validate()` → `ValidationReport`,
`units.py` mit kuratierter QUDT/UCUM-Tabelle (RFC 0006), `sclass/content.py` als
Integritäts-Mixin, `LazyRegistry` (PEP 562) in `sclass/`. Diese Module definieren den
Qualitätsmaßstab für den Rest.

**S4 — I/O-Neubauten sind durchdacht und gehärtet.** `JSON1SQLiteStore` (RFC 0001:
generierte `_sdata_*`-Spalten, WAL, durchgängig parametrisierte Queries, Transaktions-
Kontextmanager), `imagemeta.py` (RFC 0005: 6 Container, Pillow-frei, symmetrische
Handler-Registry — die sauberste Einzelkomponente), Writer-Interface (RFC 0007:
Protocol + ABC, `WriteReceipt`, `require_*`-Metadaten-Vertrag, SQL-Injection-gehärtet,
100 % Coverage).

**S5 — Konsistentes Optional-Dependency-Muster.** Schlanker Kern (nur
`numpy`/`pandas`/`suuid`), alles Weitere über Extras mit einheitlichen
`try/except ImportError`-Guards und handlungsorientierten Fehlermeldungen
(`_require_parquet`, `dataframe.py:21–36`) bzw. Pure-Python-Fallbacks.

**S6 — Projektprozesse funktionieren.** RFC-Verfahren mit Risiko-Abschnitten (0001–0007),
gepflegtes CHANGELOG (Keep-a-Changelog/SemVer), Versions-Single-Source
(`sdata/__init__.py`), Release via `uv build` + OIDC Trusted Publishing (kein
Token-Secret), bewusst lokale CI (`ci/local-ci.sh`/`make ci`), ~665 Testfunktionen,
100 % Line-Coverage auf der nicht-ausgeschlossenen Kernmenge (5299 Statements).

## 4. Was kann verbessert werden (Befunde, priorisiert)

### P1 — Korrektheit und Architektur

| # | Befund | Beleg |
|---|--------|-------|
| B1 | **Zwei API-Generationen gleichzeitig exportiert.** `deprecated.Data` (1492 Z.) ist Default-Export (`__init__.py:24/119/126`) und weiterhin load-bearing: `doe.py:79`, `iolib/hdf.py:10`, `iolib/pud.py:10`, `iolib/vault.py:8`, `experiments/*`. Nutzer sehen zwei überlappende Serialisierungs-APIs ohne Migrationspfad. | `sdata/__init__.py`, `sdata/deprecated/data.py` |
| B2 | **Bibliothek konfiguriert globales Logging.** `logging.basicConfig(...)` auf Modulebene kapert den Root-Logger der Host-Anwendung; `node.py` setzt sogar `level=DEBUG`. Korrekt wäre nur `getLogger(__name__)` (+ `NullHandler`). | `base.py:20`, `node.py:9` |
| B3 | **Latenter Bug:** `Metadata.from_json` ohne existierenden `filepath` und ohne `jsonstr` → `UnboundLocalError` statt klarer Fehlermeldung. | `metadata.py:576–592` |
| B4 | **Writer ohne Reader.** Die Polymorphie „Senke austauschen ohne Aufrufer zu ändern" existiert nur schreibend; lesend muss der Aufrufer das Backend kennen (verstreute `from_*`-Classmethods). Von RFC 0007 §11 selbst als Folge-RFC benannt. | `iolib/writer.py`, RFC 0007 |
| B5 | **Keine Format-Versionierung.** `SDATA_VERSION` trägt die *Paket*-Version (`base.py:36/98`), kein `from_*` prüft eine Formatversion, kein Migrations-Hook für Objekt-JSON. Das README-Ziel „data format versions" ist nicht eingelöst — für ein „open data format" ein Kernbedarf. | `base.py:36`, README:16–17 |
| B6 | **CSV-Roundtrip-Falle.** `to_csv(sidecar=True)` schreibt den JSON-LD-Sidecar, `from_csv` liest ihn **nie** zurück — stiller Metadatenverlust. Inkonsistent zu `sclass/image.py`, wo `from_file` den Sidecar automatisch merged (`image.py:154–165`). | `dataframe.py:611–650` |
| B7 | **Stille Fehler-Degradation als Default.** `Attribute._set_value` fängt `DtypeError` im lenient-Default, loggt nur `logger.error` und lässt den Wert unverändert — fehlerhafte Werte verschwinden lautlos. | `metadata.py:127–136` |

### P2 — Duplikation, Konsistenz, Packaging

| # | Befund | Beleg |
|---|--------|-------|
| B8 | **Store-Zwillinge.** `json1sqlitestore.py` (553 Z.) und `jsonsqlitestore.py` (699 Z.) teilen 28 gleichnamige Methoden; nur der neue wird verwendet, der alte hat als Einziges zlib-Kompression und driftet. | `sdata/iolib/` |
| B9 | **`vault.py` halbfertig.** Hängt am deprecated `Data` (`vault.py:8`), Basisklasse großteils `NotImplementedError`, `FileSystemVault.reindex` **doppelt definiert** (`:372` und `:384` — die zweite überschreibt die erste still). | `iolib/vault.py` |
| B10 | **`DataFrameGroup` inkonsistent.** Speichert rohe pandas-Frames mit dict-basierter `{label, unit}`-Spaltenbeschreibung statt des `Metadata`-Modells; keine Anbindung an Store/Writer/Vault; keine Batch-/Hierarchie-Persistenz (nur `parent_sname`/`project_sname`-Strings). | `sclass/dataframegroup.py:53–63`, `base.py:41–42` |
| B11 | **Interne Duplikation.** Fünf Klassen-Factories (`cls_from_spec`/`sclass_factory`/`sdata_factory`/`spec_to_class`/`processdata_class_factory`); drei dtype-Rater in `metadata.py` neben der `dtypes`-SSOT (`:139/:363/:835`, einer mit bare `except:`); Accessor-Wildwuchs (`df`/`udf`/`sdf`/`mdf`/`dft`/`sdft`/`cmd`/`cmdf`/`md`). | `base.py:552/590/634`, `metadata.py` |
| B12 | **Typisierung und Sprache uneinheitlich.** `metadata.py`: 2/94 Methoden mit Return-Annotation; Docstrings de/en gemischt (Funktionskern deutsch, `dataframe`/`blob` englisch, `base`/`metadata` gemischt). Daten-Bug: Topologieklasse `"sdata.sclass:Prozess"` (`process.py:47`) fehlt in `BFO_IRIS` (`vocab.py:66–84`) und löst nie zu einer BFO-IRI auf. | `metadata.py`, `process.py:47` |
| B13 | **Packaging zweigleisig/veraltet.** Extras + Metadaten leben nur in `setup.py` (kein PEP-621-`[project]` in `pyproject.toml`); `requirements.txt` widerspricht dem schlanken Kern (schwere Pins, `pytz` statt `zoneinfo`, `suuid` fehlt); `tox.ini` kaputt (`envlist = py27,py37`, `flake8 twine/` — Copy-Paste-Fehler); `.travis.yml` toter CI-Provider; `upload_pypi.sh` konkurriert mit dem OIDC-Release-Pfad; `setup.cfg` nur deprecated `[aliases] test=pytest`; `setup.py` sagt „MIT/Apache-2.0", es liegt aber nur `LICENSE-MIT` bei. | Repo-Root |
| B14 | **`contrib/`-Vendoring = ~39 % der Codebasis.** 12 035 von 30 802 Zeilen sind gebündelte Fremdpakete (sortedcontainers, piexif, timeflake, …) — Wartungs- und Sicherheits-Altlast; pro Paket klären: echte Dependency, Extra oder Entfernen. | `sdata/contrib/` |

### P3 — Hygiene

| # | Befund | Beleg |
|---|--------|-------|
| B15 | **Eingecheckter Scratch/Junk (~76 Dateien).** `t/secret1` + `t/secret2` (!), `t.py`, `db.json` (TinyDB-Experiment, `tinydb` ist nicht mal deklariert), vendored `tabulate.py` (61 KB) im Root, `create_pyc_egg.py` (Fremdprojekt-Referenzen), `sdata.data.png`, **70 `.ipynb_checkpoints`-Dateien** (davon eine im Paket: `sdata/.ipynb_checkpoints/`). | `git ls-files` |
| B16 | **Peripherie-Code unter Kernniveau.** 125 `print()`-Aufrufe außerhalb von `contrib/` (Kern selbst sauber: nur `__main__`-Demos), 18 bare `except:`; `experiments/` (1608 Z.) mit 7–15-Zeilen-Stubs und `*_old`/`*_deprecated`-Dateien im Distributionspaket; ~130 Z. auskommentierter Code in `process.py:121–289`. | paketweit |
| B17 | **Doc-/CI-Leichen.** `docs/source/` (Sphinx-Reste ohne `conf.py`), `.github/workflows/greetings.yml` mit unkonfiguriertem Platzhaltertext; ~30 lokale + ~25 Remote-Branches Merge-Rückstand. | `docs/`, `.github/` |

### README-Designziele vs. Umsetzungsstand

Die Triage-Grundlage für Maßnahmenpaket C (Ziele einlösen **oder** ehrlich streichen):

| Design-Ziel (README:11–31) | Status | Anmerkung |
|---|---|---|
| Self-describing, Metadaten neben Daten | **Ja** | `_sdata`-Einbettung in allen Formaten |
| Physikalische Einheiten + Konversion | **Ja** | RFC 0006 |
| Standard-Metadatenformate | **Ja** | Metadata, JSON-LD/QUDT/BFO |
| hdf5 / csv | **Ja** (HDF5 optional) | CSV-Metadaten: B6 |
| Hierarchische Struktur (nesting groups) | **Rudimentär** | nur `parent_sname`-Strings; `DataFrameGroup` flach |
| Data format versions | **Nein** | B5 |
| netcdf, datacubes, series | **Nein / Teilweise** | series nur als 1-Spalten-Tabelle |
| Kompression zlib/blosc | **Teilweise / Nein** | Parquet-intern zstd; zlib nur im verwaisten Store |
| Encryption (gpg) | **Nein** | `rsa.py`/`pgp.py` isoliert, nie eingebunden; Roh-RSA ohne Padding wäre ohnehin unsicher |
| swmr, posix-paths, change management, Tensor-Libs | **Nein** | keine Spur |

## 5. Roadmap — drei Maßnahmenpakete

### Paket A — Quick-Fixes (kein eigenes RFC, je ein kleiner PR)

Reihenfolge nach Aufwand/Nutzen; alle strikt additiv bzw. reine Entfernungen:

1. **A1** `logging.basicConfig` aus `base.py:20`/`node.py:9` entfernen (B2).
2. **A2** `Metadata.from_json`: expliziter `ValueError` bei fehlender Quelle (B3).
3. **A3** `from_csv` konsumiert den `<sname>.meta.jsonld`-Sidecar automatisch, analog
   `image.from_file` (B6) — plus Roundtrip-Test.
4. **A4** Repo-Hygiene: `t/`, `t.py`, `db.json`, `tabulate.py`, `create_pyc_egg.py`,
   `upload_pypi.sh`, `sdata.data.png`, alle `.ipynb_checkpoints` entfernen;
   `.gitignore` um `.ipynb_checkpoints/` ergänzen (B15). **Achtung:** `t/secret1`/`t/secret2`
   bleiben in der Git-Historie — falls es echte Geheimnisse sind, rotieren.
5. **A5** Tote Konfigs löschen: `.travis.yml`, `setup.cfg`, `tox.ini` (oder auf
   `py39–py312` reparieren), `greetings.yml` konfigurieren oder entfernen (B13/B17).
6. **A6** `"Prozess"`-Topologieklasse → englischer Name + Eintrag in `BFO_IRIS`;
   mutable defaults in `process.py:132–137` beheben (B12).
7. **A7** Lizenzaussage konsolidieren: entweder `LICENSE-APACHE` beilegen oder
   überall nur MIT deklarieren (B13).

### Paket B — Folge-RFC-Kandidaten (in vorgeschlagener Reihenfolge)

1. **`DataFrameReader`-Protocol** (B4) — das von RFC 0007 angekündigte Gegenstück:
   `read()`-Vertrag, Backends Parquet/Store/SQL, `ReadReceipt`- bzw. Roundtrip-Symmetrie
   zu `WriteReceipt`. Höchster API-Nutzen, klar umrissen.
2. **Format-Versionierung** (B5) — `_sdata_format_version`-Feld getrennt von der
   Paketversion, Toleranzregeln (minor = lesbar, major = Migrations-Hook), Prüfung in
   allen `from_*`; Vorbild ist `PRAGMA user_version` + `migrate()` im Store
   (`json1sqlitestore.py:391–406`), nur eben auf Objektebene.
3. **Persistenz-Konsolidierung** (B8–B10) — *ein* Konzept auf `sclass`-Basis:
   `jsonsqlitestore.py` deprecaten (zlib-Frage explizit entscheiden), `vault.py` auf
   `sclass.DataFrame`/`Blob` portieren oder entfernen, `DataFrameGroup` auf das
   `Metadata`-Spaltenmodell heben und `write_group`-Semantik spezifizieren
   (offener Punkt aus RFC 0002 **und** 0007).
4. **Ablösung `deprecated.Data`** (B1) — Migrationstabelle Alt-API → Neu-API,
   `DeprecationWarning` ab nächstem Minor, Portierung der internen Abhängigkeiten
   (`doe.py`, `iolib/hdf.py`, `iolib/pud.py`), Entfernen in 2.0.
5. **Packaging-Modernisierung** (B13, B14) — PEP-621-`[project]` in `pyproject.toml`
   (Extras, Metadaten, `requires-python`), `requirements.txt` abschaffen oder auf
   Lockfile-Rolle reduzieren, `contrib/`-Triage (je Paket: Dependency/Extra/entfernen).

### Paket C — Deklarationsentscheidungen (Dokumentation statt Code)

1. **README-Ziele triagieren** (Tabelle §4): netcdf, datacubes, blosc, gpg, swmr,
   posix-paths, change management, Tensor-Libs — je Ziel entscheiden: *Roadmap-Issue*
   oder *explizites Nicht-Ziel*. Ein README, das seit 2020 Unerfülltes verspricht,
   kostet Glaubwürdigkeit.
2. **Sprach-Leitlinie** für Docstrings/Kommentare festlegen (de **oder** en) und bei
   Berührung migrieren (B12).
3. **Typisierungs-Leitlinie**: neue/angefasste Module vollständig annotieren; Ziel-Module
   zuerst `metadata.py` (2/94) und `dtypes.py` (0/40) — die SSOT verdient Signaturen.
4. **Fehler-Politik dokumentieren** (B7): lenient/strict klar im README/Docs verankern;
   erwägen, `strict=True` mittelfristig zum Default zu machen (Major-Release).
5. **Offene Punkte aus RFC 0001–0007** als Issues erfassen (u. a. HDF5-Spalten-Attribute
   nativ, `unit_system`-Persistenz aus RFC 0006, JPEG-Multi-Segment >64 KiB aus RFC 0005,
   Prüfsummen-Determinismus aus RFC 0004).

## 6. Ziele / Nicht-Ziele

**Ziele**

* Gemeinsames, belegtes Bild von Stärken und Schwächen als Referenz für Priorisierung.
* Verbindliche Reihenfolge der Folge-RFCs (Paket B) und der Quick-Fixes (Paket A).
* Ehrliche Triage der README-Designziele (Paket C).

**Nicht-Ziele**

* Keine API-Entwürfe — die liefern die Folge-RFCs (insbesondere Reader und
  Format-Versionierung).
* Keine Bewertung der Fachdomänen-Module (`isomme.py`, `pud.py`, DoE) über die
  Hygiene-Ebene hinaus.
* Kein Umbau der bewusst lokalen CI-Strategie.

## 7. Designentscheidungen

* **Meta-RFC statt Issue-Liste.** Die Befunde hängen zusammen (Reader ↔ Writer,
  Format-Version ↔ Roundtrips, Vault ↔ Store ↔ Group ↔ Legacy-`Data`); nur ein
  Dokument mit Priorisierung macht die Abhängigkeiten und die Reihenfolge explizit.
* **Priorisierung nach Schadenspotenzial, nicht nach Aufwand.** P1 = Korrektheit/
  Architektur (falsche Ergebnisse oder strukturelle Sackgassen), P2 = Drift-Risiko
  durch Duplikation, P3 = Reibung/Glaubwürdigkeit.
* **Quick-Fixes von RFCs getrennt.** B2/B3/B6 sind unstrittige Fehler — sie auf ein
  RFC warten zu lassen wäre Prozess-Overhead; umgekehrt verdient B1 (API-Ablösung)
  einen ordentlichen Migrationspfad statt eines Schnellschusses.
* **Reader vor Format-Versionierung.** Beide sind P1; der Reader ist aber klar
  umrissen (RFC 0007 hat vorgearbeitet), während die Format-Versionierung eine
  Grundsatzentscheidung über alle `from_*`-Pfade ist und vom Reader-Design profitiert.

## 8. Kompatibilität / Migration

Dieses RFC ändert selbst nichts. Für die Pakete gilt:

* **Paket A** ist verhaltensneutral bis auf A1 (Anwendungen, die sich unbewusst auf
  sdatas `basicConfig` verlassen haben, müssen ihr Logging selbst konfigurieren — das
  ist der korrekte Zustand) und A3 (`from_csv` liest jetzt vorhandene Sidecars; wer das
  nicht will, bekommt einen `sidecar=False`-Schalter).
* **Paket B** ist je RFC additiv, außer der `Data`-Ablösung (Nr. 4): die läuft über
  `DeprecationWarning` → Major-Release, mit dokumentierter Migrationstabelle.
* **Paket C** ändert nur Dokumentation und Leitlinien.

## 9. Risiken / offene Punkte

* **Momentaufnahme.** Die Belege (Datei:Zeile) altern mit dem Code; das RFC dokumentiert
  den Stand 2026-07-02 (v1.3.0) und wird nicht nachgepflegt — maßgeblich sind die
  Folge-RFCs.
* **`t/secret*` in der Historie.** Entfernen aus HEAD (A4) genügt nicht, falls die
  Dateien echtes Schlüsselmaterial enthalten; dann Rotation der betroffenen Schlüssel.
  History-Rewrite (filter-repo) nur, wenn der Bruch aller Clones akzeptabel ist —
  separate Entscheidung.
* **`contrib/`-Triage kann Nutzer brechen**, die direkt aus `sdata.contrib.*`
  importieren; die Packaging-RFC (Paket B, Nr. 5) braucht dafür eine
  Deprecation-Stufe.
* **100 %-Coverage-Aussage relativieren.** Die 100 % gelten für die per `omit`
  reduzierte Kernmenge; mit jeder Portierung aus Paket B (Vault, Group) müssen die
  betroffenen Module aus der `omit`-Liste in die Messung wandern — sonst wächst
  „ungemessener" Code unter dem 100 %-Etikett.
* **Reihenfolge Paket B ist ein Vorschlag.** Wer zuerst die `Data`-Ablösung angeht,
  reduziert zwar die größte Altlast, blockiert aber Monate — die vorgeschlagene
  Reihenfolge liefert früh sichtbaren API-Nutzen (Reader) und schiebt die
  Grundsatzarbeit (Format-Version) direkt dahinter.
