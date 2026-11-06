# RFC 0019 — Einheitliche Fehlerbilder beim Zugriff auf Blob-Inhalte

| Feld        | Wert                                                                                     |
|-------------|------------------------------------------------------------------------------------------|
| Status      | Angenommen                                                                                |
| Datum       | 2026-11-06                                                                                |
| Autor       | lepy <lepy@tuta.io>                                                                       |
| Komponente  | `sdata/sclass/blob.py` (`content_bytes`, `exists`, `open`), `sdata/sclass/content.py` (`update_checksum`, `verify`), Tests `tests/test_sclass_blob_*.py` |
| Betrifft    | Ausnahmetypen von `content_bytes`/`open`, Rückgabe bzw. Ausnahme von `exists`/`verify`/`update_checksum` für `Blob`, `FileReference`, `Image` (`verify`/`update_checksum` auch `DataFrame`) |
| Vorgeschichte | RFC 0003 §9 „Risiken / offene Punkte" (`docs/rfc/0003-blob-as-data-foundation.md:198`: „fsspec-Fehlerbilder … vereinheitlichen"), `docs/rfc/open-points.md:56` |
| Validierung | geplant: `tests/test_sclass_blob_errors.py` (neu), angepasst `tests/test_sclass_blob_coverage.py` |

## 1. Problem

Ein `Blob` mit `content_type="uri"` liest seinen Inhalt über fsspec. Wie ein
Fehler beim Lesen beim Aufrufer ankommt, hängt davon ab, welche Methode er
benutzt. Gemessen auf `master` (`5e2caf1`), fsspec 2026.9.0, Python 3.11.15,
ohne s3fs, als Nicht-root-Nutzer, je Fall mit einem frischen `Blob`:

| Fall | `exists()` | `content_bytes` | `open()` | `size` |
|---|---|---|---|---|
| Datei fehlt | `False` | `ValueError` | `FileNotFoundError` beim Betreten von `with` | `None` |
| keine Leserechte | `True` | `ValueError` | `PermissionError` beim Betreten von `with` | `None` |
| Pfad ist Verzeichnis | `True` | `ValueError` | `IsADirectoryError` beim Betreten von `with` | `None` |
| `s3://` ohne s3fs | `False` | `ValueError` | `ImportError` beim Aufruf | `None` |
| unbekanntes Protokoll `foo://` | `False` | `ValueError` | `ValueError` beim Aufruf | `None` |
| `memory://` fehlt | `False` | `ValueError` | `FileNotFoundError` beim Betreten von `with` | `None` |

Daraus ergeben sich vier Defekte:

1. **`content_bytes` verliert den Fehlertyp.** Jeder Fehler aus fsspec wird
   in `ValueError` umgepackt (`sdata/sclass/blob.py:247-248`). Der
   Originalfehler steht nur implizit in `__context__` (gemessen:
   `__context__` = `FileNotFoundError`, `__cause__` = `None`); mit `except`
   lässt sich nicht nach Ursache unterscheiden. `ValueError` ist zugleich der
   Typ für Programmierfehler wie „kein Inhalt gesetzt" (`blob.py:232`, `:237`)
   und „unbekannter `content_type`" (`blob.py:250`).
2. **`open()` und `content_bytes` widersprechen sich.** `open()` gibt das
   fsspec-Handle ungeprüft zurück (`blob.py:327`). Fehler kommen als native
   Typen an, und zwar zu unterschiedlichen Zeitpunkten: lokale und
   `memory://`-Fehler erst beim Betreten des `with`-Blocks, fehlendes Backend
   und unbekanntes Protokoll schon beim Aufruf (fsspec löst das Dateisystem
   sofort auf). Derselbe fehlende Pfad ist einmal `ValueError`, einmal
   `FileNotFoundError`.
3. **`exists()` vermischt „gibt es nicht" mit „kann ich nicht prüfen".** Jede
   Ausnahme wird zu `False` (`blob.py:287-289`); ist fsspec nicht installiert,
   ebenfalls `False` (`blob.py:281-283`). `s3://` ohne s3fs und ein Tippfehler
   im Protokoll melden damit „Datei existiert nicht".
4. **`verify()` meldet Unlesbarkeit als Prüfsummenabweichung.** Die
   Hash-Properties fangen jeden Fehler ab und geben `None` zurück
   (`_content_hexdigest`, `sdata/sclass/content.py:39-41`; `sha256` delegiert
   dorthin, `content.py:56`). `verify()` vergleicht die gespeicherte Prüfsumme
   mit diesem `None` (`content.py:87`). Gemessen: Blob mit gespeicherter
   Prüfsumme, Datei danach gelöscht, Inhalt noch nicht gelesen → `verify()`
   gibt `False` zurück, genau wie bei manipuliertem Inhalt. Typischer Fall: ein
   aus `to_dict`/`from_dict` geladener Blob, dessen S3-Quelle gerade nicht
   erreichbar ist. *(Nachtrag 2026-11-06: Dieses Beispiel trifft nicht zu.
   `Blob.from_dict` liefert keinen `Blob`, sondern eine von `sdata_factory`
   erzeugte Klasse, die nur von `Base` erbt und weder `content_bytes` noch
   `verify` hat — `Base.from_dict` ignoriert die aufrufende Klasse,
   `sdata/base.py:418-420`. Zutreffend ist der Fall einer neuen Instanz auf
   dieselbe Quelle mit übernommener Prüfsumme. Der `from_dict`-Fehler ist
   nicht Teil dieses RFC.)* `update_checksum()` gibt im selben Fall still
   `None` zurück (`content.py:72`).

Zwei Randbedingungen, beide gemessen:

- **Cache.** `content_bytes` merkt sich den Inhalt je Instanz
  (`blob.py:227-228`, `:252`). Nach dem ersten erfolgreichen Lesen sieht die
  Instanz keine späteren Fehler mehr: Datei gelöscht → `update_checksum()`
  liefert weiter den alten Wert, `verify()` gibt `True` zurück. Defekt 4 trifft
  deshalb nur Instanzen, die ihren Inhalt noch nicht gelesen haben.
- **Kein Überschreiben.** `update_checksum()` überschreibt bei unlesbarem
  Inhalt eine vorhandene Prüfsumme nicht: `Metadata.set_attr` übergeht `None`
  (`sdata/metadata.py:397`).

Betroffen sind alle Unterklassen von `Blob`: `FileReference`
(`sdata/sclass/filereference.py`) und `Image` (`sdata/sclass/image.py:95`,
`:114`, `:201` lesen `content_bytes`). `DataFrame` hat ein eigenes, rein
speicherbasiertes `content_bytes` (`sdata/sclass/dataframe.py:216`), nutzt
aber dasselbe `ContentIntegrityMixin` (`dataframe.py:93`). Die Änderung an
`update_checksum()`/`verify()` (§2.2) gilt deshalb auch dort; sie wirkt sich
nur aus, wenn die CSV-Serialisierung selbst scheitert.

## 2. Vorschlag

### 2.1 Ausnahmeklassen

In `sdata/sclass/blob.py`, exportiert über `sdata.sclass.blob`:

```python
import errno as _errno


class ContentUnavailableError(ValueError):
    """Der Inhalt eines Blob konnte nicht gelesen oder geprüft werden."""

    uri = None  # Quelle; von _unavailable gesetzt


class ContentNotFoundError(FileNotFoundError, ContentUnavailableError):
    pass


class ContentPermissionError(PermissionError, ContentUnavailableError):
    pass


def _unavailable(uri, exc):
    """Übersetzt einen Backend-Fehler; der Aufrufer schreibt ``raise … from exc``."""
    msg = f"Failed to access URI '{uri}': {exc}"
    code = getattr(exc, "errno", None)
    if isinstance(exc, FileNotFoundError):
        err = ContentNotFoundError(code or _errno.ENOENT, msg, uri)
    elif isinstance(exc, PermissionError):
        err = ContentPermissionError(code or _errno.EACCES, msg, uri)
    else:
        err = ContentUnavailableError(msg)
    err.uri = uri
    return err
```

Die Basis `ValueError` hält bestehende `except ValueError`-Aufrufer von
`content_bytes` lauffähig. Die beiden Unterklassen erlauben
`except FileNotFoundError` und `except PermissionError` an jeder Methode.
Der OS-Fehlertyp steht in der Basisliste **vorne**: nur so setzt `OSError`
`errno` und `filename` aus den Konstruktor-Argumenten (ausprobiert mit Python
3.11.15: `errno=2`, `filename='/x'`; mit `ValueError` vorne sind beide
`None`). `uri` wird nach dem Erzeugen gesetzt, nicht als Schlüsselwort:
`OSError.__new__` lehnt Schlüsselwort-Argumente ab (ausprobiert:
`TypeError: ContentNotFoundError() takes no keyword arguments`). Fehlt der
Ursache ein `errno` — gemessen bei `memory://` —, gilt `ENOENT` bzw.
`EACCES`; sonst stünde `[Errno None]` in der Meldung. Mit diesem Code
ausprobiert für `FileNotFoundError` mit und ohne `errno`, `PermissionError`
und `ImportError`: Typ, `isinstance(…, ValueError)`, `errno`, `filename`,
`uri` und `__cause__` wie beschrieben.

Zuordnung des ursprünglichen Fehlers:

| Ursache | Ausnahme |
|---|---|
| `FileNotFoundError` (auch fsspec `memory://`) | `ContentNotFoundError` |
| `PermissionError` | `ContentPermissionError` |
| jede andere (`IsADirectoryError`, fehlendes Backend wie s3fs, unbekanntes Protokoll, Netzwerk) | `ContentUnavailableError` |

Immer mit `raise _unavailable(uri, e) from e`: der Originalfehler steht dann
ausdrücklich in `__cause__` statt nur implizit in `__context__`.

### 2.2 Verhalten je Methode

- **`content_bytes`** wirft die Klassen aus §2.1 statt des nackten
  `ValueError`. Die Programmierfehler (kein Inhalt, unbekannter
  `content_type`) bleiben einfacher `ValueError`. Der Cache bleibt, wie er ist.
- **`open(mode)`** öffnet bei `uri` sofort (`fsspec.open(...).open()`) und
  übersetzt Fehler wie `content_bytes`. Alle Fehler kommen damit beim Aufruf.
  Zurück kommt das geöffnete Datei-Objekt; es ist selbst ein Kontextmanager,
  `with blob.open() as fh:` funktioniert weiter (geprüft: `LocalFileOpener`
  hat `__enter__`).
- **`exists()`** gibt `False` zurück, wenn das Backend sagt, dass der Pfad
  fehlt, wenn kein Inhalt gesetzt ist oder wenn der `content_type` unbekannt
  ist (wie bisher, `blob.py:290-291`). Kann es nicht prüfen (fehlendes
  Backend, unbekanntes Protokoll, Netzwerkfehler), wirft es
  `ContentUnavailableError`. `True` bei vorhandenem, aber unlesbarem Pfad
  (Rechte, Verzeichnis) bleibt: `exists()` beantwortet „gibt es", nicht „kann
  ich lesen".
- **`update_checksum()`** und **`verify()`** berechnen den Hash ohne das
  Abfangen aus `_content_hexdigest` und lassen **jede** Ausnahme aus
  `content_bytes` durch: die Klassen aus §2.1, `ValueError` bei fehlendem
  Inhalt, bei `DataFrame` die Fehler der Serialisierung. `verify()` prüft wie
  bisher zuerst, ob eine Prüfsumme gespeichert ist (`content.py:84-86`), und
  gibt sonst ohne Lesen `False` zurück. Damit heißt `False` nur noch:
  Abweichung oder keine gespeicherte Prüfsumme.
- **Fehlendes fsspec** bleibt `ImportError` mit Installationshinweis — in
  `content_bytes` und `open` wie bisher, in `exists()` neu statt `False`. Es
  ist ein Installationsproblem, kein Inhaltsfehler.

### 2.3 Was gleich bleibt

- `size`, `sha1`, `md5`, `sha256` geben bei Fehlern weiter `None` zurück und
  loggen; das ist dokumentiert (`content.py:55`, `:60`). Siehe §5.1.
- Der Cache in `content_bytes` (§1). Siehe §5.2.
- Inhalte vom Typ `bytes` sind nicht betroffen; das gilt auch für den Blob in
  `ParquetWriter` (`sdata/iolib/writer.py:260`, `sdf.as_blob("parquet")`).
- `except ValueError` um `content_bytes` fängt weiter alle Lesefehler.

### 2.4 Was bricht

- `exists()` kann werfen, wo es bisher `False` gab: fehlendes Backend,
  unbekanntes Protokoll, fehlendes fsspec.
- `verify()` und `update_checksum()` werfen bei unlesbarem Inhalt bzw.
  fehlendem Inhalt, statt `False` bzw. `None` zu melden.
- `open()`: lokale und `memory://`-Fehler kommen beim Aufruf statt beim
  Betreten des `with`-Blocks. `except ImportError` für ein fehlendes s3fs und
  `except ValueError` für ein unbekanntes Protokoll greifen nicht mehr bzw.
  nur noch über die Basis `ValueError`: s3fs fehlt → `ContentUnavailableError`
  (Ursache `ImportError` in `__cause__`).

## 3. Migration

1. Ausnahmeklassen und `_unavailable` aus §2.1 hinzufügen. Tests: Vererbung
   (`ValueError`, `FileNotFoundError`/`PermissionError`), `errno`,
   `filename`, `uri`, `__cause__`, Fall ohne `errno`. Rein additiv.
2. `content_bytes` umstellen. Tests je Zeile der Tabelle in §1; die
   umgebungsabhängigen Zeilen mit `skipif` (Leserechte: nicht als root;
   s3: nur ohne s3fs) oder per `monkeypatch` auf fsspec. Bestehende Tests mit
   `pytest.raises(ValueError)` in `tests/test_sclass_blob_coverage.py` haben
   kein `match=` und bleiben grün.
3. `open()` umstellen (sofort öffnen, gleiche Übersetzung); Test, dass
   `with blob.open() as fh` weiter funktioniert.
4. `exists()`, `update_checksum()`, `verify()` umstellen (§2.2). Zwei
   bestehende Tests erwarten das alte Verhalten und werden im selben Commit
   angepasst: `tests/test_sclass_blob_coverage.py:84` (`exists() is False`
   ohne fsspec → `ImportError`) und `:92-93` (`weirdproto://` →
   `ContentUnavailableError`). Aufrufer im Produktcode gibt es keine: `git grep
   -n "\.exists()\|\.verify()\|update_checksum" -- sdata` trifft nur
   Docstrings, die Definitionen und `dataframe.py:990` (Blob vom Typ
   `bytes`).
5. CHANGELOG mit dem Bruch aus §2.4, Nachtrag in RFC 0003 §9 und
   `docs/rfc/open-points.md`.

Rückweg: Schritte 1 und 2 sind abwärtskompatibel und jederzeit umkehrbar.
Schritte 3 und 4 ändern beobachtbares Verhalten (§2.4); nach einem Release
bauen Aufrufer darauf, ein Zurück wäre wieder ein Bruch.

## 4. Verworfene Alternativen

- **Status quo.** Die Tabelle in §1 bleibt: Aufrufer müssen Meldungstexte
  parsen, und `verify()` meldet einen Ausfall als Manipulation.
- **Native Ausnahmen durchreichen** (wie heute `open()`). Einfach, aber jeder
  `except ValueError` um `content_bytes` bricht, und fsspec-eigene Typen
  (z. B. `ValueError: Protocol not known`) würden Teil der sdata-API.
- **Eine einzige Klasse ohne OS-Unterklassen.** Einheitlich, aber Aufrufer
  müssten für „fehlt" `isinstance(e.__cause__, FileNotFoundError)` prüfen,
  und `except FileNotFoundError` um `content_bytes` und `open()` griffe nicht.
- **`exists()` bleibt bool, „unklar" wird `False` mit Warnung.** Bricht nichts,
  lässt aber Defekt 3 bestehen. Ein dreiwertiges `exists()` (`True`/`False`/
  `None`) wäre noch fehleranfälliger: `None` ist in `if blob.exists()` falsy.
- **`verify()` gibt bei Unlesbarkeit `None` zurück.** Gleiches Problem:
  `if not blob.verify()` behandelt `None` wie eine Abweichung.
- **`open()` bleibt lazy, nur die Typen werden übersetzt.** Dafür müsste sdata
  das fsspec-Handle einpacken und Fehler beim Betreten übersetzen. Mehr Code
  für denselben Effekt; die Zeitpunkte blieben je Backend verschieden.

## 5. Offene Punkte

1. **`size` und die Hash-Properties** geben weiter `None` zurück. Sie
   ebenfalls werfen zu lassen wäre konsequent, betrifft aber jeden, der `None`
   prüft. Entscheidung, wenn die Streaming-API (RFC 0003) chunked liest.
2. **Cache und `verify()`.** Ein `verify()` auf einer Instanz mit gefülltem
   Cache prüft die gemerkten Bytes, nicht die Quelle (§1). Ob `verify()` die
   Quelle neu lesen soll, ist eine eigene Entscheidung über die Semantik von
   `verify` und nicht Teil dieses RFC.
3. **Version.** §2.4 ist ein Bruch; zusammen mit den übrigen Einträgen unter
   `[Unreleased]` beim Release entscheiden (vgl. RFC 0017 §5.1).
4. **Wiederholversuche bei Netzwerkfehlern** (S3-Timeouts) sind nicht Teil
   dieses RFC; sie gehören in die fsspec-Konfiguration des Aufrufers.

## Revisionen

### v1.1 — 2026-11-06 — bei der Umsetzung

- **§1 Defekt 4:** Das Beispiel „aus `to_dict`/`from_dict` geladener Blob"
  ist falsch; `Blob.from_dict` gibt eine dynamisch erzeugte `Base`-Unterklasse
  ohne `verify` zurück (gemessen: `type(Blob.from_dict(b.to_dict()))` ist
  `sdata.base.Blob` mit MRO `(Blob, Base, object)`). Satz bleibt stehen,
  Nachtrag berichtigt ihn. Der Defekt selbst ist unberührt: mit einer neuen
  Instanz auf dieselbe Quelle und übernommener Prüfsumme gemessen.
