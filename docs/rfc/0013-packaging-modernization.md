# RFC 0013 — Packaging-Modernisierung (PEP 621, Extras, `contrib`-Triage)

| Feld        | Wert                                                                                     |
|-------------|------------------------------------------------------------------------------------------|
| Status      | Draft                                                                                     |
| Datum       | 2026-07-02                                                                                |
| Autor       | lepy <lepy@tuta.io>                                                                       |
| Komponente  | `pyproject.toml` (`[project]`), `setup.py` (auflösen), `requirements.txt` (Rolle klären), `sdata/contrib/*` (Triage) |
| Betrifft    | Metadaten/Extras-Deklaration, Versions-Single-Source, gebündelte Fremdpakete |
| Vorgeschichte | RFC 0008 (Roadmap, B13/B14); RFC 0011 (entfernte `node.py` → `simple_graph_db` verwaist) |
| Validierung | geplant: `python -m build` erzeugt identische Wheel-Metadaten; `pip install .[extra]` je Extra; Import-Rauchtests |

## 1. Zusammenfassung

sdata deklariert Metadaten und Extras **ausschließlich** in `setup.py`
(`install_requires`, `extras_require`, `python_requires`); `pyproject.toml` trägt
nur Build-Backend + Test-/Coverage-Config, **kein** `[project]`-Table. Moderne
Tools (pip/uv/build) bevorzugen PEP 621; die Doppelpflege ist ein Drift-Risiko.
Parallel widerspricht `requirements.txt` der „schlanker Kern"-Philosophie (schwere
Pins, `pytz` statt stdlib-`zoneinfo`, **ohne** `suuid`), und `sdata/contrib/` bündelt
**~39 %** der Codebasis als vendorierte Fremdpakete — von denen nach RFC 0011
mehrere **gar nicht mehr importiert** werden.

Dieses RFC überführt die Deklaration nach **PEP 621** (`[project]` in
`pyproject.toml`), klärt die Rolle von `requirements.txt`, und triagiert `contrib/`
paketweise (entfernen / echte Abhängigkeit / vendoriert behalten).

## 2. Motivation / Kontext

* **Zwei Deklarationsorte.** Extras/Metadaten in `setup.py`, Build-Config in
  `pyproject.toml` — Änderungen müssen an einem konsistent gehalten werden, den
  Tools teils ignorieren. PEP 621 ist der Standard-Ort.
* **`requirements.txt` widerspricht dem Kern.** `setup.py` hält den Kern schlank
  (`numpy`/`pandas`/`suuid>=0.2.0`), `requirements.txt` listet `xlrd`/`openpyxl`/
  `xlsxwriter`/`pytz`/`requests`/`tabulate`/`tables`/`Pillow` — schwere Pins, die
  Extras sein sollten, und **kein** `suuid`. Es führt in die Irre.
* **`contrib/` ist Wartungslast.** 12 035 Zeilen gebündelter Fremdcode; einige
  Pakete werden **null**-mal importiert (verwaist, u. a. `simple_graph_db` seit der
  `node.py`-Entfernung in RFC 0011), andere genau einmal. Jedes vendorierte Paket
  ist ungepatchte Sicherheits-/Wartungsfläche.
* **Versions-Single-Source erhalten.** `__version__` lebt in `sdata/__init__.py`;
  `setup.py` liest sie. Der Umzug darf diese eine Quelle **nicht** duplizieren
  (PEP 621 `dynamic = ["version"]`).

## 3. Ist-Zustand (Beleg)

**Extras (nur in `setup.py`):** `did`(no-op), `http`(requests), `excel`(openpyxl/
xlsxwriter/tabulate), `hdf`(tables), `sql`(sqlalchemy), `parquet`(pyarrow),
`blob`(fsspec), `units`(pint), `rdf`(rdflib), `schema`(jsonschema).

**`contrib/`-Nutzung (Importer außerhalb `contrib/`):**

| Paket | Importer | Triage-Vorschlag |
|-------|----------|------------------|
| `attrdict` | **0** | entfernen |
| `semver.py` | **0** | entfernen |
| `timeflake` | **0** | entfernen |
| `simple_graph_db` | **0** (seit RFC 0011) | entfernen |
| `piexif` | 1 | prüfen: `imagemeta` ist Pillow-frei (RFC 0005) → evtl. entfernbar |
| `sobol_seq.py` | 1 | Extra `doe` **oder** vendoriert behalten |
| `ranger` | 1 | prüfen (nur 1 Nutzer) |
| `sortedcontainers` | 1 | echte Abhängigkeit **oder** vendoriert behalten |
| `sqlitedict.py` | 1 | prüfen (nur 1 Nutzer) |

## 4. Entwurf

### 4.1 PEP-621-`[project]` in `pyproject.toml`

```toml
[project]
name = "sdata"
dynamic = ["version"]                 # aus sdata/__init__.py (Single Source)
description = "Structured data format for open science"
readme = "README.md"
license = { text = "MIT" }            # RFC 0008 A7
requires-python = ">=3.9"
authors = [{ name = "Ingolf Lepenies", email = "lepy@tuta.io" }]
dependencies = ["numpy", "pandas", "suuid>=0.2.0"]

[project.optional-dependencies]
http = ["requests"]
excel = ["openpyxl", "xlsxwriter", "tabulate"]
hdf = ["h5py"]
sql = ["sqlalchemy"]
parquet = ["pyarrow"]
blob = ["fsspec"]
units = ["pint"]
rdf = ["rdflib"]
schema = ["jsonschema"]
did = []                              # no-op, für Kompatibilität erhalten

[tool.setuptools.dynamic]
version = { attr = "sdata.__version__" }

[tool.setuptools.packages.find]
include = ["sdata*"]
```

`setup.py` entfällt **oder** schrumpft auf einen Shim (`from setuptools import
setup; setup()`), bis Downstream-Tooling nachzieht. Die Extras/Metadaten liegen dann
an **einem** Ort; `dynamic = ["version"]` hält die Single Source in
`sdata/__init__.py`.

### 4.2 `requirements.txt`

Zwei saubere Optionen (Entscheidung im Implementierungs-PR):

* **Entfernen (empfohlen):** die Extras decken alles ab; `pip install -e ".[…]"` ist
  der dokumentierte Weg (so macht es `ci/local-ci.sh` bereits). `requirements.txt`
  ist nur noch eine irreführende Zweitliste.
* **Auf Dev-Lock reduzieren:** falls ein reproduzierbares Entwickler-Env gewünscht
  ist, wird es ein **`requirements-dev.txt`** mit klarer Rolle (gepinnte Test-/
  Lint-Tools), nicht die Kern-Deklaration.

### 4.3 `contrib`-Triage

* **Verwaist entfernen (0 Importer):** `attrdict`, `semver.py`, `timeflake`,
  `simple_graph_db` — tote gebündelte Pakete raus (mit MANIFEST-/omit-Bereinigung).
* **Genutzte prüfen (1 Importer):** je Paket entscheiden — echte
  Abhängigkeit (in `dependencies`/Extra) **oder** vendoriert behalten (mit
  dokumentiertem Grund: Pin-Stabilität, kein PyPI-Äquivalent, Lizenz). `piexif`
  besonders prüfen: `imagemeta` (RFC 0005) ist Pillow-frei, der eine Nutzer könnte
  ein Alt-Pfad sein.
* **Behalten heißt begründen:** jedes verbleibende `contrib`-Paket bekommt eine
  Kopfzeile „warum vendoriert" — sonst wächst die Last unkontrolliert weiter.

## 5. Designentscheidungen / Optionen

* **PEP 621, nicht setup.cfg:** `pyproject.toml` ist der eine moderne Ort; `setup.cfg`
  wurde in RFC 0008 A5 bereits entfernt. `dynamic = ["version"]` statt Version-Copy.
* **`setup.py`-Shim vs. Löschen:** ein minimaler Shim hält exotisches Downstream-
  Tooling am Leben; sobald `python -m build` + `pip` reichen (tun sie), kann er weg.
  Entscheidung im PR, kein Muss für den Umzug.
* **`did`-Extra als No-op behalten:** `pip install sdata[did]` darf nicht brechen,
  auch wenn `sdata.did` pure Python ist (Rückwärtskompatibilität).
* **Triage vor Entfernung:** kein contrib-Paket wird blind gelöscht; „0 Importer"
  ist Bedingung fürs Entfernen, „1 Importer" löst eine bewusste Behalten/Ersetzen-
  Entscheidung aus. Entfernen bündelt sich in einem Schritt mit `log()`-Doku, was
  wegfiel (RFC-0008-Prinzip „no silent caps").
* **`requirements.txt` entfernen** statt reparieren: eine korrekte Zweitliste bliebe
  Doppelpflege; die Extras sind die Wahrheit.

## 6. Tests / Validierung (geplant)

* **Build-Äquivalenz:** `python -m build` erzeugt ein Wheel mit denselben Kern-
  Dependencies + Extras wie zuvor (`twine check`, Metadaten-Diff vor/nach).
* **Install je Extra:** `pip install ".[parquet]"`, `".[rdf]"`, … in einem frischen
  Env; Import-Rauchtest der jeweiligen Fähigkeit.
* **Version:** `sdata.__version__` == Wheel-Version (dynamic-Auflösung greift).
* **contrib-Entfernung:** nach dem Entfernen der 0-Importer-Pakete bleibt die Suite
  grün (Beweis, dass sie wirklich verwaist waren); MANIFEST/omit konsistent.
* **CI-Pfad:** `ci/local-ci.sh` (`pip install -e ".[did,parquet,blob,sql]"`) läuft
  unverändert gegen die neue Deklaration.

## 7. Kompatibilität / Migration

* **Nutzer:** `pip install sdata` / `sdata[extra]` funktioniert unverändert (gleiche
  Namen). Wer `sdata.contrib.<verwaist>` direkt importiert hat, sieht einen Bruch —
  daher nur **0-Importer**-Pakete ohne Deprecation-Stufe entfernen; genutzte mit
  Vorlauf.
* **Downstream-Build-Tooling:** ein `setup.py`-Shim federt exotische Fälle ab.
* **Versions-Single-Source** bleibt `sdata/__init__.py` — kein Prozesswechsel für
  Releases (`RELEASING.md`/OIDC unverändert).

## 8. Risiken / offene Punkte

* **`dynamic`-Version-Auflösung** muss mit dem setuptools-Backend exakt greifen
  (`attr = "sdata.__version__"`); ein Fehlgriff bräche Releases — daher Build-Test
  **vor** dem Merge.
* **`piexif`/`sortedcontainers`/`sqlitedict`-Einzelnutzer:** vor einer Umstellung auf
  echte Dependencies prüfen, ob die vendorierte Version gepatcht/gepinnt ist (ein
  PyPI-Wechsel kann Verhalten ändern).
* **`requirements.txt`-Entfernung** trifft evtl. Doku/CI, die sie referenziert —
  vorher grep (die kanonische CI nutzt bereits Extras).
* **MANIFEST.in** listet contrib-Ressourcen (`simple_graph_db/*.sql`,
  `sortedcontainers/LICENSE`) — beim Entfernen mitpflegen.
* **Reihenfolge:** dieser Umzug ist additiv zur Funktionalität; er sollte nach den
  inhaltlichen RFCs (0009–0012) kommen, damit die Extras-Liste stabil ist — genau
  die Position am Ende der RFC-0008-Roadmap.
