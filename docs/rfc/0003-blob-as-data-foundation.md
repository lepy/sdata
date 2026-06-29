# RFC 0003 — `Blob` als Grundlage aller Datenformate (+ Blob-Härtung)

| Feld        | Wert                                                         |
|-------------|--------------------------------------------------------------|
| Status      | Proposed                                                     |
| Datum       | 2026-06-29                                                  |
| Autor       | lepy <lepy@tuta.io>                                          |
| Komponente  | `sdata/sclass/blob.py` (+ `dataframe.py`, `image.py`, `filereference.py`) |
| Betrifft    | `Blob` als gemeinsame Content-/Integritäts-/Provenienz-Basis |
| Validierung | Designvorschlag — noch nicht implementiert                  |

## 1. Zusammenfassung

`Blob` soll die **gemeinsame Grundlage aller Datenformat-Container** werden: der
Layer, der **Inhalt** (Bytes oder URI), **Integrität** (Prüfsumme/`verify`),
**Provenienz/Lizenz** und **lazy/streamendes Laden** (fsspec) bereitstellt —
während formatspezifische Klassen (`DataFrame`, `Image`, `FileReference`) nur die
**Kodierung** des Inhalts liefern (Parquet, PNG, …).

Heute ist das **nicht** realisiert: kein Container erbt von `Blob` (obwohl
`filereference.py`/`zipfile.py`/`dataframe.py` auskommentierte `Blob`-Importe
tragen — die ursprüngliche Absicht). Zugleich hat die aktuelle `Blob`-Klasse
mehrere konkrete Schwächen. Dieses RFC schlägt **(A)** eine rückwärtskompatible
Härtung von `Blob` und **(B)** den gestaffelten Umbau zur echten Foundation vor.

## 2. Kontext

`Blob(Base)` speichert den Inhalt in `self.data['content']`:

```python
{"type": "bytes" | "uri", "value": <base64-str> | <uri-str>, "filetype": "pdf"}
```

* Laden erfolgt **lazy** über `content_bytes` (für URIs via `fsspec`; Extra
  `sdata[blob]`), Ergebnis wird in `self.data['content_cached']` zwischengespeichert.
* `Blob` rechnet `sha1`/`md5`; `DEFAULT_METADATA` deklariert u. a. `checksum`,
  `mime_type`, `creation_date`, `license`, `source_uri`.
* `Blob` ist mit 100 % Coverage getestet — es ist **funktionsfähig**; dieses RFC
  adressiert **Design-/Konsistenz**-Schwächen, keine Abstürze.

Klassenlage: `DataFrame(Base)`, `Image(Base)`, `FileReference(Base)` — **keiner**
erbt von `Blob`.

## 3. Befunde (verifiziert)

**B1 — Prüfsummen-Inkonsistenz.** `DEFAULT_METADATA["checksum"]` deklariert
**SHA-256** (`required: True`), die Klasse berechnet aber nur `sha1`/`md5` und
befüllt `checksum` **nie**. Es gibt kein `sha256`.

**B2 — `required: True`-Defaults werden nie befüllt.** `checksum`, `mime_type`,
`creation_date` sind `required`, werden aber nicht automatisch gesetzt →
`blob.validate()` (gegen ein Schema) bzw. eine `required`-Prüfung schlägt
strukturell fehl.

**B3 — Cache liegt im serialisierbaren `data`.** `content_cached` wird in
`self.data` abgelegt; `to_dict`/`exists` müssen ihn defensiv `pop`en. Der Cache
gehört nicht in den serialisierten Zustand (Mutation, Gleichheit, versehentliche
Persistenz großer Bytes).

**B4 — Undefinierter Ontologie-Prefix `saf:`.** `DEFAULT_METADATA` nutzt 8×
`saf:checksum`/`saf:mimeType`/… — `saf:` ist **nicht** im JSON-LD-`@context`
(`sdata/vocab.py`) registriert → in JSON-LD entstehen **unauflösbare** IRIs.

**B5 — Fehlende Persistenz/Streaming-API.** Kein `write(uri)`/`save_as`, kein
`open()`-Handle, kein chunked Read. `content_bytes` lädt **alles** in den RAM —
widerspricht dem „Large Object"-Anspruch.

**B6 — Keine Integritätsprüfung.** Es wird (sollte) eine Prüfsumme gespeichert,
aber es gibt kein `verify()`, das den Inhalt dagegen prüft.

**B7 — MIME/`filetype` unverwaltet.** `filetype` (z. B. `"pdf"`) und das
`mime_type`-Metadatum stehen unverbunden nebeneinander; keine Ableitung
`filetype`↔`mime_type`, keine `size`.

**F1 — Foundation nicht realisiert.** Content-/Hash-/Integritäts-/Provenienz-Logik
ist nicht geteilt. `DataFrame` bettet seine Parquet-Bytes selbst in `data` ein
statt über einen gemeinsamen `Blob`-Content-Layer — Duplikation und divergierende
Serialisierung.

## 4. Ziele / Nicht-Ziele

**Ziele**

* `Blob` rückwärtskompatibel härten (B1–B7).
* `Blob` zur gemeinsamen Content-/Integritäts-/Provenienz-Basis machen, die
  formatspezifische Klassen wiederverwenden.

**Nicht-Ziele**

* Keine Brüche am `to_dict`/`from_dict`-Layout bestehender Container.
* Kein Zwang, `DataFrame` sofort auf `Blob` umzustellen (eigener Folge-RFC).
* Keine neue Pflicht-Abhängigkeit (fsspec bleibt Extra `sdata[blob]`).

## 5. Teil A — `Blob` härten (rückwärtskompatibel)

1. **Prüfsummen vereinheitlichen (B1/B6).** `sha256`-Property ergänzen; `checksum`
   beim ersten Laden lazy mit dem SHA-256 befüllen (zur deklarierten Metadatenform
   passend). `verify() -> bool` ergänzt: Inhalt gegen gespeicherte `checksum`
   prüfen. `sha1`/`md5` bleiben (Kompat).
2. **Cache aus `data` lösen (B3).** Geladene Bytes in einem **nicht serialisierten**
   Instanzattribut `self._content_cache` halten (nicht in `self.data`); `to_dict`
   muss dann nichts mehr `pop`en.
3. **`saf:` auflösen (B4).** Entweder Prefix `saf:` in `sdata/vocab.py` +
   `@context` **registrieren** (mit dereferenzierbarer IRI unter
   `lepy.github.io/sdata/ns#`) **oder** auf **Standard-Vokabular** abbilden
   (`spdx:checksum`/`schema:sha256`, `schema:encodingFormat` für MIME,
   `dcterms:created`/`modified`, `dcterms:license`, `dcat:downloadURL`/
   `dcterms:source`). Empfehlung: Standard-Vokabular (Interop), Prefix-Registrierung
   als Fallback.
4. **`required`-Defaults sinnvoll befüllen (B2).** Beim Setzen von Inhalt:
   `mime_type` aus `filetype` ableiten (Stdlib `mimetypes`), `creation_date`
   stempeln; `checksum` lazy. Felder, die nicht zuverlässig auto-befüllbar sind,
   **nicht** `required` lassen.
5. **Persistenz/Streaming (B5/B7).** `write(uri, **kwargs) -> str` (Inhalt an ein
   fsspec-Ziel schreiben), `open(mode="rb")` (streamendes Handle), `size`-Property;
   chunked Hashing direkt aus dem Stream **ohne** Voll-Load.

Alles additiv: bestehende Signaturen/`content`-Layout bleiben; neue Methoden/
Properties kommen hinzu.

## 6. Teil B — `Blob` als Foundation

Klarstellung der „Grundlage": `Blob` liefert den **Content-/Integritäts-/
Provenienz-Layer**; Format-Klassen liefern die **Kodierung**.

### Option 1 — Volle Vererbung (`DataFrame(Blob)`, `Image(Blob)`, …)

Jede Formatklasse serialisiert ihr Payload in den `Blob`-Content (bytes/uri).
*Pro:* maximale Wiederverwendung, einheitliche Identität/Integrität.
*Contra:* invasiv; `DataFrame` hat ein bewusst **mehrformatiges** Serialisierungs-
modell (Parquet/Arrow/CSV/HDF5/…) und ein etabliertes `to_dict`-Layout → Bruchrisiko.

### Option 2 — Content-Mixin / `ContentStore`-Helper

`Blob`s Content-/Hash-/Integritätslogik als wiederverwendbares Mixin bzw.
Hilfsklasse, die Container **optional** einbinden, ohne die Basisklasse zu wechseln.
*Pro:* additiv, geringes Risiko. *Contra:* keine echte „is-a Blob"-Hierarchie.

### Option 3 — Gestaffelt (empfohlen)

1. **Teil A** umsetzen (rein additiv, eigener PR).
2. `FileReference` und `Image` auf `Blob` heben — die **auskommentierten Importe
   realisieren** (kleine, isolierte PRs); beide sind „content-zentrisch" und passen
   natürlich auf `Blob`.
3. `DataFrame(Blob)` **nur** prüfen, wenn ohne Bruch des `to_dict`-Layouts möglich;
   sonst Content-Mixin (Option 2) für die gemeinsamen Teile. → **eigener Folge-RFC**.

## 7. Kompatibilität / Migration

* Teil A strikt additiv; `content`-Layout und `to_dict`/`from_dict` unverändert.
* Foundation gestaffelt, jeweils mit Round-Trip-Tests; `image.py` ist heute aus der
  Coverage `omit` (experimentell) — vor einem Umbau zu klären.
* Optional-Dependency-Muster (`try import fsspec … except ImportError`) bleibt.

## 8. Testplan / Coverage

* A1 Prüfsummen: `sha256` korrekt; `checksum` wird lazy befüllt; `verify()` True/False
  (intakt vs. manipuliert).
* A2 Cache: nach `content_bytes` ist `_content_cache` gesetzt, `to_dict()` enthält
  **kein** `content_cached`; Round-Trip bleibt gleich.
* A3 `saf:`/Vokabular: `to_jsonld()` erzeugt nur **auflösbare** Terme (gegen das
  `@context` geprüft).
* A4 required-Defaults: `mime_type`/`creation_date` nach Set gesetzt; `validate()`
  gegen ein Blob-Schema grün.
* A5 Persistenz/Streaming: `write(uri)`→`exists()`; `open()` liest identische Bytes;
  Hash aus Stream == Hash aus `content_bytes`.
* Optional-Pfade via `importorskip`/injiziertes Fake (nur `try/except ImportError`
  `# pragma: no cover`), damit die kanonische CI 100 % bleibt.

## 9. Risiken / offene Punkte

* **`DataFrame(Blob)`-Kompatibilität** — das mehrformatige Serialisierungsmodell und
  das `to_dict`-Layout dürfen nicht brechen (Folge-RFC, Option 2 als Fallback).
* **`saf:`-Entscheidung** — Standard-Vokabular vs. eigener registrierter Prefix; mit
  dem bestehenden JSON-LD-/Namespace-Programm (RFC-fremd) abstimmen.
* **`required`-Semantik** vs. `Base.SDATA_SCHEMA`/`validate()` — konsistent halten.
* **`image.py`** ist experimentell/omit — Umbau erst nach Stabilisierung.
* **fsspec-Fehlerbilder** (`content_bytes` wrappt in `ValueError`, `exists()` separat)
  bei der Streaming-API vereinheitlichen.
