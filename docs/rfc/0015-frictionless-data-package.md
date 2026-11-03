# RFC 0015 — Frictionless Data Package: Spec-konformer Export & Fremdpaket-Import

| Feld        | Wert                                                                                     |
|-------------|------------------------------------------------------------------------------------------|
| Status      | Draft — Vorschlag, **v3** nach zwei adversariellen Review-Runden (das Basis-Bündel aus der RFC-0004-Runde ist implementiert) |
| Datum       | 2026-07-14                                                                                |
| Autor       | lepy <lepy@tuta.io>                                                                       |
| Komponente  | `sdata/sclass/dataframe.py` (`to_datapackage`/`from_datapackage`); neu: `sdata/sclass/dataframegroup.py` (Group-Paket), `Blob.from_datapackage` |
| Betrifft    | Deskriptor-Vollständigkeit, Import fremder Pakete, Verzeichnisform, Multi-Resource-Pakete |
| Vorgeschichte | RFC 0004 (Bündel + Checksummen), RFC 0007/0009 (Writer/Reader), RFC 0010 (Format-Versionierung), RFC 0011 (`DataFrameGroup`), RFC 0014 (`unit_system`-Persistenz) |
| Validierung | — (Entwurf; Testplan in §8)                                                               |
| Referenz    | <https://specs.frictionlessdata.io/data-package/> (v1); Table Schema, Data Resource, Tabular Data Package ebd. |

> **Adversarieller Review, Runde 1 (v1 → v2).** Der v1-Entwurf wurde gegen den
> Normtext der Spezifikation und den Code geprüft; das deckte zwei
> **Spec-Brüche** (einen davon im heutigen Code), eine Sicherheitslücke und
> mehrere Überbehauptungen auf:
>
> | # | v1-Problem (Entwurf) | v2-Antwort |
> |---|----------------------|------------|
> | F1 | §5.4 mischte `Blob`-Ressourcen in ein `tabular-data-package` — die Spec fordert aber: „Each `resource` MUST be a Tabular Data Resource". | Profil-Herabstufung: sobald eine nicht-tabellarische Resource im Paket ist, ist das Paket ein `data-package`; tabellarische Mitglieder behalten ihr Resource-Profil (§5.4). |
> | F2 | **Betrifft auch den heutigen Code:** `fmt="parquet"` emittiert `profile: tabular-data-resource`, die Spec fordert aber „If non-inline: **Be a CSV file**". Ein `.spq` unter Tabular-Profil ist v1-ungültig; das v1-Testziel „`frictionless.validate()` grün für **alle** Pakete" war so unerfüllbar. | CSV ist das einzige Interop-Format unter Tabular-Profil. Parquet-Pakete werden als `data-package`/`data-resource` deklariert (Schema bleibt als erlaubte Custom Property). Validierungs-Erwartung je Format getrennt (§5.1, §8, D7). |
> | F3 | Verzeichnis-Import ohne Pfad-Härtung — die Spec verbietet absolute Pfade und `../` ausdrücklich („MUST NOT be used"), v1 erwähnte das nicht → Path-Traversal-Risiko. | Import erzwingt Containment: `path` muss relativ sein, ohne `..`, aufgelöst innerhalb der Paketwurzel; sonst `ValueError` (§5.2). |
> | F4 | §1 behauptete „liest es verlustfrei zurück" — falsch für CSV: dtypes gehen verloren (`datetime64`→object, nullable `Int64`→float64), denn der `"sdata"`-Block stellt nur **Metadaten** her, `pd.read_csv` rät die Typen. | Typ-Wiederherstellung beim CSV-Lesen für **eigene und fremde** Pakete: eigene aus den dtype-Werten der `column_metadata` (liegen im `"sdata"`-Block), fremde aus dem Table Schema (§5.2). Formulierungen präzisiert. |
> | F5 | Fremd-CSV-Parsing ignorierte `dialect` (Pflicht-Property bei abweichendem Dialekt — Semikolon-CSVs sind in DE-Portalen der Normalfall) und `missingValues` (z. B. `"NA"`, `"-99"`) → stumm falsche Daten. | `dialect`-Mapping und `missingValues` → `na_values` (§5.2; in v3 präzisiert, s. F18). |
> | F6 | Group-Roundtrip brach die Schlüssel-Identität: Resource-`name` ist zwangs-lowercase, Group-Keys sind snames mit Großbuchstaben (`DataFrame__…`) → nach dem Rundtrip andere Keys. | Original-Key reist im Resource-`"sdata"`-Block; der Resource-`name` bleibt reiner Slug (§5.4). |
> | F7 | Unerwähnte Asymmetrie: `fmt="csv"` verwirft einen Nicht-Default-Index (kanonische CSV, RFC 0004), `fmt="parquet"` erhält ihn. | Dokumentiert + `logger.warning` beim CSV-Export eines Nicht-Default-Index (§5.1, D8). |
> | F8 | „`id` wird beim Import wiederhergestellt" war handgewedelt: fremde `id`s (DOI, beliebiger String) passen nicht in eine SUUID. | Eigene Pakete: Identität kommt aus dem `"sdata"`-Block. Fremde `id` wird als User-Attribut `datapackage_id` bewahrt (§5.2). |
> | F9 | `created` ← `_sdata_ctime` ohne Begründung; die Spec meint die **Paket**-Erstellung. | Bewusste Entscheidung: Objekt-`ctime` statt Schreibzeitpunkt → deskriptor-identische Wiederholexporte (D9). |
>
> **Adversarieller Review, Runde 2 (v2 → v3).** Die zweite Runde prüfte v2
> gegen Code-Realitäten (`metadata.py`, `base.py`, `dataframegroup.py`) und
> die Resource-Spec-Feinheiten. Ergebnis: ein Design-Loch, eine
> Identitätskollision und sieben Präzisierungen:
>
> | # | v2-Problem | v3-Antwort |
> |---|------------|------------|
> | F10 | §5.4 versprach „`Blob` als Resource für nicht-tabellarische **Mitglieder**" — aber `DataFrameGroup` hält ausschließlich DataFrames (`data['dataframes']`; `add()` wrappt alles). Das Feature hatte keinen API-Träger. | Explizites `assets=[blob, …]`-Argument auf `to_datapackage` (DataFrame **und** Group) statt Group-Umbau; Import über `Blob.from_datapackage(source, resource=…)`. `DataFrameGroup.from_datapackage` überspringt Non-Tabular-Resources mit Warnung und nennt sie im Log (§5.4, D11). |
> | F11 | Import ignorierte das Resource-`encoding` — `latin-1`/`cp1252`-CSVs (in DE-Portalen üblich) kämen als Mojibake oder `UnicodeDecodeError` an. | `encoding` → `read_csv(encoding=…)`, Default `utf-8` (§5.2). |
> | F12 | Der F4-Fix las eigene dtypes aus den `column_metadata`-Werten — die werden aber nur bei df-**Zuweisung** synchronisiert (`_sync_column_metadata`); In-place-Mutationen (`sdf.df["a"] = ….astype(float)`) laufen am Setter vorbei. Schema-`type` (frisch aus `dtype.kind`) und `"sdata"`-Block (potenziell alt) konnten divergieren → Restore falscher Typen. | `_datapackage_descriptor` ruft zu Beginn `_sync_column_metadata()` — `set_attr` aktualisiert vorhandene Werte (`metadata.py:348`), damit sind Schema **und** Block zum Schreibzeitpunkt konsistent frisch (§5.1). |
> | F13 | `schema` und `dialect` dürfen laut Spec auch **String-Referenzen** (URL oder Pfad) sein; v2 nahm stillschweigend Inline-Objekte an. | In-Paket-Pfadreferenzen werden aufgelöst — mit derselben F3-Containment-Härtung; URL-Referenzen → klarer Fehler (Nicht-Ziel Netz-I/O, §5.2). |
> | F14 | Resource-`path` darf ein **Array** relativer Pfade sein (ein Datensatz in Chunks: „strings MUST either all be relative paths or all URLs"); v2 las nur Skalare. | CSV-Chunk-Arrays werden konkateniert (Header je Chunk; Verhalten in Tests gegen `frictionless-py` festgezurrt); Parquet-Arrays → klarer Fehler (§5.2). |
> | F15 | Group-Export: Custom-Keys sind beliebige Strings — Case-Folding (`"Foo"`/`"foo"`) kollidiert nach dem Zwangs-lowercase, Sonderzeichen verletzen das `name`-Pattern. v2 definierte kein Slugging. | Slug = `suuid.safe_name(key).lower()`; bei Kollision numerischer Suffix (`-2`, `-3`, …). Der Original-Key reist ohnehin im Resource-`"sdata"`-Block (F6) — der Roundtrip hängt nicht am Slug (§5.4). |
> | F16 | D9 begründete Determinismus, aber `zipfile.writestr` stempelt die **aktuelle Uhrzeit** in jeden Entry → zwei Exporte desselben Objekts ergeben verschiedene Zip-Bytes. Wer das Paket hasht/signiert (`as_blob`-Denke, RFC 0004), bekommt Scheinänderungen. | Feste `ZipInfo`-Timestamps aus `_sdata_ctime` + feste Kompressionsparameter → **byte-reproduzierbare** Pakete (D10). |
> | F17 | Fremd-Import-Identität: `from_datapackage` baut `cls()` → Name `"noname"`, und `SUUID.from_name` ist deterministisch → **alle** Fremdimporte ohne `"sdata"`-Block teilen sich dieselbe SUUID. Der v2-Fix „`title`→`name`" griff zu kurz: der `name`-Setter (`base.py:281`) schreibt nur `_sdata_name`, nicht sname/suuid. | Konstruktion mit `cls(name=<Paket-name │ title │ Dateiname>)` → frische, namensabgeleitete SUUID; ein vorhandener `"sdata"`-Block überschreibt sie danach ohnehin (§5.2). |
> | F18 | CSV-Zellen-Feinheiten überversprochen: pandas' `lineterminator` akzeptiert kein `\r\n` (C-Engine, 1 Zeichen) — v2 versprach das Mapping trotzdem; Table-Schema-`date` blieb ungemappt (Strings); `boolean` verließ sich auf pandas-Inferenz statt der Spec-Literale `true`/`false` (+ `trueValues`/`falseValues`). | Dialekt-Mapping auf `delimiter`/`quoteChar` begrenzt, Abweichungen beim `lineTerminator` warnen; `date` → `datetime64`; `boolean` über `trueValues`/`falseValues` (Default `true`/`false`) statt Inferenz (§5.2). |

## 1. Zusammenfassung

Ein **Frictionless Data Package** ist ein offenes Container-Format der Open
Knowledge Foundation für die Weitergabe zusammengehöriger Daten: ein Verzeichnis
(oder Zip) mit einem JSON-Deskriptor `datapackage.json` an der Wurzel, der
Paket-Metadaten (`name`, `id`, `licenses`, …) und eine Liste von **Resources**
(Dateien, URLs oder Inline-Daten) beschreibt. Für Tabellen ergänzt **Table
Schema** je Resource ein Feld-Schema (`name`/`type`/`title`/`description`/
Constraints). Das Format ist der De-facto-Austauschstandard für offene
Datenportale (CKAN, Zenodo, datahub.io) und wird von generischem Tooling
(`frictionless-py`, `datapackage-js`, R, Pandas-Integrationen) gelesen.

sdata **exportiert** heute bereits ein Single-Table-Paket
(`DataFrame.to_datapackage` → Zip mit `datapackage.json`, CSV/Parquet-Daten,
optionalem JSON-LD-Sidecar) und liest die **Metadaten** über den
`"sdata"`-Block verlustfrei zurück — aber nur aus eigenen Paketen, und beim
CSV-Pfad ohne dtype-Treue (F4). Dieses RFC schließt die Lücken zur
Spezifikation und zur Interoperabilität in **beide** Richtungen:

* **G1** Deskriptor vervollständigen (`id`, `created`, `licenses`, `keywords`,
  Resource-`mediatype`/`bytes`/`hash`), **Profil-Konformität herstellen**
  (F2) und Pakete **byte-reproduzierbar** machen (F16) — die Quellen dafür
  existieren alle bereits (`suuid`, `_sdata_ctime`, `ContentIntegrityMixin`).
* **G2** **Fremde** Pakete importieren: Verzeichnis- und Zip-Form (gehärtet,
  F3), Auswahl der Resource, Rück-Mapping der Standard-Schema-Felder nach
  `column_metadata`, Typ-/Dialekt-/Encoding-Anwendung (F4/F5/F11/F18),
  stabile Identität je Import (F17).
* **G3** **Multi-Resource-Pakete**: `DataFrameGroup` als Paket mit einer Resource
  je Mitglied (Slug-Regeln, F15); binäre Assets als `Blob`-Resources über ein
  explizites `assets=`-Argument (F1/F10).
* **G4** Optionale **Spec-Validierung** über `frictionless-py` (neues Extra),
  mit format-getrennten Erwartungen (F2).

## 2. Kontext: die Spezifikation in Kurzform

* **Deskriptor** `datapackage.json` an der Paketwurzel; einziges Pflichtfeld ist
  `resources` (≥ 1 Resource). Empfohlen: `name` (kleingeschrieben,
  `[a-z0-9._-]`), `id` (global eindeutig, z. B. UUID/DOI), `licenses`,
  `profile`. Optional: `title`, `description`, `homepage`, `version`,
  `sources`, `contributors`, `keywords`, `image`, `created` (RFC 3339).
* **Data Resource**: `name` (lowercase-Slug, im Paket eindeutig), genau eine
  Datenquelle — `path` (relativer Pfad, **Array** relativer Pfade oder
  http(s)-URL; absolute Pfade und `../` sind **verboten**) oder `data` inline
  (JSON-Array/-Objekt oder JSON-String + `format`/`mediatype`) — dazu
  `format`, `mediatype`, `encoding`, `bytes`, `hash` (MD5 oder mit Präfix,
  z. B. `sha256:<hex>`).
* **Tabular Data Package**: `profile: tabular-data-package`; **jede** Resource
  MUSS eine Tabular Data Resource sein. **Tabular Data Resource**: Pflicht
  sind `profile: tabular-data-resource`, ein `schema` (Table Schema, als
  Objekt **oder** String-Referenz) und Daten, die non-inline **CSV** sein
  MÜSSEN (inline: „JSON tabular data"); weicht die CSV von RFC 4180 ab, MUSS
  ein `dialect` deklariert sein (Objekt oder String-Referenz).
* **Table Schema**: `fields[]` (`name`, `type` ∈ integer/number/boolean/date/
  datetime/string/…, `title`, `description`, `constraints`, `rdfType`,
  `trueValues`/`falseValues`), `missingValues` (Default `[""]`).
* **Custom Properties** sind auf jeder Ebene erlaubt — darauf beruht der
  verlustfreie `"sdata"`-Block (§3).
* **v2 (datapackage.org, 2024)** ersetzt `profile` durch `$schema`; v1 bleibt
  das von den meisten Portalen akzeptierte Format. Dieses RFC bleibt bei v1
  (§6, D5).

## 3. Bestandsaufnahme: was sdata heute kann

`DataFrame.to_datapackage(path, filename, fmt="csv"|"parquet", sidecar=True)`
(`dataframe.py:997`) schreibt ein Zip mit

* `datapackage.json` — `name`/`title`/`description`/`profile:
  tabular-data-package`, **eine** Resource (`data/<sname>.csv|.spq`,
  `profile: tabular-data-resource`) mit Table Schema aus `column_metadata`:
  `type` aus dem pandas-dtype, `title` ← `label`, `description`, `unit`
  (Custom-Property), `rdfType` ← `ontology` (`_datapackage_descriptor`,
  `dataframe.py:967`);
* dem **verlustfreien `"sdata"`-Block** (volles `metadata`/`column_metadata`/
  `description`-Dict, gleiche Payload wie `df.attrs["_sdata"]`);
* optional dem JSON-LD-Sidecar `<sname>.meta.jsonld`.

`DataFrame.from_datapackage(zip)` (`dataframe.py:1043`) liest `resources[0]`
und stellt über den `"sdata"`-Block via `_restore_from_attrs` (inkl.
RFC-0010-Versionsprüfung) die **Metadaten** verlustfrei wieder her. Abgedeckt
durch `tests/test_sclass_dataframe_datapackage.py` (Roundtrip CSV/Parquet,
Deskriptor-Form, Bytes-Modus, Fehlerfälle).

**Bewertung.**

* `name` = `sname.lower()` erfüllt das v1-Pattern (snames sind per `suuid`
  auf `[A-Za-z0-9_]` normalisiert). CSV-Export + `"sdata"`-Block sind gültig
  und für Dritte lesbar.
* **Aber:** `fmt="parquet"` deklariert heute `tabular-data-resource`, was die
  Spec auf CSV festnagelt — der Parquet-Export ist **v1-ungültig
  etikettiert** (F2; Daten sind in Ordnung, das Profil lügt).
* Der Import ist **sdata-zentrisch**: ohne `"sdata"`-Block gehen alle
  Spalten-Annotationen verloren, obwohl der Deskriptor sie standardkonform
  trägt; selbst mit Block kommen CSV-dtypes nur per `read_csv`-Inferenz
  zurück (F4); und jeder Fremdimport erhält dieselbe `"noname"`-Identität
  (F17).

## 4. Lücken (Gap-Analyse)

| # | Lücke | Wirkung |
|---|-------|---------|
| G1 | Deskriptor ohne `id`, `created`, `licenses`, `keywords`, `version`; Resource ohne `mediatype`, `bytes`, `hash`, `encoding`; Parquet unter falschem Profil (F2); Zip-Bytes nicht reproduzierbar (F16) | Portale/Tooling können Identität, Lizenz und Integrität nicht prüfen; strikte Validatoren lehnen Parquet-Pakete ab; Paket-Hashes ändern sich ohne Datenänderung |
| G2 | `from_datapackage` liest nur eigene Zips: fest `resources[0]`, kein Verzeichnis/`datapackage.json`-Pfad, Standard-Schema-Felder werden ignoriert, kein `dialect`/`encoding`/`missingValues`, keine Typ-Anwendung, keine Pfad-Härtung, kollidierende Import-Identität (F3–F5, F11, F13, F14, F17, F18) | Fremde Pakete (CKAN/Zenodo-Downloads) verlieren Semantik oder kommen stumm falsch an; Mehr-Resource-Pakete sind nicht adressierbar |
| G3 | Nur Single-Table: `DataFrameGroup` hat keinen Package-Pfad; für binäre Assets fehlt jede API (F10, F15) | Ein Versuch (mehrere Tabellen + Binärassets) lässt sich nicht als **ein** Paket publizieren |
| G4 | Keine Validierung gegen die Spec | Konformität ist nur durch eigene Tests belegt, nicht durch das Referenz-Tooling |

## 5. Entwurf

### 5.1 Deskriptor-Vervollständigung (G1)

Mapping — jede Quelle existiert bereits, nichts wird erfunden; User-Attribute
werden nur emittiert, **wenn vorhanden**:

| Data Package | sdata-Quelle | Richtung |
|--------------|--------------|----------|
| `name` | `sname.lower()` (Pattern-konform, s. §3) | ✓ heute |
| `id` | `suuid_str` (global eindeutig, deterministisch) | neu, Export |
| `title` / `description` | `name` / `description` | ✓ heute |
| `created` | `_sdata_ctime` (bereits ISO/RFC 3339, UTC; Objekt-Erstellung, D9) | neu, Export |
| `licenses` | User-Attribut `license` (Open-Definition-ID, z. B. `CC-BY-4.0`) | neu, beide |
| `keywords` / `version` / `homepage` | gleichnamige User-Attribute | neu, beide |
| `contributors` | User-Attribut `author` (→ `[{title, role: "author"}]`) | neu, Export |
| Resource `mediatype` | `text/csv` bzw. `application/vnd.apache.parquet` (wie `_BLOB_FORMATS`) | neu |
| Resource `encoding` | `utf-8` (CSV) | neu, beide (Import: F11) |
| Resource `bytes` / `hash` | `len(data_bytes)` / `"sha256:" + hexdigest` über die **Datei-Bytes** | neu |
| `sdata` (Custom Property) | `metadata`/`column_metadata`/`description` | ✓ heute, verlustfrei |

**Frische-Garantie (F12).** `_datapackage_descriptor` ruft zu Beginn
`_sync_column_metadata()` auf: `set_attr` aktualisiert die Werte vorhandener
Attribute (`metadata.py:348`), damit tragen Schema-`type` **und**
`"sdata"`-Block zum Schreibzeitpunkt dieselben, aktuellen dtype-Namen — auch
nach In-place-Mutationen, die am `df`-Setter vorbeigelaufen sind.

**Profil-Korrektur (F2).** `fmt="csv"` bleibt `tabular-data-package`/
`tabular-data-resource` (voll konform inkl. Pflicht-`schema`). `fmt="parquet"`
deklariert künftig `data-package`/`data-resource`; das Table Schema und `unit`
bleiben als erlaubte Custom Properties erhalten — kein Informationsverlust,
nur ehrliche Etikettierung. Generisches Tabular-Tooling kann Parquet ohnehin
nicht lesen; wer Interop will, nimmt CSV (Default).

**Byte-Reproduzierbarkeit (F16, D10).** Alle Zip-Entries werden mit festem
`ZipInfo`-Timestamp (aus `_sdata_ctime`) und festen Kompressionsparametern
geschrieben: dasselbe Objekt ergibt **byte-identische** Pakete — hash-,
signier- und diff-stabil, konsistent zur Prüfsummen-Linie aus RFC 0004.

Pointe bei `fmt="csv"`: die Paketdatei **ist** die kanonische CSV-Form
(`to_csv(index=False)`, UTF-8) aus RFC 0004 — Resource-`hash` und
`DataFrame.sha256`/`checksum` sind damit **identisch**; ein Konsument, der die
Datei im Paket prüft, prüft zugleich die logische Datenidentität. Bei
`fmt="parquet"` ist der Hash ein Asset-Hash (Parquet ist nicht byte-stabil,
RFC 0004) — dokumentiert, analog `as_blob`. **Index-Asymmetrie (F7):** die
kanonische CSV verwirft einen Nicht-Default-Index, Parquet erhält ihn; der
CSV-Export warnt (`logger.warning`), wenn dabei ein Nicht-Default-Index
wegfällt (D8).

### 5.2 Fremdpakete importieren (G2)

```python
DataFrame.from_datapackage(source, resource=None)
```

* **Drei Quellformen:** Zip-Datei (wie heute), **Verzeichnis** mit
  `datapackage.json` an der Wurzel (kanonische Spec-Form), direkter Pfad auf
  eine `datapackage.json`. Erkennung über `zipfile.is_zipfile`/`os.path.isdir`.
* **Pfad-Härtung (F3), spec-gefordert:** Resource-`path` (und
  String-Referenzen für `schema`/`dialect`, F13) muss relativ sein, ohne
  `..`-Segmente; vor dem Lesen wird der aufgelöste Pfad auf Containment in
  der Paketwurzel geprüft (`os.path.realpath`-Vergleich), sonst
  `ValueError`. Gilt für Verzeichnis- **und** Zip-Form (Zip-Einträge werden
  nur per exaktem Namen gelesen, nie extrahiert).
* **Identität (F17):** Konstruktion mit `cls(name=<Paket-`name`, sonst
  `title`, sonst Dateiname>)` — jeder Fremdimport bekommt eine frische,
  namensabgeleitete SUUID statt der kollidierenden `"noname"`-Identität. Ein
  vorhandener `"sdata"`-Block überschreibt Name/sname/suuid danach ohnehin
  (verlustfreier Eigen-Roundtrip, unverändert).
* **Resource-Auswahl:** `resource=None` → erste tabellarische Resource
  (CSV oder Parquet); sonst Auswahl per Resource-`name`. Unbekannter Name →
  `ValueError` mit Liste der vorhandenen Namen. `path`-**Arrays** (ein
  Datensatz in Chunks, F14) werden für CSV konkateniert (Header je Chunk;
  Verhalten in Tests gegen `frictionless-py` festgezurrt), für Parquet
  abgelehnt.
* **Rück-Mapping der Standard-Felder** (nur wenn **kein** `"sdata"`-Block da
  ist — der bleibt Vorrangsquelle): `title`→`label`, `description`→
  `description`, `unit`→`unit`, `rdfType`→`ontology` je Spalte;
  Paket-`title`/`description` → `name`/`description`. Eine fremde Paket-`id`
  (DOI, beliebiger String) wird als User-Attribut **`datapackage_id`**
  bewahrt — sie wird **nicht** in eine SUUID gezwungen (F8).
* **Typ-Wiederherstellung beim CSV-Parse (F4) — für beide Pfade:**
  * *eigene Pakete:* aus den dtype-Namen in der `column_metadata` des
    `"sdata"`-Blocks (zum Schreibzeitpunkt frisch, F12);
  * *fremde Pakete:* aus dem Table Schema — `integer`→`Int64` (nullable),
    `number`→`float64`, `boolean`→`boolean` über `trueValues`/`falseValues`
    (Default `true`/`false`, F18), `datetime`/`date`→`to_datetime` (F18),
    sonst String — statt `read_csv`-Inferenz. Ein `schema` als
    String-Referenz wird in-Paket aufgelöst (F13); URL-Referenzen → Fehler.
* **Dialekt, Encoding & Missing Values (F5/F11/F18):** vom `dialect` werden
  `delimiter` und `quoteChar` auf `read_csv` abgebildet (Semikolon-CSVs!);
  andere deklarierte Abweichungen (z. B. exotischer `lineTerminator`) loggen
  eine Warnung, statt still zu raten. Resource-`encoding` →
  `read_csv(encoding=…)` (Default `utf-8`). Table-Schema-`missingValues` →
  `na_values` (`keep_default_na=False`, wenn deklariert).
* `data`-Inline-Resources (JSON-Array/-Objekt; JSON-String + `format`) werden
  unterstützt; **Remote-`path` (URL) ist Nicht-Ziel** (§9) und wirft einen
  klaren Fehler.
* `DataFrameGroup.from_datapackage(source)` lädt **alle** tabellarischen
  Resources als Mitglieder und stellt die Gruppen-Metadaten aus dem
  Paket-`"sdata"`-Block wieder her; nicht-tabellarische Resources werden mit
  Warnung übersprungen und sind einzeln über
  `Blob.from_datapackage(source, resource=…)` erreichbar (F10).

### 5.3 Verzeichnisform schreiben

`to_datapackage(..., bundle="zip"|"dir")` (Default `"zip"`, unverändert).
`"dir"` legt `<path>/<sname>/datapackage.json` + `data/…` (+ Sidecar) an —
die kanonische, diff-/git-freundliche Spec-Form, direkt von
`frictionless-py`/CKAN konsumierbar, ohne Entpacken.

### 5.4 Multi-Resource-Pakete (G3)

* **`DataFrameGroup.to_datapackage(...)`** — **ein** Paket, Paketebene =
  Gruppe (`name`/`id`/`description` der Gruppe), je Mitglied eine Resource
  (`data/<slug>.csv|.spq`, Schema wie §5.1). **Slug-Regeln (F15):** Slug =
  `suuid.safe_name(key).lower()` (Keys sind beliebige Strings); kollidieren
  zwei Slugs (Case-Folding, Normalisierung), wird ein numerischer Suffix
  angehängt. Der **Original-Gruppenschlüssel** reist im Resource-
  `"sdata"`-Block (F6) — der Roundtrip stellt die Keys exakt daraus wieder
  her und hängt nicht am Slug.
* **Binäre Assets (F10):** `to_datapackage(assets=[blob, …])` — auf
  `DataFrame` **und** `DataFrameGroup` — bettet zusätzliche
  :class:`Blob`-Objekte als `profile: data-resource` ein: `path:
  data/<slug>.<filetype>`, `mediatype` aus dem `mime_type`-Attribut,
  `bytes`/`hash` aus dem `ContentIntegrityMixin`, eigener `"sdata"`-Block je
  Resource. Bewusst ein explizites Argument statt eines Group-Umbaus
  (`DataFrameGroup` hält per Design nur DataFrames; D11). Rückweg:
  `Blob.from_datapackage(source, resource=…)`.
* **Profil-Wahl (F1):** Enthält das Paket **nur** tabellarische CSV-Resources
  → `tabular-data-package`. Sobald ein Asset (oder Parquet, F2) dabei ist →
  `data-package`; die konformen CSV-Mitglieder behalten individuell ihr
  `tabular-data-resource`-Profil. Nie ein Tabular-Paket-Etikett auf einem
  gemischten Paket.

### 5.5 Validierung (G4)

Neues optionales Extra `sdata[frictionless]` (→ `frictionless>=5`). Kein
Laufzeit-Import im Kern; genutzt nur in Tests
(`pytest.importorskip("frictionless")`). **Format-getrennte Erwartung (F2):**
CSV-Pakete müssen `frictionless.validate()` unter dem **Tabular**-Profil
bestehen (Deskriptor **und** Daten); Parquet-/Misch-Pakete validieren als
`data-package` (Deskriptor-Ebene). Das ersetzt Eigenbehauptungen durch das
Referenz-Tooling, ohne Unerfüllbares zu versprechen.

## 6. Designentscheidungen

* **D1 — Dual-Deskriptor beibehalten.** Standard-Felder für generisches
  Tooling **plus** `"sdata"`-Custom-Property für den verlustfreien
  Metadaten-Roundtrip. Custom Properties sind spec-konform; die Alternative
  (nur Standard-Felder) wäre lossy (reservierte `_sdata_*`-Attribute,
  `unit_system` aus RFC 0014), die Alternative (nur `"sdata"`) wäre für
  Dritte wertlos.
* **D2 — `unit` als Custom-Field-Property.** Einheiten sind nicht Teil des
  Table-Schema-Kerns; das flache `unit`-Feld ist etablierte Frictionless-Praxis
  und bleibt. Die reiche Semantik (QUDT/Ontologie) reist ohnehin im
  `"sdata"`-Block und im JSON-LD-Sidecar.
* **D3 — Hash über Datei-Bytes, nicht `content_bytes`.** Der Paket-Konsument
  prüft die Datei, die er hat. Dass beide bei `fmt="csv"` zusammenfallen, ist
  gewollte Konsequenz der kanonischen CSV-Form (RFC 0004), kein Mechanismus.
* **D4 — kein eigener `DataPackageWriter` (RFC 0007).** Ein Paket ist ein
  Ein-Schuss-Bündel ohne Sink-Lebenszyklus (kein offenes Handle, kein
  Append-Modus); Batch-Bedarf deckt die Group-API (§5.4). Sollte später ein
  Verzeichnis-Append-Fall entstehen, ist ein Writer additiv nachrüstbar.
* **D5 — v1-Profil beibehalten, v2 beobachten.** `profile`-Mechanik bleibt;
  v2 (`$schema`) wird erst emittiert, wenn die Ziel-Portale es akzeptieren.
  Der `"sdata"`-Block ist davon unabhängig über RFC 0010
  (`_sdata_format_version`) versioniert.
* **D6 — Import erfindet nichts.** Ohne `"sdata"`-Block werden nur die
  tatsächlich vorhandenen Standard-Felder gemappt; fehlende Annotationen
  bleiben leer (kein Raten von Einheiten o. Ä.).
* **D7 — Profil-Wahrheit vor Format-Komfort (F1/F2).** Das Profil beschreibt,
  was ein fremder Validator prüfen kann — nicht, was sdata gern wäre.
  Parquet und gemischte Pakete sind `data-package`; nur reine CSV-Pakete
  tragen das Tabular-Etikett. Lieber ein schwächeres, wahres Profil als ein
  stärkeres, falsches.
* **D8 — CSV bleibt kanonisch index-frei (F7).** Konsistent mit
  `content_bytes` (RFC 0004); der Verlust eines Nicht-Default-Index im
  CSV-Pfad wird gewarnt, nicht still geschluckt. Wer den Index braucht,
  nimmt `fmt="parquet"` oder materialisiert ihn als Spalte.
* **D9 — deterministischer Deskriptor (F9).** `created` kommt aus
  `_sdata_ctime` (Objekt-Erstellung), nicht vom Schreibzeitpunkt: zwei
  Exporte desselben Objekts erzeugen denselben Deskriptor. Die
  Spec-Lesart „Paket-Erstellung" wird bewusst zugunsten der
  Reproduzierbarkeit (RFC-0004-Linie) ausgelegt.
* **D10 — byte-reproduzierbare Pakete (F16).** D9 zu Ende gedacht: feste
  `ZipInfo`-Timestamps (aus `_sdata_ctime`) und feste Kompressionsparameter,
  damit derselbe Inhalt dieselben Zip-Bytes ergibt. Ein deterministischer
  Deskriptor in einem nicht-deterministischen Container wäre eine halbe
  Garantie.
* **D11 — Assets explizit statt Group-Umbau (F10).** `DataFrameGroup` bleibt
  eine reine Tabellen-Sammlung (RFC 0011); binäre Beilagen kommen als
  `assets=`-Argument in den Export. Das hält die Group-Semantik schlank und
  macht die Paket-Zusammensetzung am Aufrufort sichtbar.

## 7. Kompatibilität

* **Additiv mit einer deklarierten Ausnahme.** Bestehende Zips laden
  unverändert (der `"sdata"`-Block-Pfad bleibt erster Kanal); neue
  Deskriptor-Felder sind für Alt-Leser unsichtbar. Signatur-Erweiterungen
  (`resource=`, `bundle=`, `assets=`) haben abwärtskompatible Defaults.
  **Ausnahme:** der Profil-String von Parquet-Paketen ändert sich
  (`tabular-data-*` → `data-*`, F2) — ein Bugfix zur Spec-Konformität;
  `from_datapackage` liest beide Varianten.
* **Kein neuer Pflicht-Dependency.** CSV-Pakete funktionieren weiter ohne
  pyarrow; `frictionless` ist reines Test-/Opt-in-Extra.
* Die `id`/`hash`-Emission ändert die **Daten**-Bytes nicht — Checksummen aus
  RFC 0004 bleiben stabil. Die Zip-Timestamps ändern sich einmalig auf die
  deterministische Form (F16); wer alte Paket-Bytes gehasht hat, re-hasht.

## 8. Tests / Validierung (Plan)

* Deskriptor-Vollständigkeit: `id`==`suuid_str`, `created` RFC 3339,
  `licenses`/`keywords` nur bei vorhandenen User-Attributen, Resource
  `bytes`/`hash`/`mediatype`; `hash` verifiziert gegen die Datei-Bytes;
  CSV: `hash` == `"sha256:" + sdf.sha256`; Parquet-Paket trägt
  `data-package`-Profil (F2).
* Dtype-Treue (F4/F12): CSV-Roundtrip eigener Pakete mit `datetime64`-,
  `Int64`- und `boolean`-Spalten kommt typgleich zurück — auch nach einer
  In-place-dtype-Mutation vor dem Export (Frische-Garantie).
* Reproduzierbarkeit (F16): zweimal `to_datapackage()` auf demselben Objekt
  → byte-identische Zips.
* Fremdpaket-Import: fixture-Paket **ohne** `"sdata"`-Block (Verzeichnis- und
  Zip-Form) → `label`/`unit`/`ontology`/Typen korrekt gemappt; Semikolon-CSV
  mit `dialect`; `latin-1`-CSV mit `encoding` (F11); `missingValues` →
  `NaN`; `boolean` aus `true`/`false` und custom `trueValues` (F18);
  `date`-Spalte → `datetime64` (F18); `schema` als In-Paket-String-Referenz
  (F13); `path`-Array aus zwei CSV-Chunks → konkateniert, Verhalten
  deckungsgleich mit `frictionless-py` (F14); fremde `id` →
  `datapackage_id`; zwei verschiedene Fremdimporte → **verschiedene** SUUIDs
  (F17); `resource=`-Auswahl; unbekannte Resource → `ValueError`;
  URL-`path`/URL-`schema` → klarer Fehler; Inline-`data` (Array und
  String+`format`).
* Pfad-Härtung (F3/F13): Deskriptor mit `../escape.csv`, absolutem Pfad und
  `../`-Schema-Referenz → `ValueError`, kein Dateizugriff außerhalb der
  Wurzel (Verzeichnis- und Zip-Form).
* Group-Paket: N Tabellen + `assets=[blob]` → ein Paket mit
  `data-package`-Profil (F1/F10); reine CSV-Gruppe → `tabular-data-package`;
  Roundtrip stellt die **Original-Keys** wieder her (F6), auch bei
  Slug-Kollision `"Foo"`/`"foo"` (F15); Blob über
  `Blob.from_datapackage(resource=…)` zurück, `bytes`/`hash` korrekt;
  Group-Import überspringt Assets mit Warnung.
* `bundle="dir"`: Layout, Roundtrip, Sidecar.
* CSV-Export mit Nicht-Default-Index → Warnung (F7).
* `frictionless.validate()` (`importorskip`): CSV-Pakete grün unter
  Tabular-Profil; Parquet-/Misch-Pakete grün als `data-package`.
* `make ci` grün; neue Pfade 100 % Coverage (HDF5-Ausnahme gilt hier nicht).

## 9. Nicht-Ziele

* **Kein Publishing-Client** (CKAN-/Zenodo-Upload) — sdata erzeugt das Paket,
  der Transport bleibt außen.
* **Keine Remote-Resources** (`path`-, `schema`- oder `dialect`-URLs) beim
  Import — bewusst, um keinen impliziten Netzwerk-I/O im Kern zu haben
  (Blob/fsspec, RFC 0003, ist der Ort dafür).
* **Kein v2-`$schema`-Emit** (D5) und **keine Constraint-Validierung** der
  Daten gegen das Table Schema (nur Typ-Anwendung; Validierung liefert das
  `frictionless`-Extra).
* **Kein vollständiger CSV-Dialect-Support** — nur `delimiter`/`quoteChar`
  (§5.2); andere Dialekt-Abweichungen werden gewarnt, nicht emuliert.
* **Keine `path`-Arrays für Parquet** und keine gemischten
  Chunk-Formate — klarer Fehler statt Halbunterstützung.

## 10. Referenzen

* Data Package (v1): <https://specs.frictionlessdata.io/data-package/>
* Data Resource: <https://specs.frictionlessdata.io/data-resource/>
* Tabular Data Package: <https://specs.frictionlessdata.io/tabular-data-package/>
* Tabular Data Resource: <https://specs.frictionlessdata.io/tabular-data-resource/>
* Table Schema: <https://specs.frictionlessdata.io/table-schema/>
* Data Package Standard v2: <https://datapackage.org/>
* frictionless-py: <https://framework.frictionlessdata.io/>
