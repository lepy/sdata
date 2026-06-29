# -*- coding: utf-8 -*-
"""Image — ein :class:`~sdata.sclass.blob.Blob` über Bild-Inhalt.

Der Bild-Inhalt liegt als Blob-Content (``uri`` für Dateien, ``bytes`` für
In-Memory-Daten); Pillow wird nur lazy zum Dekodieren genutzt
(:attr:`Image.pil`/:meth:`Image.to_numpy`/:meth:`Image.save`). Pillow ist optional
(``pip install pillow``). sdata-Metadaten können in PNGs eingebettet werden.
"""
import io
import os
import json
import logging
from pathlib import Path

import numpy as np

from sdata.suuid import SUUID
from sdata.metadata import Metadata
from sdata.sclass.blob import Blob

try:
    import PIL.Image
    import PIL.PngImagePlugin
except ImportError:  # pragma: no cover - optionale Abhängigkeit (Pillow)
    PIL = None

logger = logging.getLogger(__name__)


class Image(Blob):
    """Image object based on :class:`~sdata.sclass.blob.Blob`."""

    SDATA_CLS = "sdata.sclass.image.Image"

    @classmethod
    def from_file(cls, filepath, project=None, ns_name=None, **kwargs):
        """Create an Image referencing an image file (kept as ``uri`` content).

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
        return img

    @classmethod
    def from_bytes(cls, name, image_data, project=None, **kwargs):
        """Create an Image from in-memory image bytes.

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

    def _load_embedded_metadata(self) -> None:
        """Merge sdata metadata embedded in a PNG (``img.info['sdata']``), if present."""
        if PIL is None:
            return
        try:
            raw = self.pil.info.get("sdata")
            if raw:
                self.metadata.update_from_usermetadata(Metadata.from_json(raw))
        except Exception as exp:
            logger.debug(f"no embedded sdata metadata: {exp}")

    def save(self, filepath, **kwargs):
        """Save the image to ``filepath``; for PNG the sdata metadata is embedded.

        :param filepath: destination path.
        :raises ImportError: if Pillow is not installed.
        :return: the destination ``filepath``.
        """
        if PIL is None:
            raise ImportError("Pillow is required for Image.save (pip install pillow).")
        img = self.pil
        if str(filepath).lower().endswith(".png"):
            info = PIL.PngImagePlugin.PngInfo()
            info.add_text("sdata", self.metadata.to_json())
            img.save(filepath, "PNG", pnginfo=info)
        else:
            img.save(filepath, **kwargs)
        logger.info(f"Image saved to {filepath}")
        return filepath
