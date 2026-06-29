# RFC 0005 — Native, format-übergreifende Bild-Metadaten

| Feld        | Wert                                                          |
|-------------|--------------------------------------------------------------|
| Status      | Accepted — implementiert (PNG/JPEG/JP2/GIF/WebP/TIFF)        |
| Datum       | 2026-06-29                                                  |
| Autor       | lepy <lepy@tuta.io>                                          |
| Komponente  | `sdata/imagemeta.py`, `sdata/sclass/image.py`               |
| Betrifft    | Einbettung von sdata-Metadaten direkt in Bilddateien        |
| Validierung | `imagemeta.py` 100 %; Pillow-Round-Trips für 6 Formate       |

> **Umsetzungsstand.** Implementiert. `sdata/imagemeta.py` bettet sdata-Metadaten
> **nativ und Pillow-frei** in PNG, JPEG, JP2, GIF und WebP ein; `Image` nutzt es
> für eine **einheitliche** `save`/`from_file`-API über alle Formate.

## 1. Zusammenfassung

sdata bekommt **eigenen** Code, um Metadaten (das sdata-Metadaten-JSON) direkt in
Bilddateien zu schreiben und zu lesen — mit **einer** API über alle Formate. Bisher
konnte `Image` Metadaten nur in **PNG** einbetten (über Pillows `PngInfo`); JPEG,
JPEG 2000 und andere Formate blieben außen vor.

Die neue Schicht `sdata.imagemeta` ist **reiner Python-Code** (Standardbibliothek,
keine Pillow-Abhängigkeit). Sie erkennt das Format an den Magic-Bytes und schreibt
die Nutzlast in den **nativen** Metadaten-Träger des jeweiligen Containers:

| Format | Träger der sdata-Nutzlast                          | Kennung            |
| ------ | -------------------------------------------------- | ------------------ |
| PNG    | `iTXt`-Chunk (UTF-8) vor `IEND`                    | Keyword `sdata`    |
| JPEG   | `APP1`-Segment direkt hinter SOI                   | `sdata\0`-Präfix   |
| JP2    | `uuid`-Box (ISO BMFF) vor der `jp2c`-Codestream-Box| feste sdata-UUID   |
| GIF    | Comment-Extension hinter dem Header                | `sdata\0`-Präfix   |
| WebP   | eigener RIFF-Chunk `sdAT`                           | FourCC `sdAT`      |
| TIFF   | privates IFD-Tag (65000), Original-Bytes unverändert| Tag `65000`        |

## 2. Motivation

* **Format-Unabhängigkeit:** eine Tabelle, ein Bild, ein PDF — Metadaten gehören in
  das Asset, nicht nur in eine Sidecar-Datei. Für Bilder soll das **format-agnostisch**
  und mit identischer API funktionieren.
* **Kein Tool-Zwang:** keine Abhängigkeit von `exiftool` o. ä.; das Schreiben/Lesen
  ist Teil von sdata.
* **Pillow-frei lesen:** das Auslesen eingebetteter Metadaten darf nicht von einem
  optionalen Bild-Backend abhängen — `imagemeta.extract` arbeitet auf den rohen Bytes.

## 3. Entwurf

### 3.1 Fassade (`sdata.imagemeta`)

```python
detect_format(data) -> "png"|"jpeg"|"jp2"|"gif"|"webp"|None
embed(data, payload, fmt=None) -> bytes        # replace-Semantik
extract(data, fmt=None) -> str | None          # lenient: unbekannt -> None
supported_formats() -> tuple[str, ...]
```

* **Replace-Semantik:** eine vorhandene sdata-Nutzlast wird **ersetzt**, nicht
  dupliziert (idempotentes erneutes Einbetten).
* **Lenient lesen:** `extract` liefert für unbekannte Formate bzw. Bilder ohne
  eingebettete Nutzlast `None` (kein Fehler). `embed` wirft
  `UnsupportedImageFormatError` für nicht unterstützte Formate.
* **Registry:** `fmt -> (embed_fn, extract_fn)` — weitere Formate (TIFF, …) sind als
  zwei kleine Funktionen + ein Registry-Eintrag nachrüstbar.

### 3.2 Pro Format (Byte-Ebene)

* **PNG** — Chunk-Struktur (`len|type|data|crc`). Ein unkomprimierter `iTXt`-Chunk mit
  Keyword `sdata` wird vor `IEND` eingefügt; CRC-32 über `type+data`.
* **JPEG** — Marker-Segmente. Ein `APP1`-Segment (`sdata\0` + UTF-8) direkt hinter SOI;
  der Marker-Walk stoppt bei SOS. Limit: 16-bit-Längenfeld → Nutzlast ≤ 65527 Byte
  (`PayloadTooLargeError`).
* **JP2** — ISO-BMFF-Boxen (`LBox|TBox|DBox`, optional 64-bit `XLBox`). Eine `uuid`-Box
  mit fester sdata-UUID wird vor der `jp2c`-Box eingefügt.
* **GIF** — Sub-Block-Streams. Eine Comment-Extension (`0x21 0xFE`) mit Präfix `sdata\0`
  hinter Header + Logical Screen Descriptor (+ Global Color Table); Nutzlast in
  255-Byte-Sub-Blöcken. Der Block-Walker überspringt Bild- und sonstige Extension-Daten
  korrekt.
* **WebP** — RIFF-Container. Ein eigener Chunk `sdAT` wird angehängt und die RIFF-Größe
  aktualisiert. Begründung der Wahl s. u.
* **TIFF** — offset-basierte IFDs. Statt fehleranfälliger Offset-Chirurgie bleiben die
  **Original-Bytes unverändert** (alle bestehenden Offsets, inkl. `StripOffsets`, gültig):
  eine **Kopie** der ersten IFD — ergänzt um ein privates Tag (65000) mit der Nutzlast —
  wird ans Dateiende angehängt und der Header auf diese neue IFD umgelenkt. Little- und
  Big-Endian (`II`/`MM`, klassisches TIFF/Magic 42); BigTIFF (Magic 43) ist nicht
  abgedeckt. Erneutes Einbetten ersetzt logisch die Nutzlast; verwaiste Vorgänger-Bytes
  bleiben ungenutzt im File (kein Re-Pack).

### 3.3 `Image`-Integration

* `Image.save(path)` wählt den Container an der Datei-Endung. Liegt der Inhalt bereits
  in diesem Container vor, wird die Nutzlast **ohne Re-Encoding** eingebettet
  (verlustfrei, Pillow-frei); sonst transkodiert Pillow zuerst. Formate ohne nativen
  Handler werden via Pillow geschrieben (Warnung, keine Einbettung).
* `Image.from_file`/`from_bytes` lesen eingebettete Metadaten über `imagemeta.extract`
  zurück (Pillow-frei) und mergen sie (`update_from_usermetadata`).
* `Image.embedded_metadata()` liefert die eingebettete `Metadata` (oder `None`).
* **Sidecar-Fallback (gleiche API):** Formate **ohne** nativen Träger (z. B. BMP)
  werden via Pillow geschrieben und die Metadaten in einem verlustfreien
  `<filepath>.meta.json`-Sidecar abgelegt (gleiche Nutzlast wie eingebettet);
  `from_file` merged einen vorhandenen Sidecar. `save(sidecar=True|False|None)` steuert
  die Policy (immer / nie / nur ohne nativen Träger).

## 4. Designentscheidungen

* **WebP: eigener `sdAT`-Chunk statt VP8X+XMP.** Empirisch behält ein zusätzlicher,
  unbekannter RIFF-Chunk die Dekodier-Integrität (libwebp/Pillow ignorieren unbekannte
  Chunks; Bildgröße/Pixel bleiben unverändert). Das ist robuster und einfacher als eine
  VP8X-Promotion mit XMP-Verpackung. **Trade-off:** ein pedantischer Validator könnte
  einen „simple"-WebP mit Zusatz-Chunk bemängeln; funktional (Dekodierung + sdata-
  Round-Trip) ist es einwandfrei. VP8X+XMP bleibt als spätere Verfeinerung möglich.
* **Hash/Identität.** Das Einbetten verändert die Datei-Bytes (und damit deren Hash).
  Wer einen stabilen Inhalts-Hash braucht, hasht **vor** dem Einbetten oder die reinen
  Pixel — analog zum Daten-vs-Metadaten-Hash bei `DataFrame` (RFC 0004).
* **Sidecar als Fallback und Komplement.** Formate ohne nativen Träger werden über
  einen automatischen, verlustfreien `<filepath>.meta.json`-Sidecar einheitlich
  abgedeckt (gleiche Nutzlast wie eingebettet). Für maschinenlesbare Linked Data
  bleibt zusätzlich der JSON-LD-Sidecar (`semantic.write_sidecar`) verfügbar; beide
  teilen dasselbe Metadaten-Modell.

## 5. Tests / Coverage

* `tests/test_imagemeta.py`: **synthetische** Container-Bytes (Pillow-frei) decken
  `imagemeta.py` zu **100 %** ab — inkl. Replace-Semantik, fehlender Nutzlast, JPEG-
  Standalone-/Non-FF-Marker, JP2-XLBox/`LBox==0`/malformed-Guard, GIF mit/ohne (Local)
  Color Table und Nicht-Comment-Extensions, WebP-Padding. Zusätzlich Pillow-Round-Trips
  über PNG/JPEG/JP2/GIF/WebP/TIFF (Decodier-Integrität).
* `tests/test_image.py`: einheitliche `Image`-API über alle sechs Formate + Transkodierung.

## 6. Kompatibilität / Migration

* Strikt additiv: `imagemeta` ist neu; `Image.from_file`/`from_bytes`/`save` behalten
  ihre Signaturen. PNG-Round-Trips bleiben kompatibel (jetzt über `iTXt` statt
  `PngInfo`, identisches `sdata`-Keyword).
* `imagemeta.py` ist **gemessen** (100 %); `image.py` bleibt wegen des optionalen
  Pillow-Transkodier-Pfads in der Coverage-`omit`.

## 7. Offene Punkte / Zukunft

* Weitere **native** Träger über die Registry, wo ein Container sie bietet, z. B.
  **BigTIFF** (Magic 43, 8-byte-Offsets). Formate ohne nativen Träger (BMP, …) sind
  bereits über den Sidecar-Fallback abgedeckt. 
* Optional: WebP **VP8X+XMP** für strikte Interop; PNG **`zTXt`** (komprimiert) für sehr
  große Nutzlasten; JPEG **Multi-Segment-APP1** jenseits 64 KiB.
