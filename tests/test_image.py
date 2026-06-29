# -*- coding: utf-8 -*-
"""Image(Blob) — RFC 0003 Teil B: Image auf Blob (Bild als Content), PIL lazy.

Pillow ist optional und nicht in der kanonischen CI -> dieser Test skippt dort;
image.py bleibt in der Coverage-``omit``. Verifiziert in Umgebungen mit Pillow.
"""
import os
import pytest

pytest.importorskip("PIL")

from sdata.sclass.blob import Blob
from sdata.sclass.image import Image

modulepath = os.path.dirname(__file__)


def _img(name):
    return os.path.join(modulepath, "images", name)


def test_image_from_file_identity():
    png = Image.from_file(_img("a.png"), project="ImageProject", description="a png image")
    assert png.name == "a.png"
    assert isinstance(png, Blob)

    png = Image.from_file(_img("sdata.png"), ns_name="ImageProject", description="a png image")
    assert png.name == "sdata.png"
    assert png.sname == "Image__sdata_png__f4cacf348db05dcfb36b8174985290e6"

    jpg = Image.from_file(_img("sdata.jpg"), ns_name="ImageProject", description="a jpg image")
    assert jpg.name == "sdata.jpg"
    assert jpg.sname == "Image__sdata_jpg__d0874e8e90d95e3988027658fb9000d5"


def test_image_blob_capabilities():
    png = Image.from_file(_img("sdata.png"), ns_name="ImageProject")
    assert png.data["content"]["type"] == "uri"        # Bild als uri-Content
    assert png.exists() is True
    assert png.size and png.size > 0                   # geerbte Blob-Größe
    assert len(png.sha256) == 64                        # geerbte Blob-Integrität
    arr = png.to_numpy()                                # PIL-Dekodierung
    assert arr.ndim >= 2
    assert png.pil.size[0] > 0


def test_image_from_bytes_and_png_metadata_roundtrip(tmp_path):
    import PIL.Image
    src = tmp_path / "src.png"
    PIL.Image.new("RGB", (4, 3), (10, 20, 30)).save(str(src), "PNG")

    img = Image.from_bytes("pic.png", src.read_bytes())
    img.metadata.add("exposure", 1.5, unit="s", description="exposure time")

    out = str(tmp_path / "out.png")
    img.save(out)                                       # bettet sdata-Metadaten ein
    reloaded = Image.from_file(out)
    assert reloaded.metadata.get("exposure").value == 1.5
    assert reloaded.to_numpy().shape == (3, 4, 3)       # (Höhe, Breite, Kanäle)


@pytest.mark.parametrize("ext,pil_format,kwargs", [
    ("png", "PNG", {}),
    ("jpg", "JPEG", {}),
    ("jp2", "JPEG2000", {}),
    ("gif", "GIF", {}),
    ("webp", "WEBP", {}),
])
def test_image_metadata_roundtrip_all_formats(tmp_path, ext, pil_format, kwargs):
    """Einheitliche API: Metadaten schreiben→lesen über PNG/JPEG/JP2/GIF/WebP."""
    import io
    import PIL.Image

    buf = io.BytesIO()
    PIL.Image.new("RGB", (6, 4), (30, 60, 90)).save(buf, pil_format, **kwargs)

    img = Image.from_bytes(f"pic.{ext}", buf.getvalue())
    img.metadata.add("operator", "ada", description="who acquired the image")

    out = str(tmp_path / f"out.{ext}")
    img.save(out)                                       # gleiche API für alle Formate

    reloaded = Image.from_file(out)
    assert reloaded.metadata.get("operator").value == "ada"
    assert reloaded.pil.size == (6, 4)                  # Pixel/Dimensionen intakt
    # Metadaten sind nativ in der Datei (Pillow-frei lesbar)
    assert reloaded.embedded_metadata() is not None


def test_image_save_transcodes_between_formats(tmp_path):
    """save() in ein anderes Format transkodiert via Pillow und bettet ein."""
    import io
    import PIL.Image

    buf = io.BytesIO()
    PIL.Image.new("RGB", (5, 5), (1, 2, 3)).save(buf, "PNG")
    img = Image.from_bytes("pic.png", buf.getvalue())   # PNG-Quelle
    img.metadata.add("note", "transcoded")

    out = str(tmp_path / "out.webp")                    # Ziel: WebP (Formatwechsel)
    img.save(out)
    reloaded = Image.from_file(out)
    assert reloaded.metadata.get("note").value == "transcoded"
    assert reloaded.filetype == "webp"
