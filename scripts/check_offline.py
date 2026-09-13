#!/usr/bin/env python3
r"""Prueft eine gebaute Doku-Site oder eingecheckte Diagramme auf
tatsaechlichen Netzbezug zur Laufzeit.

Kontextsensitiv statt grep (RFC-003-Befund): ein reines Text-Grep kann eine
Ladeanweisung nicht von einem im Text gezeigten Beispiel unterscheiden — es
schlaegt auf `<code>url(https://…)</code>` in eigener Prosa ebenso an wie auf
ein `data-*`-Attribut, das zufaellig eine URL als Wert traegt. Dieses Skript
sieht sich mit `html.parser` an, WO eine Adresse steht, nicht nur, DASS sie
irgendwo im Text vorkommt:

- Attribute ladender Elemente: link/script/img/source/iframe/audio/video,
  dazu object[data], embed[src], base[href], srcset an img/source,
  meta[http-equiv=refresh][content=url=...] sowie href/xlink:href an den
  SVG-Elementen image/use
- Inline-`style`-Attribute an jedem Element sowie `url()`/`@import` in
  `<style>`-Bloecken und *.css-Dateien (CSS-Kommentare werden vorher
  entfernt — string-fest, siehe unten)
- `fetch(`, `.open(<method>, url)`, `new Worker(`, `import(` (dynamisch),
  `import "…"`/`import x from "…"` (statisch), `importScripts(`,
  `new WebSocket(`, `new EventSource(`, `sendBeacon(`, `.src = "…"` in
  `<script>`-Bloecken sowie *.js-/*.mjs-Dateien

Erkannt werden absolute (`https://…`, GROSS/klein gemischt) und
protokollrelative Adressen (`//host/…`) gleichermassen — ein echter
Site-relativer Pfad wie `/assets/…` beginnt nur mit einem Schraegstrich und
faellt nicht darunter. Attributwerte werden vor dem Vergleich getrimmt,
Anfuehrungszeichen um eine `url=`-Angabe in `meta[refresh]` abgestreift.

**`<pre>`/`<code>` blenden nur Text aus, keine Elemente.** Ein Codebeispiel
wird beim Rendern escaped — aus `<script>` im Markdown wird `&lt;script&gt;`,
und der Parser sieht dort nur Text, den dieses Skript ohnehin nirgends als
Fliesstext nach Adressen durchsucht (es gibt keinen Volltext-Scan, nur
Attribute und die Koerper echter `<style>`/`<script>`-Elemente). Ein
*echtes* verschachteltes Tag innerhalb `<pre>`/`<code>` ist deshalb kein
Beispiel, sondern ein wirksames Element, und wird — wie im Browser — immer
geprueft, egal wie tief verschachtelt oder ob das umgebende `<pre>`/`<code>`
je geschlossen wird.

**Ein nicht geschlossenes `<style>`/`<script>` blendet nicht den Rest der
Datei aus.** `close()` wertet eine noch offene Sammlung beim Dateiende aus,
statt sie stillschweigend zu verwerfen — sonst waere alles nach so einem
Tag unsichtbar, dieselbe Fehlerklasse wie beim `<pre>`/`<code>`-Fund oben.

**CSS-Kommentarentfernung ist string-fest.** `content: "/*"` … `content: "*/"`
um eine echte Ladeanweisung ist keine Kommentarklammer, sondern zwei
unabhaengige Zeichenketten — ein reiner `/\*.*?\*/`-Stripper wuerde das
Dazwischenliegende faelschlich mitloeschen (Falsch-Negativ). Echte
Zeichenketten werden deshalb zuerst erkannt und unangetastet uebersprungen.

**Die Namensraum-Ausnahme (w3.org/schema.org) gilt nur fuer rein
deklarative CSS-Konstrukte** (`@namespace url(...)`), niemals fuer echte
Ladeattribute oder JS-Netzwerkaufrufe: `xmlns` steht gar nicht in
`LADENDE_ATTRIBUTE`, und `<script src="https://www.w3.org/…">` laedt trotzdem
wirklich.

`<a href>` und `rel=canonical/alternate/…` bleiben wie bisher erlaubt.

    python3 scripts/check_offline.py [verzeichnis]

`verzeichnis` ist die gebaute Site (`site/`, Voreinstellung) oder ein
Ordner mit eingecheckten Diagrammen (`docs/assets/diagramme/`).
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

LADENDE_ATTRIBUTE = {
    "link": {"href"},
    "script": {"src"},
    "img": {"src"},
    "source": {"src"},
    "iframe": {"src"},
    "audio": {"src"},
    "video": {"src"},
    "object": {"data"},
    "embed": {"src"},
    # SVG-eigene Referenzen — der praktisch wichtigste Fall, weil die
    # eingecheckten Diagramm-SVG genau dieser Dateityp sind.
    "image": {"href", "xlink:href"},
    "use": {"href", "xlink:href"},
    # <base href="https://…"> im <head>: macht JEDE relative Adresse der
    # Seite zu einem Netzbezug, ohne dass sonst irgendwo eine absolute URL
    # steht.
    "base": {"href"},
}
SRCSET_TAGS = {"img", "source"}
LINK_REL_AUSNAHME = {"canonical", "alternate", "prev", "next"}

# Absolut (http/https, gross-/kleingeschrieben) oder protokollrelativ
# (//host/…). Ein einzelner fuehrender Schraegstrich (/assets/…) ist ein
# erlaubter site-relativer Pfad und faellt nicht darunter.
NETZADRESSE_RE = re.compile(r"^(?:https?:)?//", re.IGNORECASE)
# Nur fuer rein deklarative XML-Namensraeume gedacht (xmlns="...w3.org...",
# @namespace url(...) in CSS) — NIE fuer echte Ladeattribute: die stehen gar
# nicht in LADENDE_ATTRIBUTE, ein <script src="https://www.w3.org/…"> laedt
# trotzdem wirklich. Deshalb nur in pruefe_css_text angewendet, nirgends bei
# Attributen oder JS-Netzwerkaufrufen.
NAMENSRAUM_AUSNAHME = re.compile(
    r"^(?:https?:)?//(www\.)?(w3\.org|schema\.org)/", re.IGNORECASE
)
META_REFRESH_URL_RE = re.compile(r"url\s*=\s*(\S+)", re.IGNORECASE)

# String-fest: matcht zuerst eine Zeichenkette (bleibt unangetastet) oder
# einen echten Kommentar (wird entfernt). Ohne die Zeichenketten-Alternative
# wuerde content:"/*" ... content:"*/" um eine echte Ladeanweisung diese
# faelschlich als "auskommentiert" verschlucken — ein Falsch-Negativ, das
# schlimmer ist als der Fehlalarm, den die Kommentarentfernung beheben soll.
CSS_STRING_ODER_KOMMENTAR_RE = re.compile(
    r'"(?:[^"\\]|\\.)*"' r"|'(?:[^'\\]|\\.)*'" r"|/\*.*?\*/",
    re.DOTALL,
)
CSS_URL_RE = re.compile(r'url\(\s*["\']?\s*((?:https?:)?//[^)"\']+)', re.IGNORECASE)
CSS_IMPORT_RE = re.compile(r'@import[^;]*?((?:https?:)?//[^;)"\']+)', re.IGNORECASE)
# JS-Netzwerkaufrufe. Das Anfuehrungszeichen ist absichtlich PFLICHT (nicht
# optional): ein bare "//" ohne vorangehendes Zeichen ist im JS-Quelltext
# ein Zeilenkommentar, keine URL — ohne diese Pflicht wuerde
# "fetch(\n  // Kommentar\n  x)" faelschlich anschlagen.
JS_FETCH_RE = re.compile(r'fetch\(\s*["\'`]\s*((?:https?:)?//[^"\'`)\s]+)', re.IGNORECASE)
JS_WORKER_RE = re.compile(r'new\s+Worker\(\s*["\'`]\s*((?:https?:)?//[^"\'`)\s]+)', re.IGNORECASE)
JS_XHR_OPEN_RE = re.compile(r'\.open\([^)]*,\s*["\'`]\s*((?:https?:)?//[^"\'`)\s]+)', re.IGNORECASE)
JS_IMPORT_RE = re.compile(r'import\(\s*["\'`]\s*((?:https?:)?//[^"\'`)\s]+)', re.IGNORECASE)
JS_WEBSOCKET_RE = re.compile(r'new\s+WebSocket\(\s*["\'`]\s*((?:wss?:)?//[^"\'`)\s]+)', re.IGNORECASE)
# Statischer ESM-Import — zwei Formen: der reine Seiteneffekt-Import
# (import "https://…") und der benannte (import x from "https://…"). Nur
# `import(` (dynamisch) war bisher erfasst.
JS_STATIC_IMPORT_RE = re.compile(r'\bimport\s+["\'`]\s*((?:https?:)?//[^"\'`)\s]+)', re.IGNORECASE)
JS_IMPORT_FROM_RE = re.compile(r'\bfrom\s+["\'`]\s*((?:https?:)?//[^"\'`)\s]+)', re.IGNORECASE)
JS_IMPORTSCRIPTS_RE = re.compile(r'importScripts\(\s*["\'`]\s*((?:https?:)?//[^"\'`)\s]+)', re.IGNORECASE)
JS_SENDBEACON_RE = re.compile(r'sendBeacon\(\s*["\'`]\s*((?:https?:)?//[^"\'`)\s]+)', re.IGNORECASE)
JS_EVENTSOURCE_RE = re.compile(r'new\s+EventSource\(\s*["\'`]\s*((?:https?:)?//[^"\'`)\s]+)', re.IGNORECASE)
# element.src = "https://…" — direkte Eigenschaftszuweisung statt Attribut.
JS_SRC_ASSIGN_RE = re.compile(r'\.src\s*=\s*["\'`]\s*((?:https?:)?//[^"\'`)\s;]+)', re.IGNORECASE)

JS_REGEXE = (
    JS_FETCH_RE, JS_WORKER_RE, JS_XHR_OPEN_RE, JS_IMPORT_RE, JS_WEBSOCKET_RE,
    JS_STATIC_IMPORT_RE, JS_IMPORT_FROM_RE, JS_IMPORTSCRIPTS_RE,
    JS_SENDBEACON_RE, JS_EVENTSOURCE_RE, JS_SRC_ASSIGN_RE,
)


def ist_netzadresse(wert: str) -> bool:
    return bool(NETZADRESSE_RE.match(wert.strip()))


def ist_ausnahme(url: str) -> bool:
    return bool(NAMENSRAUM_AUSNAHME.match(url.strip()))


def _entferne_css_kommentare(text: str) -> str:
    def ersetzen(m: re.Match) -> str:
        treffer = m.group(0)
        return "" if treffer.startswith("/*") else treffer
    return CSS_STRING_ODER_KOMMENTAR_RE.sub(ersetzen, text)


def pruefe_css_text(text: str) -> list[str]:
    # Ein auskommentiertes Beispiel laedt nichts — Kommentare zuerst
    # entfernen, sonst ist das Gate ein Fehlalarm-Generator statt ein
    # Vertrauensanker. String-fest (siehe CSS_STRING_ODER_KOMMENTAR_RE).
    text = _entferne_css_kommentare(text)
    treffer = []
    for regex in (CSS_URL_RE, CSS_IMPORT_RE):
        for m in regex.finditer(text):
            # Ausnahme bewusst nur hier: @namespace url(...w3.org...) ist
            # eine reine Deklaration, kein Ladevorgang.
            if not ist_ausnahme(m.group(1)):
                treffer.append(m.group(0).strip()[:80])
    return treffer


def pruefe_js_text(text: str) -> list[str]:
    # Keine Namensraum-Ausnahme hier: jeder dieser Aufrufe ist ein wirklicher
    # Netzwerkzugriff, nie eine reine Deklaration wie xmlns.
    treffer = []
    for regex in JS_REGEXE:
        for m in regex.finditer(text):
            treffer.append(m.group(0).strip()[:80])
    return treffer


class _SiteParser(HTMLParser):
    """Wertet eine HTML-/SVG-Datei kontextsensitiv aus: prueft Attribute
    (auch `style`, `srcset`, `meta[http-equiv=refresh]`, SVG-`href`) und den
    Koerper von `<style>`/`<script>` an JEDEM Tag, unabhaengig von der
    Verschachtelung — auch innerhalb `<pre>`/`<code>`. Was hier NICHT
    geprueft wird, ist freier Text (`handle_data` ausserhalb eines
    `<style>`/`<script>`-Koerpers wird nirgends gescannt); ein im Markdown
    gezeigtes Codebeispiel erscheint dem Parser ohnehin nur als solcher Text
    (escaped), nicht als echtes Element."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.treffer: list[str] = []
        self._sammel_tag: str | None = None
        self._sammel_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)

        style = attrs_dict.get("style")
        if style:
            self.treffer.extend(pruefe_css_text(style))

        # Keine Namensraum-Ausnahme fuer echte Ladeattribute: die ist fuer
        # rein deklarative xmlns-/@namespace-Werte gedacht, und xmlns steht
        # gar nicht in LADENDE_ATTRIBUTE. Ein <script src="https://www.w3.org/…">
        # laedt trotzdem wirklich.
        if tag in LADENDE_ATTRIBUTE:
            rel = (attrs_dict.get("rel") or "").strip().lower()
            for name in LADENDE_ATTRIBUTE[tag]:
                wert = (attrs_dict.get(name) or "").strip()
                if not wert or not ist_netzadresse(wert):
                    continue
                if tag == "link" and rel in LINK_REL_AUSNAHME:
                    continue
                self.treffer.append(f'<{tag} {name}="{wert}">')

        if tag in SRCSET_TAGS:
            srcset = attrs_dict.get("srcset") or ""
            for kandidat in srcset.split(","):
                kandidat = kandidat.strip()
                if not kandidat:
                    continue
                url = kandidat.split()[0].strip()
                if url and ist_netzadresse(url):
                    self.treffer.append(f'<{tag} srcset="{kandidat}">')

        if tag == "meta":
            http_equiv = (attrs_dict.get("http-equiv") or "").strip().lower()
            if http_equiv == "refresh":
                content = attrs_dict.get("content") or ""
                m = META_REFRESH_URL_RE.search(content)
                if m:
                    # Eine URL in meta[refresh] darf in Anfuehrungszeichen
                    # stehen (content="0;url='https://…'"): abstreifen, sonst
                    # bricht der nachfolgende Vergleich am Zitatzeichen.
                    url = m.group(1).strip().strip("'\";")
                    if ist_netzadresse(url):
                        self.treffer.append(f'<meta http-equiv="refresh" content="{content}">')

        if tag in ("style", "script"):
            self._sammel_tag = tag
            self._sammel_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == self._sammel_tag:
            self._flush_sammlung()

    def handle_data(self, data: str) -> None:
        if self._sammel_tag:
            self._sammel_text.append(data)

    def _flush_sammlung(self) -> None:
        """Wertet den gesammelten <style>/<script>-Text aus und beendet die
        Sammlung. Wird von handle_endtag beim reellen End-Tag aufgerufen —
        UND von close() beim Dateiende, falls das Tag nie geschlossen wurde.
        Ohne Letzteres blendet ein nicht geschlossenes <style>/<script> den
        Rest der Datei aus: handle_endtag feuert nie, der gesammelte Text
        wird nie geprueft, und alles Folgende (ein echtes <script src="…">
        danach eingeschlossen) bleibt unsichtbar — dieselbe Fehlerklasse wie
        der fruehere <pre>/<code>-Mechanismus."""
        text = "".join(self._sammel_text)
        if self._sammel_tag == "style":
            self.treffer.extend(pruefe_css_text(text))
        else:
            self.treffer.extend(pruefe_js_text(text))
        self._sammel_tag = None
        self._sammel_text = []

    def _loese_offenes_element_auf(self) -> str | None:
        """Wertet ein am Dateiende offen gebliebenes <style>/<script> aus
        und gibt seinen unverarbeiteten Rohtext zurueck (None, wenn keines
        offen war oder nichts davon uebrig blieb). Loest den Rest bewusst
        NICHT selbst rekursiv weiter auf — das erledigt close() iterativ
        (siehe dort), sonst reisst ein adversarialer Fall mit vielen
        hundert verschachtelten, nie geschlossenen Elementen Pythons
        Rekursionsgrenze."""
        if not self._sammel_tag:
            return None
        # Ein CDATA-Element (<style>/<script>) ohne schliessendes Tag ruft
        # handle_data() fuer seinen Koerper NIE auf — html.parser haelt ihn
        # unveraendert in self.rawdata zurueck und wartet auf das Ende-Tag,
        # das nie kommt. Ohne diesen Fallback waere der gesamte Koerper
        # unsichtbar, nicht nur ungeprueft.
        rest = self.rawdata
        if rest:
            self._sammel_text.append(rest)
        self._flush_sammlung()
        # Der verschluckte Rest kann selbst wieder echtes Markup enthalten
        # (ein <script src="…"> oder <img src="…">, das NACH dem nie
        # geschlossenen <style>/<script> im Dokument stand und dadurch nie
        # als eigenes Tag geparst wurde, sondern als Textinhalt im Rest
        # landete). Der Aufrufer wertet ihn als eigenstaendiges Fragment
        # erneut aus.
        return rest if rest and rest.strip() else None

    def close(self) -> None:
        super().close()
        rest = self._loese_offenes_element_auf()
        # Der Rest kann selbst wieder ein nie geschlossenes <style>/<script>
        # enthalten. Ein rekursiver Abstieg (ein neuer _SiteParser je
        # verschachtelter Ebene, der sich selbst wieder ueber close()
        # aufloest) wuerde bei etwa tausend so verschachtelten, nie
        # geschlossenen Elementen Pythons Rekursionsgrenze reissen: der Lauf
        # endet dann mit einem RecursionError-Traceback statt einer
        # Fundmeldung, und alle noch nicht geprueften Dateien bleiben aussen
        # vor. Deshalb iterativ statt rekursiv aufloesen — das deckt jede
        # Verschachtelungstiefe ab, ohne die Aufrufstapel-Tiefe von Python
        # je zu belasten.
        while rest:
            unterparser = _SiteParser()
            unterparser.feed(rest)
            HTMLParser.close(unterparser)
            self.treffer.extend(unterparser.treffer)
            rest = unterparser._loese_offenes_element_auf()


MARKUP_SUFFIXE = (".html", ".htm", ".svg")


def pruefe_datei(pfad: Path) -> list[str]:
    text = pfad.read_text(encoding="utf-8", errors="replace")
    if pfad.suffix in MARKUP_SUFFIXE:
        parser = _SiteParser()
        parser.feed(text)
        parser.close()
        return parser.treffer
    if pfad.suffix == ".css":
        return pruefe_css_text(text)
    if pfad.suffix in (".js", ".mjs"):
        return pruefe_js_text(text)
    return []


def pruefe_site(wurzel: Path) -> dict[Path, list[str]]:
    ergebnis: dict[Path, list[str]] = {}
    for pfad in sorted(wurzel.rglob("*")):
        if not pfad.is_file() or pfad.suffix not in (*MARKUP_SUFFIXE, ".css", ".js", ".mjs"):
            continue
        treffer = pruefe_datei(pfad)
        if treffer:
            ergebnis[pfad] = treffer
    return ergebnis


def main(argv: list[str]) -> int:
    wurzel = Path(argv[1]) if len(argv) > 1 else Path("site")
    if not wurzel.is_dir():
        print(f"{wurzel} fehlt — zuerst bauen.", file=sys.stderr)
        return 1

    ergebnis = pruefe_site(wurzel)
    if ergebnis:
        print("Nachgeladene externe Ressourcen — die Offline-Zusage haelt nicht:")
        for pfad, treffer in ergebnis.items():
            for fund in treffer:
                print(f"  {pfad}: {fund}")
        return 1

    print("OK — keine externen Ressourcen.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
