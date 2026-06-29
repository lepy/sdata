# -*- coding: utf-8 -*-
"""Native, format-übergreifende Einbettung von sdata-Metadaten in Bild-Bytes.

Reiner Python-Code (**keine** Pillow-Abhängigkeit für die Metadaten-Schicht): ein
Text-Payload (i. d. R. das sdata-Metadaten-JSON) wird über eine **einheitliche
API** verlustfrei in den jeweiligen Bildcontainer geschrieben bzw. daraus gelesen.

Unterstützte Container und ihr nativer Träger:

* **PNG**  — ``iTXt``-Chunk mit Schlüsselwort ``sdata`` (UTF-8)
* **JPEG** — ``APP1``-Segment mit Kennung ``sdata\\0`` (UTF-8)
* **JP2**  — ``uuid``-Box (JPEG 2000, ISO BMFF) mit fester sdata-UUID
* **GIF**  — Comment-Extension mit Präfix ``sdata\\0``
* **WebP** — eigener RIFF-Chunk ``sdAT`` (von Decodern als unbekannt ignoriert)

Das Format wird an den Magic-Bytes erkannt (:func:`detect_format`); :func:`embed`
und :func:`extract` wählen den passenden Handler. Die Schreibsemantik ist
*replace* (eine vorhandene sdata-Nutzlast wird ersetzt, nicht dupliziert). Pillow
(optional) wird nur zum **Transkodieren der Pixel** benötigt, nicht für die
Metadaten — das Lesen funktioniert daher vollständig Pillow-frei.

:Example:

>>> from sdata import imagemeta
>>> png_with_meta = imagemeta.embed(png_bytes, '{"name": "probe"}')  # doctest: +SKIP
>>> imagemeta.extract(png_with_meta)                                  # doctest: +SKIP
'{"name": "probe"}'
"""
import struct
import zlib
import logging
from typing import Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)

#: Kennung/Schlüsselwort der sdata-Nutzlast in allen Containern.
SDATA_ID = "sdata"
_SID = SDATA_ID.encode("ascii")
#: JPEG-``APP1``-Kennung (``sdata\\0``) zur Unterscheidung von EXIF/XMP.
_JPEG_IDENT = _SID + b"\x00"
#: GIF-Comment-Präfix (``sdata\\0``) zur Erkennung der sdata-Comment-Extension.
_GIF_PREFIX = _SID + b"\x00"
#: 16-Byte-UUID für die JP2-``uuid``-Box (genau 16 Byte).
SDATA_JP2_UUID = b"SDATA-IMG-META\x00\x00"
#: WebP-FourCC des sdata-Chunks (unbekannt → von WebP-Decodern ignoriert).
_WEBP_FOURCC = b"sdAT"
#: Maximale JPEG-``APP1``-Nutzlast (Längenfeld 16 bit, inkl. 2 Längen-Bytes).
_JPEG_MAX_PAYLOAD = 0xFFFF - 2 - len(_JPEG_IDENT)


class ImageMetadataError(Exception):
    """Basisfehler der Bild-Metadaten-Schicht."""


class UnsupportedImageFormatError(ImageMetadataError):
    """Das Bildformat wird (zum Schreiben) nicht unterstützt."""


class PayloadTooLargeError(ImageMetadataError):
    """Die Nutzlast passt nicht in ein einzelnes Format-Segment (z. B. JPEG ``APP1``)."""


# ====================================================================== PNG
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _png_chunks(data: bytes) -> Iterator[Tuple[bytes, bytes]]:
    """Iteriere ``(chunk_type, chunk_data)`` eines PNG (ohne 8-Byte-Signatur)."""
    pos = len(_PNG_MAGIC)
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        cdata = data[pos + 8:pos + 8 + length]
        yield ctype, cdata
        pos += 12 + length  # length(4) + type(4) + data + crc(4)


def _png_make_chunk(ctype: bytes, cdata: bytes) -> bytes:
    """Baue einen PNG-Chunk (Länge + Typ + Daten + CRC-32 über Typ+Daten)."""
    crc = zlib.crc32(ctype + cdata) & 0xFFFFFFFF
    return struct.pack(">I", len(cdata)) + ctype + cdata + struct.pack(">I", crc)


def _png_itxt(payload: str) -> bytes:
    """``iTXt``-Chunk mit Schlüsselwort ``sdata`` (unkomprimiert, UTF-8)."""
    body = (_SID + b"\x00"        # keyword + null
            + b"\x00\x00"          # compression flag + method
            + b"\x00"              # (leerer) language tag + null
            + b"\x00"              # (leeres) translated keyword + null
            + payload.encode("utf-8"))
    return _png_make_chunk(b"iTXt", body)


def _png_embed(data: bytes, payload: str) -> bytes:
    """Schreibe ``payload`` als ``iTXt``-Chunk vor ``IEND`` (ersetzt vorhandenen)."""
    out = bytearray(_PNG_MAGIC)
    for ctype, cdata in _png_chunks(data):
        if ctype in (b"iTXt", b"tEXt") and cdata.split(b"\x00", 1)[0] == _SID:
            continue  # vorhandenen sdata-Text-Chunk verwerfen (replace)
        if ctype == b"IEND":
            out += _png_itxt(payload)
        out += _png_make_chunk(ctype, cdata)
    return bytes(out)


def _png_extract(data: bytes) -> Optional[str]:
    """Lies die sdata-Nutzlast aus ``iTXt``/``tEXt`` mit Schlüsselwort ``sdata``."""
    for ctype, cdata in _png_chunks(data):
        if ctype == b"iTXt":
            keyword, _, rest = cdata.partition(b"\x00")
            if keyword == _SID:
                rest = rest[2:]                       # compflag + method
                _, _, rest = rest.partition(b"\x00")  # language tag
                _, _, text = rest.partition(b"\x00")  # translated keyword
                return text.decode("utf-8")
        elif ctype == b"tEXt":
            keyword, _, text = cdata.partition(b"\x00")
            if keyword == _SID:
                return text.decode("latin-1")
    return None


# ===================================================================== JPEG
_JPEG_MAGIC = b"\xff\xd8\xff"


def _jpeg_segments(data: bytes) -> Iterator[Tuple[int, int, Optional[int], Optional[bytes]]]:
    """Iteriere ``(start, end, marker, segment_payload)`` ab SOI bis einschließlich SOS.

    ``segment_payload`` ist ``None`` für eigenständige Marker (RSTn/TEM) bzw. ab
    SOS/EOI (dort umfasst die Spanne ``start..len(data)``, also den Rest).
    """
    pos = 2  # nach SOI
    n = len(data)
    while pos < n:
        if data[pos] != 0xFF:
            yield pos, n, None, None      # kein Marker mehr → Rest
            return
        start = pos
        while pos < n and data[pos] == 0xFF:
            pos += 1                      # Füll-Bytes (0xFF) überspringen
        marker = data[pos]
        if marker in (0xDA, 0xD9):        # SOS / EOI → Rest verbatim
            yield start, n, marker, None
            return
        if 0xD0 <= marker <= 0xD7 or marker == 0x01:  # RSTn / TEM: ohne Länge
            yield start, pos + 1, marker, None
            pos += 1
            continue
        (length,) = struct.unpack(">H", data[pos + 1:pos + 3])
        end = pos + 1 + length
        yield start, end, marker, data[pos + 3:end]
        pos = end


def _jpeg_strip(data: bytes) -> bytes:
    """Entferne ein vorhandenes sdata-``APP1``-Segment (SOI bleibt erhalten)."""
    out = bytearray(data[:2])  # SOI
    for start, end, marker, seg in _jpeg_segments(data):
        if marker == 0xE1 and seg is not None and seg.startswith(_JPEG_IDENT):
            continue
        out += data[start:end]
    return bytes(out)


def _jpeg_embed(data: bytes, payload: str) -> bytes:
    """Schreibe ``payload`` als ``APP1``-Segment direkt hinter SOI (replace)."""
    body = _JPEG_IDENT + payload.encode("utf-8")
    if len(body) + 2 > 0xFFFF:
        raise PayloadTooLargeError(
            f"payload too large for a single JPEG APP1 segment "
            f"(max {_JPEG_MAX_PAYLOAD} bytes)")
    segment = b"\xff\xe1" + struct.pack(">H", len(body) + 2) + body
    cleaned = _jpeg_strip(data)
    return cleaned[:2] + segment + cleaned[2:]


def _jpeg_extract(data: bytes) -> Optional[str]:
    """Lies die sdata-Nutzlast aus dem ``APP1``-Segment mit Kennung ``sdata\\0``."""
    for _start, _end, marker, seg in _jpeg_segments(data):
        if marker == 0xE1 and seg is not None and seg.startswith(_JPEG_IDENT):
            return seg[len(_JPEG_IDENT):].decode("utf-8")
    return None


# ====================================================================== JP2
_JP2_MAGIC = b"\x00\x00\x00\x0cjP  \r\n\x87\n"


def _jp2_boxes(data: bytes) -> Iterator[Tuple[bytes, int, int, int]]:
    """Iteriere Top-Level-Boxen als ``(type, box_start, content_start, box_end)``."""
    pos = 0
    n = len(data)
    while pos + 8 <= n:
        (lbox,) = struct.unpack(">I", data[pos:pos + 4])
        tbox = data[pos + 4:pos + 8]
        content_start = pos + 8
        if lbox == 1:                                   # 64-bit XLBox
            (xlbox,) = struct.unpack(">Q", data[pos + 8:pos + 16])
            content_start = pos + 16
            end = pos + xlbox
        elif lbox == 0:                                 # bis Dateiende
            end = n
        else:
            end = pos + lbox
        yield tbox, pos, content_start, end
        if end <= pos:                                  # Schutz vor Endlosschleife
            return
        pos = end


def _jp2_uuid_box(payload: str) -> bytes:
    """``uuid``-Box mit fester sdata-UUID + UTF-8-Nutzlast."""
    content = SDATA_JP2_UUID + payload.encode("utf-8")
    return struct.pack(">I", len(content) + 8) + b"uuid" + content


def _jp2_embed(data: bytes, payload: str) -> bytes:
    """Schreibe ``payload`` als ``uuid``-Box vor die ``jp2c``-Codestream-Box (replace)."""
    out = bytearray()
    for tbox, start, cstart, end in _jp2_boxes(data):
        if tbox == b"uuid" and data[cstart:cstart + 16] == SDATA_JP2_UUID:
            continue  # vorhandene sdata-Box verwerfen (replace)
        if tbox == b"jp2c":
            out += _jp2_uuid_box(payload)
        out += data[start:end]
    return bytes(out)


def _jp2_extract(data: bytes) -> Optional[str]:
    """Lies die sdata-Nutzlast aus der ``uuid``-Box mit der sdata-UUID."""
    for tbox, _start, cstart, end in _jp2_boxes(data):
        if tbox == b"uuid" and data[cstart:cstart + 16] == SDATA_JP2_UUID:
            return data[cstart + 16:end].decode("utf-8")
    return None


# ====================================================================== GIF
_GIF_MAGICS = (b"GIF87a", b"GIF89a")


def _gif_body_start(data: bytes) -> int:
    """Offset hinter Header + Logical Screen Descriptor + Global Color Table."""
    packed = data[10]
    pos = 13  # 6 (Header) + 7 (Logical Screen Descriptor)
    if packed & 0x80:  # Global Color Table vorhanden
        pos += 3 * (2 ** ((packed & 0x07) + 1))
    return pos


def _gif_skip_subblocks(data: bytes, pos: int) -> int:
    """Position direkt hinter einem Sub-Block-Stream (Terminator ``0x00``)."""
    n = len(data)
    while pos < n:
        size = data[pos]
        pos += 1
        if size == 0:
            break
        pos += size
    return pos


def _gif_read_subblocks(data: bytes, pos: int) -> Tuple[bytes, int]:
    """Lies einen Sub-Block-Stream zu ``(bytes, end_pos)`` zusammen."""
    out = bytearray()
    n = len(data)
    while pos < n:
        size = data[pos]
        pos += 1
        if size == 0:
            break
        out += data[pos:pos + size]
        pos += size
    return bytes(out), pos


def _gif_comment_spans(data: bytes) -> Iterator[Tuple[int, int, bytes]]:
    """Iteriere ``(start, end, text)`` jeder Comment-Extension auf Block-Ebene."""
    pos = _gif_body_start(data)
    n = len(data)
    while pos < n:
        intro = data[pos]
        if intro == 0x3B:                       # Trailer
            return
        if intro == 0x2C:                       # Image Descriptor
            packed = data[pos + 9]
            pos += 10
            if packed & 0x80:                   # Local Color Table
                pos += 3 * (2 ** ((packed & 0x07) + 1))
            pos += 1                            # LZW minimum code size
            pos = _gif_skip_subblocks(data, pos)
            continue
        if intro == 0x21:                       # Extension
            label = data[pos + 1]
            sub_start = pos + 2
            if label == 0xFE:                   # Comment Extension
                text, end = _gif_read_subblocks(data, sub_start)
                yield pos, end, text
                pos = end
            else:                               # Graphic Control / Application / …
                pos = _gif_skip_subblocks(data, sub_start)
            continue
        return                                  # unbekannter Block → abbrechen


def _gif_subblocks(payload: bytes) -> bytes:
    """Zerlege ``payload`` in 255-Byte-Sub-Blöcke mit ``0x00``-Terminator."""
    out = bytearray()
    for i in range(0, len(payload), 255):
        chunk = payload[i:i + 255]
        out += bytes([len(chunk)]) + chunk
    out += b"\x00"
    return bytes(out)


def _gif_strip(data: bytes) -> bytes:
    """Entferne vorhandene sdata-Comment-Extensions (replace)."""
    spans = [(s, e) for s, e, t in _gif_comment_spans(data)
             if t.startswith(_GIF_PREFIX)]
    if not spans:
        return data
    out = bytearray()
    prev = 0
    for start, end in spans:
        out += data[prev:start]
        prev = end
    out += data[prev:]
    return bytes(out)


def _gif_embed(data: bytes, payload: str) -> bytes:
    """Schreibe ``payload`` als Comment-Extension hinter den Header (replace)."""
    cleaned = _gif_strip(data)
    at = _gif_body_start(cleaned)
    ext = b"\x21\xfe" + _gif_subblocks(_GIF_PREFIX + payload.encode("utf-8"))
    return cleaned[:at] + ext + cleaned[at:]


def _gif_extract(data: bytes) -> Optional[str]:
    """Lies die sdata-Nutzlast aus der Comment-Extension mit Präfix ``sdata\\0``."""
    for _start, _end, text in _gif_comment_spans(data):
        if text.startswith(_GIF_PREFIX):
            return text[len(_GIF_PREFIX):].decode("utf-8")
    return None


# ===================================================================== WebP
def _webp_chunks(data: bytes) -> Iterator[Tuple[bytes, bytes]]:
    """Iteriere ``(fourcc, chunk_data)`` eines RIFF/WebP (ab dem ``WEBP``-Tag)."""
    pos = 12  # 'RIFF' + size(4) + 'WEBP'
    n = len(data)
    while pos + 8 <= n:
        fourcc = data[pos:pos + 4]
        (size,) = struct.unpack("<I", data[pos + 4:pos + 8])
        body = data[pos + 8:pos + 8 + size]
        yield fourcc, body
        pos += 8 + size + (size & 1)  # ungerade Größe → 1 Pad-Byte


def _webp_embed(data: bytes, payload: str) -> bytes:
    """Schreibe ``payload`` als eigenen ``sdAT``-Chunk ans Ende (replace)."""
    chunks: List[Tuple[bytes, bytes]] = [
        (fourcc, body) for fourcc, body in _webp_chunks(data)
        if fourcc != _WEBP_FOURCC
    ]
    chunks.append((_WEBP_FOURCC, payload.encode("utf-8")))
    out = bytearray()
    for fourcc, body in chunks:
        out += fourcc + struct.pack("<I", len(body)) + body
        if len(body) & 1:
            out += b"\x00"
    return b"RIFF" + struct.pack("<I", len(out) + 4) + b"WEBP" + bytes(out)


def _webp_extract(data: bytes) -> Optional[str]:
    """Lies die sdata-Nutzlast aus dem ``sdAT``-Chunk."""
    for fourcc, body in _webp_chunks(data):
        if fourcc == _WEBP_FOURCC:
            return body.decode("utf-8")
    return None


# ================================================================== Fassade
#: Registry: ``fmt -> (embed, extract)``.
_HANDLERS = {
    "png": (_png_embed, _png_extract),
    "jpeg": (_jpeg_embed, _jpeg_extract),
    "jp2": (_jp2_embed, _jp2_extract),
    "gif": (_gif_embed, _gif_extract),
    "webp": (_webp_embed, _webp_extract),
}


def detect_format(data: bytes) -> Optional[str]:
    """Erkenne das Bildformat an den Magic-Bytes.

    :param data: die Bild-Bytes.
    :return: ``"png"``/``"jpeg"``/``"jp2"``/``"gif"``/``"webp"`` oder ``None``.
    """
    if data.startswith(_PNG_MAGIC):
        return "png"
    if data.startswith(_JPEG_MAGIC):
        return "jpeg"
    if data.startswith(_JP2_MAGIC):
        return "jp2"
    if data[:6] in _GIF_MAGICS:
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def supported_formats() -> Tuple[str, ...]:
    """Die unterstützten Format-Schlüssel (Reihenfolge der Registry)."""
    return tuple(_HANDLERS)


def embed(data: bytes, payload: str, fmt: Optional[str] = None) -> bytes:
    """Bette ``payload`` (Text) nativ in die Bild-Bytes ein (replace-Semantik).

    :param data: die Original-Bild-Bytes.
    :param payload: der einzubettende Text (i. d. R. sdata-Metadaten-JSON).
    :param fmt: Format-Schlüssel; ``None`` → automatische Erkennung.
    :return: neue Bild-Bytes mit eingebetteter sdata-Nutzlast.
    :raises UnsupportedImageFormatError: wenn das Format unbekannt/nicht unterstützt ist.
    :raises PayloadTooLargeError: wenn die Nutzlast nicht in ein Segment passt (JPEG).
    """
    fmt = fmt or detect_format(data)
    if fmt not in _HANDLERS:
        raise UnsupportedImageFormatError(
            f"unsupported image format: {fmt!r} "
            f"(supported: {', '.join(_HANDLERS)})")
    result = _HANDLERS[fmt][0](data, payload)
    logger.debug("embedded %d-byte sdata payload into %s image", len(payload), fmt)
    return result


def extract(data: bytes, fmt: Optional[str] = None) -> Optional[str]:
    """Lies eine eingebettete sdata-Nutzlast aus den Bild-Bytes (Pillow-frei).

    Lenient beim Lesen: unbekannte/nicht unterstützte Formate liefern ``None``
    (kein Fehler), ebenso Bilder ohne eingebettete sdata-Nutzlast.

    :param data: die Bild-Bytes.
    :param fmt: Format-Schlüssel; ``None`` → automatische Erkennung.
    :return: die eingebettete Nutzlast (Text) oder ``None``.
    """
    fmt = fmt or detect_format(data)
    if fmt not in _HANDLERS:
        return None
    return _HANDLERS[fmt][1](data)
