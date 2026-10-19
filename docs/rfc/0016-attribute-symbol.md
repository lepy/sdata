# RFC 0016 — Formelzeichen als eigenes Attributfeld `symbol`

| Feld        | Wert                                                                                     |
|-------------|------------------------------------------------------------------------------------------|
| Status      | Vorschlag                                                                                 |
| Datum       | 2026-10-19                                                                                |
| Autor       | lepy <lepy@tuta.io>                                                                       |
| Komponente  | `sdata/metadata.py` (`Attribute`, `Metadata`), `sdata/sclass/dataframe.py` (`set_column`, Spalten-Feldliste), `sdata/semantic.py`, `sdata/vocab.py`, `ns/context.jsonld` |
| Betrifft    | alle Serialisierungen von Attributen und Spalten-Annotationen                             |
| Vorgeschichte | RFC 0006 (Spalten-Annotationen), RFC 0010 (Format-Versionierung); Anlass: Konvertierung von Zugversuchsdaten nach tto (tto RFC-001) |
| Validierung | verifiziert: `tests/test_attribute_symbol.py` (Round-Trips dict, Arrow, HDF5, Data Package, CSV-Sidecar, Metadaten-CSV alt/neu, JSON-LD, HTML); volle Suite grün |

## 1. Problem

Ein `Attribute` hat die Felder `name`, `value`, `unit`, `dtype`,
`description`, `label`, `required`, `ontology`
(`sdata/metadata.py:280`, `ATTRIBUTEKEYS`). Für das Formelzeichen einer
Größe gibt es kein Feld:

- Eine tto-konforme Spalte heißt `R_p02[MPa]`, ihre Größe hat das
  Formelzeichen `R_p0,2` und die Benennung „0,2-%-Dehngrenze“. Heute muss
  eines von beiden in `label` landen; das andere geht verloren oder wird in
  `description` versteckt.
- Im JSON-LD ist der Term `symbol` bereits für das **Einheiten**-Symbol
  vergeben (`sdata/vocab.py`, `CONTEXT_TERMS["symbol"] = "qudt:symbol"`,
  ausgegeben über `units.unit_node`). Ein Formelzeichen kann ihn nicht
  mitbenutzen, ohne dass `kN` und `F` am selben Knoten kollidieren.
- Werkzeuge, die Spalten beschriften (Plot-Achsen, Berichte), brauchen das
  Formelzeichen getrennt vom Klartext-Label.

## 2. Vorschlag

### 2.1 Python-API

`Attribute` erhält das Feld `symbol: str` (Vorgabe `""`), gesetzt wie
`label`:

```python
Attribute("R_p02", 952.1, unit="MPa", label="0,2-%-Dehngrenze",
          symbol="R_p0,2", ontology="tto:Rp02")
```

- `Attribute.to_dict()` enthält `"symbol"`.
- `Metadata.set_attr(..., symbol=...)` und `Metadata.update_from_dict`
  übernehmen es; fehlt es, bleibt `""`.
- `DataFrame.set_column(name, *, symbol=...)` und der `ColumnAccessor`
  (`sdf.col.F.symbol`) setzen es an der Spalte.

### 2.2 Serialisierung

| Format | Ablage | Verträglichkeit |
|---|---|---|
| dict/JSON/ZIP, Parquet (`attrs["_sdata"]`), HDF5-Gruppe `_sdata` | über `Attribute.to_dict` | alte Leser ignorieren den Schlüssel (`update_from_dict` liest nur bekannte Felder) |
| Arrow/Feather-Feldmetadaten, HDF5-Dataset-Attribute | `_COL_FIELD_KEYS` um `"symbol"` erweitert | alte Leser ignorieren den Schlüssel |
| Data Package | im `sdata`-Block (verlustfrei) | wie dict |
| JSON-LD (`_attr_node`, `column_node`) | neuer Term `quantitySymbol` → `sdata:quantitySymbol` | additiver Term |
| Metadaten-CSV (`Metadata.to_csv`/`from_csv`), `to_dataframe` | `symbol` als **neunte, letzte** Spalte | neue Leser lesen alte 8-Spalten-Dateien; alte Leser scheitern an 9 Spalten (§3) |

`CURRENT_FORMAT_VERSION` bleibt 1: Ein zusätzlicher optionaler Schlüssel ist
nach RFC 0010 §5 kein Shape-Bruch des Objekt-JSON.

### 2.3 JSON-LD-Term

```json
"quantitySymbol": "sdata:quantitySymbol"
```

in `vocab.CONTEXT_TERMS` und im gehosteten `ns/context.jsonld`. `symbol`
bleibt das Einheiten-Symbol.

## 3. Migration

1. `Attribute.symbol`, `to_dict`, `set_attr`, `update_from_dict` (additiv).
2. `ATTRIBUTEKEYS` und `to_list` um `symbol` am Ende; `Metadata.from_csv`
   und `from_dataframe` akzeptieren Daten ohne `symbol`.
3. `DataFrame.set_column(symbol=...)`, `_COL_FIELD_KEYS`, JSON-LD-Term,
   Sidecar-Rückweg.
4. Kein Löschen, keine Datei-Migration; vollständig umkehrbar bis zur
   ersten Veröffentlichung von Metadaten-CSVs mit neun Spalten. Danach
   brauchen Leser sdata ≥ dieser Version für diese CSVs.

## 4. Verworfene Alternativen

- **Status quo (Formelzeichen in `label`):** Label und Formelzeichen sind
  verschiedene Dinge; eines geht verloren.
- **Formelzeichen in `description` mit Konvention:** nicht maschinenlesbar.
- **JSON-LD-Term `symbol` wiederverwenden:** kollidiert mit dem
  Einheiten-Symbol am selben Knoten.
- **`qudt:symbol` am Spaltenknoten für das Formelzeichen und das
  Einheiten-Symbol nach `qudt:unit` verschieben:** ändert die Bedeutung
  bestehender JSON-LD-Dokumente.
- **`qudt:latexSymbol`:** verlangt LaTeX; Formelzeichen wie `R_p0,2` sind
  ASCII-Schreibweisen, keine LaTeX-Ausdrücke.
- **Formatversion auf 2 heben:** nach RFC 0010 nur bei Shape-Bruch; ein
  optionales Feld ist keiner.

## 5. Offene Punkte

1. `AttrSpec`/`MetadataSchema`/`TableSchema` bekommen kein `symbol`; ob ein
   Schema Formelzeichen vorgeben soll, wird mit dem ersten Verbraucher
   entschieden.

Die HTML-Darstellung (`sdata/interactive.py`) zeigt `symbol` als zweite
Spalte; das ist Teil dieses RFC.
