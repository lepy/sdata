# -*- coding: utf-8 -*-
"""sdata.imagemeta — native, format-übergreifende Einbettung von sdata-Metadaten.

Die Metadaten-Schicht ist reiner Python-Code (kein Pillow): die Coverage wird über
**synthetische** Container-Bytes erreicht (PNG/JPEG/JP2/GIF/WebP), die hier per Hand
gebaut werden. Zusätzliche Round-Trips gegen echte, mit Pillow erzeugte Bilder
(am Ende, ``importorskip('PIL')``) validieren die Decodier-Integrität.
"""
import struct
import zlib

import pytest

from sdata import imagemeta as im

PAYLOAD = '{"name": "probe", "ü": "äöü€"}'


# ----------------------------------------------------------------- Builders
def _png_chunk(ctype, cdata):
    crc = zlib.crc32(ctype + cdata) & 0xFFFFFFFF
    return struct.pack(">I", len(cdata)) + ctype + cdata + struct.pack(">I", crc)


def _png(*chunks):
    return im._PNG_MAGIC + b"".join(_png_chunk(ct, cd) for ct, cd in chunks)


def _png_minimal(*extra):
    return _png((b"IHDR", b"\x00" * 13), *extra, (b"IDAT", b"x"), (b"IEND", b""))


def _itxt(keyword, text, compflag=0):
    body = (keyword + b"\x00" + bytes([compflag]) + b"\x00"
            + b"\x00" + b"\x00" + text.encode("utf-8"))
    return (b"iTXt", body)


def _text(keyword, text):
    return (b"tEXt", keyword + b"\x00" + text.encode("latin-1"))


def _box(tbox, content):
    return struct.pack(">I", len(content) + 8) + tbox + content


def _jp2(*boxes):
    return im._JP2_MAGIC + b"".join(boxes)


def _riff_webp(*chunks):
    body = b""
    for fourcc, data in chunks:
        body += fourcc + struct.pack("<I", len(data)) + data
        if len(data) & 1:
            body += b"\x00"
    return b"RIFF" + struct.pack("<I", len(body) + 4) + b"WEBP" + body


def _gif(packed=0x80, gct=b"\x00" * 6, blocks=b"", trailer=True):
    # Header + Logical Screen Descriptor (7) + optional Global Color Table
    out = b"GIF89a" + struct.pack("<HH", 4, 4) + bytes([packed]) + b"\x00\x00"
    if packed & 0x80:
        out += gct
    out += blocks
    if trailer:
        out += b"\x3b"
    return out


def _gif_image_block(local_ct=False):
    """A minimal Image Descriptor block (optional local color table)."""
    packed = 0x80 | 0x00 if local_ct else 0x00  # bit7 = local color table
    desc = b"\x2c" + struct.pack("<HHHH", 0, 0, 4, 4) + bytes([packed])
    if local_ct:
        desc += b"\x11" * 6  # 2-entry local color table (3*2^1)
    desc += b"\x02"          # LZW minimum code size
    desc += b"\x02ab\x00"    # one 2-byte sub-block + terminator
    return desc


# ===================================================================== PNG
def test_png_detect():
    assert im.detect_format(_png_minimal()) == "png"


def test_png_embed_extract_roundtrip():
    out = im.embed(_png_minimal(), PAYLOAD)
    assert im.detect_format(out) == "png"
    assert im.extract(out) == PAYLOAD


def test_png_replace_does_not_duplicate():
    once = im.embed(_png_minimal(), PAYLOAD)
    twice = im.embed(once, "second")
    assert im.extract(twice) == "second"
    assert len(twice) <= len(once) + 8  # replaced, not appended


def test_png_extract_from_text_chunk():
    data = _png_minimal(_text(b"sdata", "from-tEXt"))
    assert im.extract(data) == "from-tEXt"


def test_png_extract_ignores_foreign_keywords():
    data = _png_minimal(_itxt(b"Comment", "x"), _text(b"Author", "y"))
    assert im.extract(data) is None


def test_png_extract_none_when_absent():
    assert im.extract(_png_minimal()) is None


# ===================================================================== JPEG
def _jpeg(*segments, trailer=b"\xff\xda\x00\x00data"):
    return b"\xff\xd8" + b"".join(segments) + trailer


def _app(marker, payload):
    return bytes([0xFF, marker]) + struct.pack(">H", len(payload) + 2) + payload


def test_jpeg_detect_embed_extract():
    src = _jpeg(_app(0xE0, b"JFIF\x00"))  # APP0 like a real JPEG
    assert im.detect_format(src) == "jpeg"
    out = im.embed(src, PAYLOAD)
    assert im.extract(out) == PAYLOAD


def test_jpeg_replace_existing():
    once = im.embed(_jpeg(_app(0xE0, b"JFIF\x00")), PAYLOAD)
    twice = im.embed(once, "second")
    assert im.extract(twice) == "second"


def test_jpeg_standalone_and_nonff_markers():
    # RST0 (standalone, no length) before SOS, then APP1 sdata
    src = (b"\xff\xd8" + b"\xff\xd0"            # SOI + RST0 (standalone)
           + _app(0xE1, im._JPEG_IDENT + b"hi")  # APP1 sdata
           + b"\xff\xda\x00\x00scan")
    assert im.extract(src) == "hi"
    # a non-0xFF byte where a marker is expected terminates the walk (no sdata)
    nonff = b"\xff\xd8" + _app(0xE0, b"X") + b"\x00\x01\x02"  # JFIF magic, then junk
    assert im.detect_format(nonff) == "jpeg"
    assert im.extract(nonff) is None


def test_jpeg_extract_none_when_absent():
    assert im.extract(_jpeg(_app(0xE0, b"JFIF\x00"))) is None


def test_jpeg_payload_too_large():
    huge = "x" * (im._JPEG_MAX_PAYLOAD + 1)
    with pytest.raises(im.PayloadTooLargeError):
        im.embed(_jpeg(_app(0xE0, b"JFIF\x00")), huge)


# ====================================================================== JP2
def test_jp2_detect_embed_extract():
    src = _jp2(_box(b"ftyp", b"jp2 "), _box(b"jp2h", b"\x00" * 4),
              _box(b"jp2c", b"codestream"))
    assert im.detect_format(src) == "jp2"
    out = im.embed(src, PAYLOAD)
    assert im.extract(out) == PAYLOAD


def test_jp2_replace_existing():
    src = _jp2(_box(b"jp2c", b"cs"))
    once = im.embed(src, PAYLOAD)
    twice = im.embed(once, "second")
    assert im.extract(twice) == "second"


def test_jp2_xlbox_64bit_length():
    # jp2h as a 64-bit XLBox (LBox==1) exercises the XLBox branch
    content = b"\x00" * 4
    xlbox = _box_xl(b"jp2h", content)
    src = _jp2(_box(b"ftyp", b"jp2 "), xlbox, _box(b"jp2c", b"cs"))
    out = im.embed(src, PAYLOAD)
    assert im.extract(out) == PAYLOAD


def test_jp2_lbox_zero_to_eof():
    # final jp2c with LBox==0 extends to EOF
    jp2c_eof = struct.pack(">I", 0) + b"jp2c" + b"codestream-to-eof"
    src = _jp2(_box(b"jp2h", b"\x00" * 4)) + jp2c_eof
    out = im.embed(src, PAYLOAD)
    assert im.extract(out) == PAYLOAD


def test_jp2_malformed_box_guard():
    # LBox==1 with XLBox==0 -> end<=pos -> iteration guard returns
    bad = struct.pack(">I", 1) + b"junk" + struct.pack(">Q", 0)
    assert im.extract(im._JP2_MAGIC + bad) is None


def test_jp2_extract_none_when_absent():
    assert im.extract(_jp2(_box(b"jp2c", b"cs"))) is None


def _box_xl(tbox, content):
    # 64-bit length box: LBox=1, then 8-byte XLBox = total length
    total = len(content) + 16
    return struct.pack(">I", 1) + tbox + struct.pack(">Q", total) + content


# ====================================================================== GIF
def test_gif_detect_both_magics():
    assert im.detect_format(_gif()) == "gif"
    assert im.detect_format(b"GIF87a" + b"\x00" * 20) == "gif"


def test_gif_embed_extract_roundtrip():
    src = _gif(blocks=_gif_image_block())
    out = im.embed(src, PAYLOAD)
    assert im.detect_format(out) == "gif"
    assert im.extract(out) == PAYLOAD


def test_gif_replace_existing():
    once = im.embed(_gif(blocks=_gif_image_block()), PAYLOAD)
    twice = im.embed(once, "second")
    assert im.extract(twice) == "second"


def test_gif_large_payload_subblocks():
    big = "y" * 600  # > 255 -> multiple sub-blocks
    out = im.embed(_gif(blocks=_gif_image_block()), big)
    assert im.extract(out) == big


def test_gif_no_global_color_table():
    src = _gif(packed=0x00, blocks=_gif_image_block())  # no GCT
    out = im.embed(src, PAYLOAD)
    assert im.extract(out) == PAYLOAD


def test_gif_local_color_table_and_other_extension():
    # image descriptor WITH local color table + a non-comment (graphic control) ext
    gce = b"\x21\xf9\x04\x00\x00\x00\x00\x00"  # graphic control extension
    src = _gif(blocks=gce + _gif_image_block(local_ct=True))
    out = im.embed(src, PAYLOAD)
    assert im.extract(out) == PAYLOAD


def test_gif_unknown_introducer_stops():
    src = _gif(blocks=b"\x99raw", trailer=False)  # unknown block byte
    assert im.extract(src) is None


def test_gif_extract_none_when_absent():
    assert im.extract(_gif(blocks=_gif_image_block())) is None


# ===================================================================== WebP
def test_webp_detect_embed_extract():
    src = _riff_webp((b"VP8 ", b"pixeldata"))
    assert im.detect_format(src) == "webp"
    out = im.embed(src, PAYLOAD)
    assert im.extract(out) == PAYLOAD


def test_webp_replace_and_padding():
    # odd-length body exercises the RIFF pad byte; replace drops the old sdAT
    once = im.embed(_riff_webp((b"VP8L", b"abc")), "odd")   # 3-byte -> pad
    twice = im.embed(once, "evenpad!")                       # 8-byte -> no pad
    assert im.extract(twice) == "evenpad!"


def test_webp_extract_none_when_absent():
    assert im.extract(_riff_webp((b"VP8 ", b"pixeldata"))) is None


# ====================================================================== TIFF
def _tiff(e="<", extra_entries=()):
    """A minimal classic TIFF: header + IFD0 (ImageWidth) + optional entries."""
    entries = [(256, 3, 1, struct.pack(e + "H", 4) + b"\x00\x00")]  # ImageWidth=4
    entries = sorted(entries + list(extra_entries), key=lambda en: en[0])
    hdr = (b"II\x2a\x00" if e == "<" else b"MM\x00\x2a") + struct.pack(e + "I", 8)
    ifd = struct.pack(e + "H", len(entries))
    for tag, typ, cnt, vf in entries:
        ifd += struct.pack(e + "HHI", tag, typ, cnt) + vf
    ifd += struct.pack(e + "I", 0)
    return hdr + ifd


def test_tiff_detect_both_endians():
    assert im.detect_format(_tiff("<")) == "tiff"
    assert im.detect_format(_tiff(">")) == "tiff"


def test_tiff_embed_extract_le_and_be():
    for e in ("<", ">"):
        out = im.embed(_tiff(e), PAYLOAD)
        assert im.detect_format(out) == "tiff"
        assert im.extract(out) == PAYLOAD


def test_tiff_replace_existing():
    once = im.embed(_tiff("<"), PAYLOAD)
    twice = im.embed(once, "second")
    assert im.extract(twice) == "second"


def test_tiff_tiny_payload_inline():
    out = im.embed(_tiff("<"), "hi")   # ≤4 Byte → inline-Value (kein Offset)
    assert im.extract(out) == "hi"


def test_tiff_extract_none_when_absent():
    assert im.extract(_tiff("<")) is None


# ================================================================== Fassade
def test_detect_unknown_returns_none():
    assert im.detect_format(b"not an image") is None


def test_supported_formats():
    assert im.supported_formats() == ("png", "jpeg", "jp2", "gif", "webp", "tiff")


def test_embed_unsupported_format_raises():
    with pytest.raises(im.UnsupportedImageFormatError):
        im.embed(b"not an image", PAYLOAD)
    with pytest.raises(im.UnsupportedImageFormatError):
        im.embed(b"\x89PNG\r\n\x1a\n...", PAYLOAD, fmt="bmp")  # not in the registry


def test_extract_unknown_format_is_lenient():
    assert im.extract(b"not an image") is None


def test_embed_explicit_fmt():
    out = im.embed(_png_minimal(), PAYLOAD, fmt="png")
    assert im.extract(out, fmt="png") == PAYLOAD


# ----------------------------------------------- real images (Pillow round-trips)
@pytest.fixture
def _pil():
    return pytest.importorskip("PIL.Image")


def _encode(pil, fmt, **kwargs):
    import io
    buf = io.BytesIO()
    pil.new("RGB", (7, 5), (10, 20, 30)).save(buf, fmt, **kwargs)
    return buf.getvalue()


@pytest.mark.parametrize("fmt,kwargs", [
    ("PNG", {}), ("JPEG", {}), ("JPEG2000", {}), ("GIF", {}),
    ("WEBP", {}), ("WEBP", {"lossless": True}), ("TIFF", {}),
])
def test_real_image_roundtrip_keeps_pixels(_pil, fmt, kwargs):
    import io
    raw = _encode(_pil, fmt, **kwargs)
    out = im.embed(raw, PAYLOAD)
    assert im.extract(out) == PAYLOAD
    # the image still decodes and keeps its dimensions (no corruption)
    reopened = _pil.open(io.BytesIO(out))
    reopened.load()
    assert reopened.size == (7, 5)
