# -*- coding: utf-8 -*-
"""Image — ein :class:`~sdata.sclass.blob.Blob` über Bild-Inhalt.

Der Bild-Inhalt liegt als Blob-Content (``uri`` für Dateien, ``bytes`` für
In-Memory-Daten). sdata-Metadaten werden **format-übergreifend nativ** in die
Bilddatei eingebettet (PNG/JPEG/JP2/GIF/WebP/TIFF) — über :mod:`sdata.imagemeta`,
das ohne Pillow auskommt. Formate **ohne** nativen Metadaten-Träger (z. B. BMP)
erhalten einen verlustfreien ``<filepath>.meta.json``-**Sidecar**; die ``save``/
``from_file``-API ist für alle Formate identisch. Pillow wird nur lazy zum
**Dekodieren/Transkodieren** der Pixel genutzt (:attr:`Image.pil`/
:meth:`Image.to_numpy`/:meth:`Image.save` bei Formatwechsel) und ist optional
(``pip install pillow``).
"""
import io
import os
import logging
from pathlib import Path

import numpy as np

from sdata import imagemeta
from sdata.suuid import SUUID
from sdata.metadata import Metadata
from sdata.sclass.blob import Blob

try:
    import PIL.Image
except ImportError:  # pragma: no cover - optionale Abhängigkeit (Pillow)
    PIL = None

logger = logging.getLogger(__name__)


class Image(Blob):
    """Image object based on :class:`~sdata.sclass.blob.Blob`."""

    SDATA_CLS = "sdata.sclass.image.Image"

    #: Datei-Endung → (Pillow-Format, :mod:`sdata.imagemeta`-Format) für :meth:`save`.
    _SUFFIX_FORMATS = {
        "png": ("PNG", "png"),
        "jpg": ("JPEG", "jpeg"), "jpeg": ("JPEG", "jpeg"), "jpe": ("JPEG", "jpeg"),
        "jp2": ("JPEG2000", "jp2"), "j2k": ("JPEG2000", "jp2"),
        "jpf": ("JPEG2000", "jp2"), "jpx": ("JPEG2000", "jp2"),
        "gif": ("GIF", "gif"),
        "webp": ("WEBP", "webp"),
        "tif": ("TIFF", "tiff"), "tiff": ("TIFF", "tiff"),
    }

    @classmethod
    def from_file(cls, filepath, project=None, ns_name=None, **kwargs):
        """Create an Image referencing an image file (kept as ``uri`` content).

        Any sdata metadata is read back and merged: natively embedded
        (PNG/JPEG/JP2/GIF/WebP/TIFF, Pillow-free) and/or from an adjacent
        ``<filepath>.meta.json`` sidecar (for formats without a native container).

        :param filepath: path to the image file.
        :param project: namespace for the deterministic SUUID (alias of ``ns_name``).
        :param ns_name: namespace for the deterministic SUUID.
        :param kwargs: forwarded to :class:`Blob`/:class:`~sdata.base.Base`.
        :return: an :class:`Image` instance.
        """
        suuid = SUUID.from_file("Image", filepath, ns_name=ns_name or project)
        suffix = Path(filepath).suffix.lstrip(".").lower() or "binary"
        img = cls(content_type="uri", value=filepath, filetype=suffix,
                  name=os.path.basename(filepath), suuid=suuid, **kwargs)
        img._load_embedded_metadata()
        img._load_sidecar_metadata(filepath)
        return img

    @classmethod
    def from_bytes(cls, name, image_data, project=None, **kwargs):
        """Create an Image from in-memory image bytes.

        Any embedded sdata metadata is read back and merged (Pillow-free).

        :param name: a name for the image (its suffix sets the filetype).
        :param image_data: the raw image bytes.
        :param project: namespace for the deterministic SUUID.
        :return: an :class:`Image` instance.
        """
        suuid = SUUID.from_str("Image", name, ns_name=project)
        suffix = Path(name).suffix.lstrip(".").lower() or "binary"
        img = cls(content_type="bytes", value=image_data, filetype=suffix,
                  name=name, suuid=suuid, **kwargs)
        img._load_embedded_metadata()
        return img

    @property
    def pil(self):
        """The image decoded lazily with Pillow (:class:`PIL.Image.Image`)."""
        if PIL is None:
            raise ImportError("Pillow is required for Image decoding (pip install pillow).")
        return PIL.Image.open(io.BytesIO(self.content_bytes))

    def to_numpy(self) -> np.ndarray:
        """The image as a NumPy array (colour channels)."""
        return np.array(self.pil)

    @property
    def basename(self) -> str:
        """The image file base name (== ``name``)."""
        return self.name

    def embedded_metadata(self):
        """Return the sdata metadata embedded in the image bytes, or ``None``.

        Reads the native sdata payload (PNG ``iTXt`` / JPEG ``APP1`` / JP2 ``uuid``
        box / GIF comment / WebP ``sdAT`` chunk) without Pillow.

        :return: a :class:`~sdata.metadata.Metadata`, or ``None`` if absent/invalid.
        """
        raw = imagemeta.extract(self.content_bytes)
        if not raw:
            return None
        try:
            return Metadata.from_json(raw)
        except Exception as exp:
            logger.debug(f"embedded sdata metadata not parseable: {exp}")
            return None

    def _load_embedded_metadata(self) -> None:
        """Merge sdata metadata embedded in the image bytes (any supported format)."""
        try:
            embedded = self.embedded_metadata()
        except Exception as exp:  # e.g. unreadable uri content
            logger.debug(f"no embedded sdata metadata: {exp}")
            return
        if embedded is not None:
            self.metadata.update_from_usermetadata(embedded)

    @staticmethod
    def sidecar_path(filepath) -> str:
        """Path of the metadata sidecar for ``filepath`` (``<filepath>.meta.json``)."""
        return str(filepath) + ".meta.json"

    def write_sidecar(self, filepath) -> str:
        """Write the sdata metadata next to ``filepath`` as a lossless JSON sidecar.

        The sidecar carries the **same** payload as the embedded form
        (``metadata.to_json()``), so a round-trip is lossless regardless of whether
        the format has a native metadata container.

        :param filepath: the image path the sidecar belongs to.
        :return: the sidecar path (``<filepath>.meta.json``).
        """
        sidecar = self.sidecar_path(filepath)
        with open(sidecar, "w", encoding="utf-8") as fh:
            fh.write(self.metadata.to_json())
        logger.info(f"Image metadata sidecar written to {sidecar}")
        return sidecar

    def _load_sidecar_metadata(self, filepath) -> None:
        """Merge metadata from an adjacent ``<filepath>.meta.json`` sidecar, if present."""
        sidecar = self.sidecar_path(filepath)
        if not os.path.exists(sidecar):
            return
        try:
            with open(sidecar, "r", encoding="utf-8") as fh:
                md = Metadata.from_json(fh.read())
            self.metadata.update_from_usermetadata(md)
            logger.debug(f"merged sidecar metadata from {sidecar}")
        except Exception as exp:
            logger.debug(f"sidecar metadata not loadable: {exp}")

    def save(self, filepath, sidecar=None, **kwargs):
        """Save the image to ``filepath`` with sdata metadata — one API for all formats.

        The container is chosen from the file suffix. For a format with a native
        metadata container (PNG/JPEG/JP2/GIF/WebP/TIFF) the metadata is **embedded**:
        without re-encoding if the stored bytes already use that container (lossless,
        Pillow-free), otherwise Pillow transcodes first. For **any other** format
        (e.g. BMP) the image is written via Pillow and the metadata travels in a
        lossless ``<filepath>.meta.json`` **sidecar** — so metadata is never lost.

        :param filepath: destination path (its suffix selects the format).
        :param sidecar: sidecar policy — ``None`` (default) writes a sidecar only when
          the format has no native container; ``True`` always writes one (in addition
          to embedding); ``False`` never writes one.
        :param kwargs: forwarded to ``PIL.Image.save`` when transcoding.
        :raises ImportError: if Pillow is required (transcode / non-native format) but
          not installed.
        :return: the destination ``filepath``.
        """
        suffix = Path(filepath).suffix.lstrip(".").lower()
        target = self._SUFFIX_FORMATS.get(suffix)

        if target is None:
            # Kein nativer Metadaten-Träger → Pillow schreiben + verlustfreier Sidecar.
            if PIL is None:
                raise ImportError("Pillow is required for Image.save (pip install pillow).")
            self.pil.save(filepath, **kwargs)
            if sidecar is not False:
                self.write_sidecar(filepath)
                logger.info("Image.save: '%s' has no native metadata container; "
                            "metadata written to a sidecar", filepath)
            return filepath

        pil_format, meta_fmt = target
        src = self.content_bytes
        if imagemeta.detect_format(src) == meta_fmt:
            img_bytes = src                      # passender Container → kein Transkodieren
        else:
            if PIL is None:
                raise ImportError("Pillow is required to transcode images "
                                  "(pip install pillow).")
            buffer = io.BytesIO()
            self.pil.save(buffer, pil_format, **kwargs)
            img_bytes = buffer.getvalue()

        img_bytes = imagemeta.embed(img_bytes, self.metadata.to_json(), meta_fmt)
        with open(filepath, "wb") as fh:
            fh.write(img_bytes)
        if sidecar is True:
            self.write_sidecar(filepath)
        logger.info(f"Image saved to {filepath}")
        return filepath
