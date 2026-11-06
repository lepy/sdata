# RFC 0018 — `JsonDocument`: JSON-Inhalt als eigene sdata-Klasse

| Feld        | Wert                                                                                     |
|-------------|------------------------------------------------------------------------------------------|
| Status      | Angenommen (Nutzer 2026-11-06: „dp2g-Report soll auf sdata-json aufbauen“) |
| Datum       | 2026-11-06                                                                                |
| Fassung     | v1.2 (siehe Revisionen)                                                                   |
| Autor       | lepy <lepy@tuta.io>                                                                       |
| Komponente  | neu `sdata/sclass/json_document.py`, Registry `sdata/sclass/__init__.py`, Tests `tests/test_sclass_json_document.py` |
| Betrifft    | Ablage strukturierter JSON-Dokumente (z. B. Report-Boards) als sdata-Container             |
| Vorgeschichte | RFC 0003 (Blob als Grundlage), RFC 0004 (`ContentIntegrityMixin`, kanonische Hash-Basis); Anlass: dp2g-format RFC-009 (Typ `Report`), scale-board-mcp RFC-002 (Reports im Vault) |
| Validierung | `tests/test_sclass_json_document.py`                                                      |

## 1. Problem

Ein JSON-Dokument (Baum aus Objekten und Listen, kein Tabellenformat) lässt sich
heute nur als `Blob` ablegen. Gemessen auf `origin/master` (df8a400):

- `Blob` speichert Bytes base64-kodiert in `data['content']['value']`
  (`sdata/sclass/blob.py:185`). Ein Report-Board von 244 643 Byte JSON wird
  so 326 192 Byte groß; mit zlib (Stufe 6) 56 411 Byte statt 44 061 Byte für das
  rohe JSON (+28 %, Messung 2026-11-06).
- Der Inhalt ist im Container nicht lesbar, nicht vergleichbar und nicht
  abfragbar; jeder Leser muss erst dekodieren.
- `Blob` kennt den Inhaltstyp `uri`, der beim Lesen über fsspec aufgelöst wird
  (`sdata/sclass/blob.py:240-243`). Ein Leser, der nur JSON erwartet, muss diesen
  Fall selbst abweisen, sonst öffnet ein Container eine fremde Adresse.
- Dass der Inhalt JSON ist, steht nur in `filetype` (frei wählbarer Text). Die
  SUUID heißt `Blob__…`; ein Leser erkennt an der Kennung nicht, was er bekommt.

`DataFrame` und `DataFrameGroup` passen nicht: ein verschachtelter Baum hat keine
Spalten.

> **Nachtrag v1.1 (2026-11-06):** v1.0 ging davon aus, sdata habe nichts für
> JSON außer `Blob`. Das stimmt so nicht; vorhanden sind zwei Bausteine:
>
> - **dtype `json`** für Metadatenattribute (`sdata/dtypes.py:413`,
>   `DtypeSpec("json", dict, …)`): ein Attribut kann ein dict tragen. Das ist
>   ein Attributwert, kein Dokument; Prüfsumme, Inhaltskennung und
>   Größenbetrachtung gelten dafür nicht, und ein Board von 245 KB als ein
>   Attribut neben `_sdata_sname` passt nicht zu den Metadaten.
> - **`Base.data`** ist ein freies dict und läuft durch `to_dict`/`from_dict`
>   (`sdata/base.py:387-397`; Probe 2026-11-06: ein verschachteltes dict
>   kommt unverändert zurück). Ein `Base` mit dem Board in `data` wäre
>   ablegbar. Es fehlen aber die kanonische Hash-Basis, die Prüfung auf
>   JSON-Werte, und `_sdata_class` lautet `sdata.base:Base`, die Kennung
>   `Base__…` – ein Leser erkennt daran nicht, dass ein JSON-Dokument folgt.
>
> `JsonDocument` ist deshalb eine dünne Spezialisierung von `Base`: Inhalt in
> `data['content']`, kanonische `content_bytes`, Prüfung, eigener Klassenname.

## 2. Vorschlag

### 2.1 Klasse

```python
class JsonDocument(ContentIntegrityMixin, Base):
    """JSON-Dokument; der Inhalt liegt als JSON-Wert direkt in data['content']."""

    def __init__(self, content: Any = None, *, json_format: str | None = None, **kwargs): ...

    content: Any                 # Property, Lesen und Setzen; nur JSON-Werte
    json_format: str | None      # Property auf Metadatenattribut "json_format"
    content_bytes: bytes         # kanonische Form, Hash-Basis (RFC 0004)
```

- Aufbau wie `DataFrame` (RFC 0004): `ContentIntegrityMixin` + `Base`, **kein**
  `Blob`. Damit gibt es keinen `uri`-Pfad und keine base64-Kodierung.
- `data['content']` hält den JSON-Wert unverändert (dict, list, str, int,
  float, bool, None). Beim Setzen wird geprüft, dass er JSON-serialisierbar ist
  (`json.dumps(..., allow_nan=False)`); `NaN`/`Infinity` und Nicht-JSON-Typen
  werden mit `ValueError` abgelehnt.
- `content_bytes` = `json.dumps(content, sort_keys=True, ensure_ascii=False,
  separators=(",", ":"), allow_nan=False).encode("utf-8")`. Die Prüfsummen
  (`sha256`, `verify`) hängen damit nur am logischen Inhalt, nicht an
  Schlüsselreihenfolge oder Leerraum.
- `json_format`: optionaler Bezeichner des Inhaltsformats, z. B.
  `scale-board/1`. sdata deutet ihn nicht; er sagt dem Leser, welches Schema
  der Inhalt erfüllt.

### 2.1a Metadaten (v1.1)

`JsonDocument` erbt die vollständigen sdata-Metadaten von `Base`: die
reservierten Attribute (`_sdata_sname`, `_sdata_suuid`, `_sdata_class`,
`_sdata_ctime`, `_sdata_format_version`, `_sdata_name`, …) und beliebige
eigene Attribute mit `dtype`, `unit`, `label`, `description`, `ontology`,
`symbol` (`Metadata.add`). Fachliche Attribute eines Dokuments – bei dp2g
`Report` etwa `report_id`, `subject`, `revision`, `board_format`,
`derived_from` – stehen dort als gewöhnliche sdata-Attribute, nicht im
JSON-Inhalt. `json_format` ist eines davon.

### 2.2 Erkennbar an der Kennung

Ohne Eingriff heißt das Objekt `JsonDocument__<safe_name>__<huuid32>`
(`Base.class_name` = Klassenname, `sdata/base.py:190`); ein generischer Leser
erkennt JSON an der Kennung. `_sdata_class` lautet
`sdata.sclass.json_document:JsonDocument`, `from_dict` findet die Klasse
darüber (`sdata/base.py:419`).

> **Nachtrag v1.2 (2026-11-06):** Der letzte Satz stimmt nicht. `Base.from_dict`
> gibt nur den Klassennamen aus `_sdata_class` an `sdata_factory` weiter
> (`sdata/base.py:416-421`) und erzeugt eine dynamische Unterklasse von `Base`
> gleichen Namens, ohne `content` und ohne Prüfung; das gilt ebenso für
> `Blob` und `DataFrame` (Probe 2026-11-06: `Base.from_dict(blob.to_dict())`
> hat MRO `sdata.base.Blob, Base`). Leser rufen deshalb
> `JsonDocument.from_dict`; es prüft `_sdata_class` und lehnt fremde Klassen
> ab. Die Auflösung der echten Klasse in `Base.from_dict` ist ein eigener RFC.

Fachregister dürfen den Typteil der SUUID durch ihren Datentyp ersetzen (so
dp2g-format: `Report__…`). Sie müssen dann im Register festhalten, dass dieser
Typ `JsonDocument` nutzt; der Leser erkennt JSON dann über den Typ.

### 2.3 Registry und Serialisierung

- Eintrag `"JsonDocument": "sdata.sclass.json_document:JsonDocument"` in
  `sdata/sclass/__init__.py`.
- `to_dict`/`from_dict`, `to_json`, `to_zip(deterministic=True)` aus `Base`
  bleiben unverändert; der Inhalt reist als JSON im `.sjson`-Member.
  Verdichten ist Sache des Containers (zip, gzip), nicht der Klasse; es gibt
  keine Varianten „json-raw“/„json-zip“.

## 3. Migration

1. Klasse, Registry-Eintrag, Tests (Rundreise `to_dict`/`from_dict` und
   `to_zip`/`from_zip`; kanonische `content_bytes` unabhängig von der
   Schlüsselreihenfolge; Ablehnung von `NaN` und Nicht-JSON-Typen;
   `verify` nach `update_checksum`; SUUID-Klassenteil `JsonDocument`). Rein
   additiv.
2. Eintrag im CHANGELOG, Navigation in `mkdocs.yml`.
3. Abnehmer heben ihren Pin an (dp2g-format, scale-board-mcp, dp2g-board); erst
   danach schreiben sie `JsonDocument`.

Alles bleibt umkehrbar, bis der erste Abnehmer `JsonDocument`-Objekte
dauerhaft ablegt (z. B. im Vault).

## 4. Verworfene Alternativen

- **Status quo (`Blob` mit `filetype: json`):** base64-Aufschlag, unlesbarer
  Inhalt, `uri`-Pfad, Kennung `Blob__…` (§1).
- **`JsonDocument(Blob)`:** erbt `uri` und base64; der Gewinn läge nur im
  Namen.
- **Mehrere Klassen (`json-raw`, `json-zip`, …):** vermischt Kodierung des
  Containers mit der Bedeutung des Inhalts; die Verdichtung leistet `to_zip`.
- **`Base` direkt, Inhalt in `data` (v1.1):** ohne neue Klasse ablegbar, aber
  ohne Hash-Basis und Prüfung, Kennung `Base__…` (§1, Nachtrag).
- **Metadatenattribut mit dtype `json` (v1.1):** für kleine Werte gedacht;
  das Dokument wäre ein Attribut neben den Kennungsattributen.
- **Inhalt als String statt als JSON-Wert:** lesbar, aber jeder Leser muss
  doppelt parsen und Diffs zeigen eine einzige Zeile.

## 5. Offene Punkte

1. **Größenobergrenze.** Ob `JsonDocument` eine Grenze für den Inhalt prüft
   oder das dem Leser überlässt (scale-board-mcp liest Container mit 512 MiB
   Obergrenze), bei der Umsetzung entscheiden.
2. **Schema-Prüfung.** `json_format` ist nur ein Bezeichner; eine Prüfung gegen
   ein JSON-Schema ist nicht vorgesehen.

## Revisionen

### v1.2 — 2026-11-06 — nach Umsetzung und Review

- **§2.2:** „`from_dict` findet die Klasse darüber“ trifft nicht zu (Nachtrag
  dort, Beleg `sdata/base.py:416-421`). Leser nutzen `JsonDocument.from_dict`.
- Umsetzung auf `feat/json-document` (25ca08d, e010f5d): Tupel werden
  abgelehnt (json.dumps machte sie still zu Listen), Prüfung iterativ ohne
  Rekursionsgrenze, `content_bytes` prüft erneut. §5 Punkt 1 (Größengrenze)
  bleibt offen.

### v1.1 — 2026-11-06 — vorhandene JSON-Bausteine

- **§1:** v1.0 nannte nur `Blob`. sdata hat den dtype `json` für Attribute
  (`sdata/dtypes.py:413`) und das freie `Base.data` (`sdata/base.py:387-397`).
  Nachtrag in §1, zwei Alternativen in §4; die Entscheidung bleibt.
- **§2.1a neu:** `JsonDocument` trägt die vollständigen sdata-Metadaten;
  fachliche Attribute stehen dort, nicht im Inhalt.
