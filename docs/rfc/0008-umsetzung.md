# RFC 0008 — Umsetzungsstand (Arbeitscheckliste)

Arbeitsstand zur Roadmap aus [RFC 0008](0008-bestandsaufnahme-roadmap.md).
Diese Datei ist die **Wahrheitsquelle für den Umsetzungs-Loop**: pro Iteration wird
genau **ein** offener Punkt vollständig umgesetzt und hier abgehakt (`[x]` + PR/Commit).

## Arbeitsregeln (gelten für jede Iteration)

1. Genau **einen** offenen Punkt nehmen — den obersten nicht abgehakten, sofern keine
   Abhängigkeit dagegen spricht.
2. Eigener Branch je Punkt (`fix/…`, `chore/…`, `feat/…`, `docs/…` — Konvention wie
   bisherige Historie, deutsche Commit-Messages).
3. `make ci` muss grün sein, bevor abgehakt wird (bei reinen Doku-/Repo-Punkten:
   `mkdocs build` bzw. Plausibilitätsprüfung).
4. Punkt hier abhaken und Branch/Commit notieren; PR erstellen, **nicht selbst mergen**.
5. Bei Paket-B-Punkten: erst das RFC (Draft) schreiben, erst in der Folge-Iteration
   implementieren — RFC-Review bleibt Menschensache.
6. Erst wenn **alle** Punkte abgehakt sind, endet der Loop.

## Paket A — Quick-Fixes (je 1 Iteration)

- [x] **A1** `logging.basicConfig` entfernen (`base.py:20`, `node.py:9`), nur
  `getLogger(__name__)` (+ `NullHandler` im Paket-Init) — PR #94
- [x] **A2** `Metadata.from_json`: expliziter `ValueError` bei fehlender Quelle
  (`metadata.py:576–592`) + Test — PR #95
- [ ] **A3** `from_csv` konsumiert `<sname>.meta.jsonld`-Sidecar automatisch (analog
  `image.from_file`), Schalter `sidecar=False`, Roundtrip-Test
- [ ] **A4** Repo-Hygiene: `t/`, `t.py`, `db.json`, `tabulate.py`, `create_pyc_egg.py`,
  `upload_pypi.sh`, `sdata.data.png`, alle `.ipynb_checkpoints` entfernen;
  `.gitignore` um `.ipynb_checkpoints/` ergänzen. Hinweis RFC §9: `t/secret*` bleiben
  in der Historie — **falls echtes Schlüsselmaterial: melden, nicht still entfernen**
- [ ] **A5** Tote Konfigs: `.travis.yml`, `setup.cfg` löschen; `tox.ini` löschen oder
  auf py39–py312 reparieren; `greetings.yml` konfigurieren oder entfernen
- [ ] **A6** `"sdata.sclass:Prozess"` → englischer Name + `BFO_IRIS`-Eintrag
  (`process.py:47`, `vocab.py`); mutable defaults `process.py:132–137` beheben
- [ ] **A7** Lizenzaussage konsolidieren (`LICENSE-APACHE` beilegen **oder** überall
  nur MIT deklarieren)

## Paket B — Folge-RFCs (je Punkt: RFC-Iteration, dann Implementierungs-Iteration(en))

- [ ] **B1a** RFC 0009 `DataFrameReader`-Protocol schreiben (Draft)
- [ ] **B1b** RFC 0009 implementieren + Tests (Backends: Parquet/Store/SQL, Symmetrie
  zu `WriteReceipt`)
- [ ] **B2a** RFC 0010 Format-Versionierung schreiben (`_sdata_format_version`,
  Toleranz-/Migrationsregeln)
- [ ] **B2b** RFC 0010 implementieren (Feld + Prüfung in allen `from_*`, Migrations-Hook)
- [ ] **B3a** RFC 0011 Persistenz-Konsolidierung schreiben (Store-Zwilling, Vault,
  `DataFrameGroup`/`write_group`)
- [ ] **B3b** RFC 0011 implementieren (inkl. `omit`-Liste: portierte Module in die
  Coverage-Messung aufnehmen)
- [ ] **B4a** RFC 0012 Ablösung `deprecated.Data` schreiben (Migrationstabelle,
  Deprecation-Stufen)
- [ ] **B4b** RFC 0012 umsetzen Stufe 1: `DeprecationWarning` + interne Abhängigkeiten
  portieren (`doe.py`, `iolib/hdf.py`, `iolib/pud.py`)
- [ ] **B5a** RFC 0013 Packaging-Modernisierung schreiben (PEP 621, Extras,
  `contrib/`-Triage)
- [ ] **B5b** RFC 0013 implementieren (`[project]`-Tabelle, `requirements.txt`-Rolle,
  contrib-Entflechtung mit Deprecation-Stufe)

## Paket C — Deklarationen/Doku (je 1 Iteration)

- [ ] **C1** README-Designziele triagieren (Tabelle RFC §4): je Ziel Roadmap-Punkt
  oder explizites Nicht-Ziel; README entsprechend umschreiben
- [ ] **C2** Sprach-Leitlinie Docstrings/Kommentare festlegen und dokumentieren
- [ ] **C3** Typisierungs-Leitlinie dokumentieren; `metadata.py` und `dtypes.py`
  annotieren
- [ ] **C4** Fehler-Politik (lenient/strict) in README/Docs verankern; strict-Default
  als 2.0-Kandidat notieren
- [ ] **C5** Offene Punkte aus RFC 0001–0007 als Issues/Roadmap-Liste erfassen

## Protokoll

| Datum | Punkt | Branch/Commit | Anmerkung |
|-------|-------|---------------|-----------|
| 2026-07-02 | Vorbereitung | `docs/rfc-0008-bestandsaufnahme` | RFC 0008 + Checkliste + Nav committet; Branch baut auf der unge-mergten RFC-0007-Doku (`c5cd053`) auf, damit die Nav konsistent bleibt; PR #93 |
| 2026-07-02 | A1 | `fix/logging-basicconfig` (PR #94) | basicConfig raus aus `base.py`/`node.py`/`iolib/owncloudfs.py`, Modul-Logger in `node.py`, NullHandler im Paket-Init; `did/*`-CLI-`main()` bewusst belassen; `make ci` grün (100 %) |
| 2026-07-02 | A2 | `fix/metadata-from-json` (PR #95) | `from_json` ohne Quelle → `ValueError` (statt `UnboundLocalError`); Fallback filepath-fehlt+jsonstr bleibt; 3-Fälle-Test; `make ci` grün (100 %) |
