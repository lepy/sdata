# -*- coding: utf-8 -*-
"""Wiederverwendbarer Integritäts-/Hash-Layer (RFC 0004, Option B).

:class:`ContentIntegrityMixin` stellt Prüfsummen (``sha1``/``md5``/``sha256``),
``size`` sowie ``update_checksum``/``verify`` über einen ``content_bytes``-Hook und
das ``metadata``-Objekt (aus :class:`~sdata.base.Base`) bereit. Genutzt von
:class:`~sdata.sclass.blob.Blob` und :class:`~sdata.sclass.dataframe.DataFrame`.
"""
import io
import hashlib
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ContentIntegrityMixin:
    """Hash/``verify``/``size`` über ``self.content_bytes`` + ``self.metadata``.

    Subklassen liefern eine ``content_bytes``-Property (``bytes``) und besitzen
    (über :class:`~sdata.base.Base`) ein ``metadata``-Objekt.
    """

    def _update_hash(self, hash_obj: Any, buffer_size: int = 65536) -> None:
        """Speise den Hash-Objekt-Stream aus ``content_bytes`` (chunked)."""
        bytes_io = io.BytesIO(self.content_bytes)
        while True:
            data = bytes_io.read(buffer_size)
            if not data:
                break
            hash_obj.update(data)

    def _content_hexdigest(self, algo) -> Optional[str]:
        """Hex-Digest des Inhalts mit ``algo`` (z. B. ``hashlib.sha256``); ``None`` bei Fehler."""
        try:
            hash_obj = algo()
            self._update_hash(hash_obj)
            return hash_obj.hexdigest()
        except Exception as exp:
            logger.error(f"Failed to compute {algo().name}: {exp}")
            return None

    @property
    def sha1(self) -> Optional[str]:
        """SHA-1 hex digest of the content (lazy; ``None`` on error)."""
        return self._content_hexdigest(hashlib.sha1)

    @property
    def md5(self) -> Optional[str]:
        """MD5 hex digest of the content (lazy; ``None`` on error)."""
        return self._content_hexdigest(hashlib.md5)

    @property
    def sha256(self) -> Optional[str]:
        """SHA-256 hex digest of the content (lazy; ``None`` on error)."""
        return self._content_hexdigest(hashlib.sha256)

    @property
    def size(self) -> Optional[int]:
        """Size of the content in bytes (lazy; ``None`` on error)."""
        try:
            return len(self.content_bytes)
        except Exception as exp:
            logger.error(f"Failed to determine size: {exp}")
            return None

    def update_checksum(self) -> Optional[str]:
        """Store the SHA-256 of the content in the ``checksum`` metadata (``schema:sha256``).

        :return: the stored SHA-256 hex digest (``None`` if the content is unavailable).
        """
        digest = self.sha256
        self.metadata.set_attr("checksum", digest)
        return digest

    def verify(self) -> bool:
        """Verify the content against the stored ``checksum`` (SHA-256) metadata.

        :return: ``True`` iff a checksum is stored and matches the current content;
          ``False`` on mismatch or when no checksum has been stored yet.
        """
        attr = self.metadata.get("checksum")
        stored = attr.value if attr is not None else None
        if not stored:
            logger.warning("verify: no checksum stored (call update_checksum first)")
            return False
        return stored == self.sha256
