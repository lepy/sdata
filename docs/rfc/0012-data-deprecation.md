# RFC 0012 — Ablösung der `deprecated.Data`-Generation

| Feld        | Wert                                                                                     |
|-------------|------------------------------------------------------------------------------------------|
| Status      | Accepted — Stufe 1 implementiert (RFC 0008 Paket B, gemergt); Stufe 2 = 2.0                                                                                     |
| Datum       | 2026-07-02                                                                                |
| Autor       | lepy <lepy@tuta.io>                                                                       |
| Komponente  | `sdata/deprecated/data.py`, `sdata/__init__.py` (Export), interne Nutzer `sdata/iolib/pud.py`, `sdata/experiments/*` (`sdata/iolib/hdf.py` 2026-07-02 entfernt statt portiert) |
| Betrifft    | `Data` (Alt-Generation), `SDATACLS`/`__all__`, `Pud`, `TestProgram`/`Workbook`/`Image(alt)` |
| Vorgeschichte | RFC 0008 (Roadmap, B1); parallel zu RFC 0009–0011 (die die `sclass`-Ersatz-APIs liefern) |
| Validierung | verifiziert: `DeprecationWarning`-Tests, portierte interne Nutzer, Migrationstabelle in den Docs |

## 1. Zusammenfassung

sdata exportiert **zwei** Generationen von Datenobjekten: die neue
`sclass.DataFrame` (RFC 0003–0011) und die alte `Data` (`deprecated/data.py`,
1492 Zeilen). `Data` ist **Default-Export** (`SDATACLS["Data"]`, erste Position in
`__all__`, `__init__.py:123/130`) und **weiterhin load-bearing**: `Pud` (`pud.py`),
`hdf.py` und die `experiments/*` erben davon. Neue Nutzer sehen zwei überlappende
Serialisierungs-APIs ohne Wegweiser.

Dieses RFC definiert den **kontrollierten Ausstieg**: eine vollständige
**Migrationstabelle** (jede `Data`-Methode → `sclass`-Äquivalent, Ersatz oder
bewusstes Streichen), eine **Deprecation-Treppe** (`DeprecationWarning` ab dem
nächsten Minor, Entfernung im Major 2.0), und die **Portierung der internen
Nutzer** auf `DataFrame`/Writer/Reader. Es ist der letzte große Punkt der
RFC-0008-Roadmap und baut bewusst auf den fertigen Ersatz-APIs aus RFC 0009–0011
auf.

## 2. Motivation / Kontext

* **Zwei APIs, ein Zweck.** `Data` und `DataFrame` serialisieren beide Tabellen +
  Metadaten, mit unterschiedlichen Signaturen. Das ist die in RFC 0008 als **B1**
  markierte Hauptlast: Verwirrung, doppelte Wartung, Drift.
* **`Data` ist nicht toter Code.** Solange `Pud`/`hdf.py`/`experiments` davon
  erben, kann `Data` nicht einfach gelöscht werden — es braucht einen echten
  Migrationspfad, keinen Schnellschuss (RFC 0008 §5, Paket B, Nr. 4).
* **Der Ersatz ist jetzt vollständig.** RFC 0009 (Reader), 0010 (Format-Version),
  0011 (Store/Group/Batch) schließen die letzten Lücken, die `DataFrame` gegenüber
  `Data` hatte. Was bleibt, sind **Bequemlichkeits-Serialisierer** (xlsx, sqlite,
  url, html, folder), die `Data` hat und `DataFrame` (noch) nicht — die entscheidet
  dieses RFC einzeln (§5).
* **Default-Export prägt Gewohnheit.** Solange `import sdata; sdata.Data` das Erste
  ist, was `__all__` zeigt, lernen neue Nutzer die falsche Klasse. Der Export-Swap
  ist Teil der Ablösung.

## 3. Ziele / Nicht-Ziele

**Ziele**

* **Migrationstabelle** `Data` → `DataFrame`/Writer/Reader für **jede** öffentliche
  Methode (§5), als Doku-Seite dauerhaft verankert.
* **Deprecation-Treppe:** `DeprecationWarning` bei `Data()`-Instanziierung (nächster
  Minor); `DataFrame` als Default-Export voranstellen; Entfernung von `Data` in 2.0.
* **Interne Nutzer portieren:** `Pud` und `hdf.py` auf `DataFrame` umstellen (bzw.
  klar als deprecated markieren); `experiments/*` sind bereits `omit`/experimentell
  und werden nur mitgezogen, nicht priorisiert.
* **Lücken schließen oder streichen:** die `Data`-only-Serialisierer (§5) entweder
  auf `DataFrame` portieren (wenn wertvoll) oder als Nicht-Ziel dokumentieren
  (Ersatz über Writer/Reader oder pandas direkt).

**Nicht-Ziele**

* **Keine** Sofort-Entfernung von `Data` in diesem RFC — nur die Treppe.
* Keine Neuimplementierung der `experiments/*`-Domänenklassen (die hängen an
  Domänenlogik, nicht nur an `Data`).
* Keine Änderung am `DataFrame`-Serialisierungsformat (RFC 0009–0011 gelten).
* Kein Excel-/HTML-Feature-Ausbau über das hinaus, was `Data` schon konnte.

## 4. Ist-Zustand (Beleg)

| Ort | Kopplung | Beleg |
|-----|----------|-------|
| Default-Export | `Data` erste Position in `__all__`, in `SDATACLS` | `__init__.py:123/130` |
| `Pud` | `class Pud(Data)`, `Data.__init__` | `pud.py:12/41` (nicht in `omit`) |
| `hdf.py` | `from sdata import Data` | `hdf.py:10` (in `omit`) |
| `experiments` | `TestProgram(Data)`/`Workbook(Data)`/`Image(Data)` | `experiments/__init__.py:20`, `workbook.py:19`, `image_old.py:24` (in `omit`) |
| Größe | 1492 Zeilen Alt-Code | `deprecated/data.py` |

## 5. Migrationstabelle (Data → sclass)

| `Data`-Methode | Ersatz | Entscheidung |
|----------------|--------|--------------|
| `to_parquet`/`from_parquet` | `DataFrame.to_parquet`/`from_parquet` | **1:1** vorhanden |
| `to_csv`/`from_csv` | `DataFrame.to_csv`/`from_csv` (+ Sidecar, RFC 0008 A3) | **1:1** (reicher) |
| `to_json`/`from_json` | `DataFrame.to_dict`+`json` / `from_dict` | **1:1** vorhanden |
| `to_dataframe` | `DataFrame.to_dataframe` | **1:1** vorhanden |
| `to_hdf5`/`from_hdf5` | `DataFrame.to_hdf`/`from_hdf` (RFC 0002) | **1:1** vorhanden |
| `to_sqlite`/`from_sqlite` | `SqlWriter`/`SqlReader` (RFC 0007/0009) | **ersetzt** (Interface) |
| `to_xlsx`/`from_xlsx`/`to_xlsx_base64`/`to_xlsx_byteio` | — | **portieren** nach `DataFrame` **oder** streichen (Empfehlung: dünner `to_xlsx`/`from_xlsx` über `openpyxl`-Extra, Rest streichen) |
| `to_html` | `DataFrame.df.to_html` (pandas) | **streichen** (pandas deckt es) |
| `from_url` | `DataFrame.from_*` + `fsspec`/`requests` am Aufrufer | **streichen** (Blob/fsspec, RFC 0004) |
| `to_folder`/`from_folder` | `write_group`/`read_group` (RFC 0011) bzw. `ParquetWriter`-Verzeichnismodus | **ersetzt** (Batch) |
| `to_html`-Styling | — | **streichen** |

> **Leitlinie:** Was `DataFrame`/Writer/Reader schon können → 1:1 verweisen. Was nur
> pandas-Zucker war (`to_html`, `from_url`) → streichen mit Einzeiler-Ersatz in der
> Doku. Excel bleibt als schmales optionales Feature erhalten, weil es einen echten
> Austauschbedarf deckt, den pandas nicht in einem Aufruf löst.

## 6. Deprecation-Treppe

**Stufe 1 (nächster Minor, = B4b):**

* `Data.__init__` löst ein `DeprecationWarning` aus („use sdata.sclass.dataframe.
  DataFrame; removal in sdata 2.0"), einmalig pro Prozess sinnvoll gefiltert.
* `DataFrame` wird **Default-Export**: erste Position in `__all__`, in `SDATACLS`
  bleibt `Data` erhalten (Deserialisierung alter Objekte!), aber `DataFrame` führt.
* **Interne Nutzer portieren:** `Pud` erbt künftig von `DataFrame` (oder wird selbst
  deprecated, falls die Domäne ruht); `hdf.py` nutzt `DataFrame.to_hdf`/`from_hdf`.
* Migrationstabelle (§5) als Doku-Seite (`usage/migration-data.md`) + README-Notiz.

**Stufe 2 (Major 2.0):**

* `Data` und `deprecated/data.py` entfernt; `SDATACLS["Data"]` fällt weg oder zeigt
  über eine Format-Migration (RFC 0010) auf `DataFrame` beim Deserialisieren.
* `experiments/*`-Altklassen entfernt oder auf `DataFrame` portiert.
* `from_url`/`to_html`/xlsx-Extras final gemäß §5.

## 7. Deserialisierung alter `Data`-Objekte

Ein per `Data.to_json`/`to_hdf5` geschriebenes Objekt trägt `_sdata_class =
"...:Data"`. Nach der Entfernung muss `from_dict` es weiter lesen können:

* **RFC 0010 nutzen:** eine registrierte Format-Migration bildet ein `Data`-Payload
  (v1) auf ein `DataFrame`-Payload ab (Klassen-Spec umschreiben, Datenlayout
  angleichen) — genau der Anwendungsfall der Migrations-Treppe.
* Solange `Data` in Stufe 1 noch existiert, bleibt `SDATACLS["Data"]` als
  Fallback; die Migration wird **vor** dem 2.0-Cut scharfgeschaltet und getestet.

## 8. Designentscheidungen / Optionen

* **Treppe statt Sofort-Löschung:** `Data` ist load-bearing; ein Minor mit Warnung
  gibt Downstream Zeit. Konsistent zur Store-Deprecation (RFC 0011).
* **`DataFrame` als Default-Export, `Data` bleibt in `SDATACLS`:** der Export lenkt
  neue Nutzer richtig, die Registry hält die Deserialisierung alter Objekte am
  Leben (bis die Format-Migration greift).
* **Excel behalten, HTML/URL streichen:** Excel-Austausch ist ein realer Bedarf ohne
  pandas-Einzeiler; `to_html`/`from_url` sind dünner pandas-/fsspec-Zucker.
* **`Pud` erbt künftig `DataFrame`:** die Domänenklasse verliert nichts (die
  `ATTRIBUTES`-Liste ist Metadaten-Schema, das `MetadataSchema`/`TableSchema`
  ausdrücken; RFC 0008 C-Ebene) — oder wird deprecated, falls die Domäne ruht.
* **`experiments/*` nachrangig:** bereits `omit`/experimentell; sie werden in 2.0
  mitgezogen, blockieren aber Stufe 1 nicht.

## 9. Tests / Coverage (geplant)

* **Stufe 1:** `Data()` löst `DeprecationWarning` (`pytest.warns`); `import sdata`
  exportiert `DataFrame` an erster Stelle; `SDATACLS["Data"]` weiterhin auflösbar
  (Deserialisierung eines alten `Data`-Dicts).
* **Interne Nutzer:** `Pud` funktioniert nach Portierung (oder warnt konsistent);
  `hdf.py` nutzt den `DataFrame`-HDF5-Pfad.
* **Migrationstabelle:** je 1:1-Zeile ein Roundtrip-Test über das `DataFrame`-
  Äquivalent (die meisten existieren schon).
* **Format-Migration (Stufe 2, vorbereitet):** ein `Data`-Payload wird über die
  RFC-0010-Treppe zu einem lesbaren `DataFrame` (Test schon in Stufe 1 als
  `xfail`/vorbereitet).

## 10. Kompatibilität / Migration

* **Stufe 1 ist nicht-brechend** außer der Warnung: bestehender Code läuft weiter,
  wird aber auf die Ablösung hingewiesen. Der Export-Swap ändert die Reihenfolge in
  `__all__`, nicht die Verfügbarkeit von `Data`.
* **Alte serialisierte Objekte** bleiben lesbar (SDATACLS-Fallback → später
  Format-Migration).
* **Stufe 2 ist ein Major-Break** (Entfernung) — angekündigt, mit Migrationstabelle
  und Format-Migration abgesichert.

## 11. Risiken / offene Punkte

* **`Pud`-Portierung:** die `ATTRIBUTES`-Domänenliste muss auf ein
  `MetadataSchema`/`TableSchema` abgebildet werden; falls die Domäne (Zugversuch)
  aktiv genutzt wird, braucht das Sorgfalt — sonst deprecaten.
* **Excel-Umfang:** `Data` hat vier xlsx-Methoden; die Portierung sollte auf ein
  schlankes `to_xlsx`/`from_xlsx` reduzieren, nicht alle vier spiegeln.
* **Format-Migration `Data`→`DataFrame`** ist der kniffligste Teil (unterschiedliches
  `to_dict`-Layout) und gehört vollständig **vor** den 2.0-Cut, mit Tests.
* **`experiments/*`** könnten mehr Domänenlogik tragen als es scheint; vor Entfernung
  in 2.0 einzeln prüfen.
* **Downstream-Nutzer** außerhalb des Repos, die `sdata.Data` direkt verwenden,
  sehen erst die Warnung, dann (2.0) den Bruch — die Migrationstabelle ist ihr
  Wegweiser.
