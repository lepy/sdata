import base64
import logging
import hashlib
import os
import io
import typing
from typing import Any, List, Dict, Optional, Literal, Optional, Type
from sdata.base import Base
logger = logging.getLogger(__name__)

# Import fsspec for handling various URI schemes (local file, S3, Zip, etc.)
# Note: fsspec must be installed (pip install fsspec) and for S3, also install s3fs (pip install s3fs)
try:
    import fsspec
except ImportError:
    logger.warn('fsspec not installed')
    fsspec = None

class Blob(Base):
    """
    A derived class from Base that represents a generic binary large object (Blob).
    Stores the content in self.data['content'] as a dictionary with:
    - 'type': 'bytes' for in-memory bytes (base64-encoded for serialization) or 'uri' for a filesystem URI (local path, S3 object, Zip path, etc., handled via fsspec).
    - 'value': The base64-encoded bytes string (for 'bytes') or the URI string (for 'uri').
    - 'filetype': The file type (e.g., 'pdf', 'png', 'jpg', 'txt', or any custom type). This is always stored and serialized.

    Additionally, integrates hash calculations (SHA1 and MD5) from the provided class for integrity checks.
    The actual bytes are loaded lazily when accessed via .content_bytes property, ensuring large content is not loaded unless explicitly requested.
    For serialization in to_dict(), bytes are base64-encoded if type is 'bytes'; URIs are kept as-is.
    Supports PDFs, images (png, jpg), or any arbitrary file types.
    Uses fsspec to handle various URI schemes:
    - Local file: 'file:///path/to/file.pdf' or simply '/path/to/file.pdf'
    - S3: 's3://bucket/key.pdf'
    - Zip: 'zip://innerfile.txt::/path/to/outer.zip'
    """

    ContentType = Literal['bytes', 'uri']

    def __init__(
            self,
            content_type: Optional[ContentType] = 'bytes',
            value: Optional[Any] = None,  # bytes for 'bytes', str URI for 'uri'
            filetype: Optional[str] = 'binary',  # Default to generic binary, e.g., 'pdf', 'png', 'jpg'
            **kwargs: Any
    ) -> None:
        """
        Initialize Blob with content type, value, and filetype.
        No content loading occurs here; loading is lazy via content_bytes property.

        :param content_type: 'bytes' for in-memory bytes or 'uri' for filesystem URI (local, S3, Zip, etc.).
        :param value: The content value - bytes object for 'bytes', URI string for 'uri' (e.g., '/local/path', 's3://bucket/key').
        :param filetype: The type of the file (e.g., 'pdf', 'png', 'jpg', 'txt').
        :param kwargs: Keyword arguments passed to Base.__init__ (e.g., name, description).
        :raises ValueError: If invalid content_type or mismatched value type.
        """
        super().__init__(**kwargs)

        if content_type not in typing.get_args(self.ContentType):
            raise ValueError(f"Invalid content_type: {content_type}")

        self.data['content'] = {
            'type': content_type,
            'filetype': filetype
        }

        self._set_value(value)

        logger.debug(f"Created Blob '{self.sname}' with content_type '{content_type}' and filetype '{filetype}'")

    def _set_value(self, value: Any) -> None:
        """
        Set the 'value' in self.data['content'] based on content_type.
        For 'bytes', store as base64-encoded string; for 'uri', store as str.
        No loading occurs here.
        """
        content = self.data['content']
        ctype = content['type']

        if ctype == 'bytes':
            if not isinstance(value, bytes):
                raise ValueError("For 'bytes' type, value must be a bytes object.")
            content['value'] = base64.b64encode(value).decode('utf-8')
        elif ctype == 'uri':
            if not isinstance(value, str):
                raise ValueError("For 'uri' type, value must be a string URI.")
            content['value'] = value
        else:
            raise ValueError(f"Unknown content_type: {ctype}")

    def set_content(
            self,
            content_type: ContentType,
            value: Any,
            filetype: Optional[str] = None
    ) -> None:
        """
        Update the content type, value, and optionally filetype.
        Clears any cached content to maintain lazy loading.

        :param content_type: New content_type ('bytes' or 'uri').
        :param value: New value (bytes or URI str).
        :param filetype: Optional new filetype (e.g., 'pdf', 'png', 'jpg').
        """
        self.data['content']['type'] = content_type
        if filetype is not None:
            self.data['content']['filetype'] = filetype
        self._set_value(value)
        self.data.pop('content_cached', None)  # Clear cache for lazy reloading
        logger.debug(
            f"Updated Blob '{self.sname}' to content_type '{content_type}' and filetype '{self.data['content']['filetype']}'")

    @property
    def content_bytes(self) -> bytes:
        """
        Lazily load and retrieve the content as bytes (only when this property is accessed).
        If type is 'uri', use fsspec to open and read; if 'bytes', decode from base64.
        Caches the result for subsequent accesses.

        :return: The content as bytes.
        :raises ValueError: If loading fails or no value set.
        :raises Exception: If fsspec encounters an error (e.g., invalid URI, missing dependencies like s3fs for S3).
        """
        if 'content_cached' in self.data:
            return self.data['content_cached']

        content = self.data.get('content')
        if content is None:
            raise ValueError("No content set in Blob.")

        ctype = content.get('type')
        val = content.get('value')
        if val is None:
            raise ValueError("No value set in content.")

        if ctype == 'bytes':
            loaded_bytes = base64.b64decode(val)
        elif ctype == 'uri':
            try:
                with fsspec.open(val, 'rb') as f:
                    loaded_bytes = f.read()
            except Exception as e:
                raise ValueError(f"Failed to load from URI '{val}': {str(e)}")
        else:
            raise ValueError(f"Unknown content_type: {ctype}")

        self.data['content_cached'] = loaded_bytes  # Cache the loaded bytes
        return loaded_bytes

    @property
    def filetype(self) -> str:
        """
        Retrieve the filetype (no content loading required).

        :return: The filetype string (e.g., 'pdf', 'png', 'jpg').
        """
        return self.data['content'].get('filetype', 'binary')

    def exists(self) -> bool:
        """
        Test whether the blob content exists (integrated from provided class).
        For 'uri', checks if the path/URI is accessible via fsspec; for 'bytes', always True if value set.

        :return: True if exists, False otherwise.
        """
        content = self.data.get('content')
        if content is None:
            return False

        ctype = content.get('type')
        val = content.get('value')
        if val is None:
            return False

        if ctype == 'bytes':
            return True  # In-memory, assumes exists if set
        elif ctype == 'uri':
            try:
                return fsspec.core.exists(val)
            except Exception as e:
                logger.warning(f"Failed to check existence for URI '{val}': {str(e)}")
                return False
        else:
            return False

    @property
    def sha1(self) -> Optional[str]:
        """
        Calculate the SHA1 hash of the blob content lazily (integrated from provided class).
        Loads content_bytes if necessary.

        :return: SHA1 hexdigest or None if loading fails.
        """
        try:
            hash_obj = hashlib.sha1()
            self._update_hash(hash_obj)
            return hash_obj.hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute SHA1: {str(e)}")
            return None

    @property
    def md5(self) -> Optional[str]:
        """
        Calculate the MD5 hash of the blob content lazily (integrated from provided class).
        Loads content_bytes if necessary.

        :return: MD5 hexdigest or None if loading fails.
        """
        try:
            hash_obj = hashlib.md5()
            self._update_hash(hash_obj)
            return hash_obj.hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute MD5: {str(e)}")
            return None

    def _update_hash(self, hash_obj: Any, buffer_size: int = 65536) -> None:
        """
        Update the hash object with the blob content (integrated from provided class).
        Uses content_bytes for hashing.

        :param hash_obj: Hash object (e.g., hashlib.sha1() or md5()).
        :param buffer_size: Buffer size for reading (default 65536).
        """
        content_bytes = self.content_bytes  # Lazy load
        bytes_io = io.BytesIO(content_bytes)
        while True:
            data = bytes_io.read(buffer_size)
            if not data:
                break
            hash_obj.update(data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Extend Base.to_dict to include the content dict as-is (with base64 for bytes and filetype).
        Does not include or load the actual content bytes.
        """
        data_copy = self.data.copy()
        data_copy.pop('content_cached', None)  # Remove cache if present
        result = super().to_dict()
        result['data'] = data_copy
        return result

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Blob':
        """
        Create a Blob instance from a dictionary.
        Restores content dict including filetype; no content loading occurs here (lazy via content_bytes).
        """
        instance = super().from_dict(d)
        if 'content' not in instance.data:
            instance.data['content'] = {'type': 'bytes', 'filetype': 'binary'}
        # Validate content structure
        content = instance.data['content']
        if 'type' not in content or 'filetype' not in content:
            raise ValueError("Invalid content structure in dict.")
        if content['type'] == 'bytes' and 'value' in content:
            # Ensure value is base64 string; no need to decode here
            pass
        elif content['type'] == 'uri' and 'value' in content:
            # Ensure value is str
            if not isinstance(content['value'], str):
                raise ValueError("URI value must be a string.")
        return instance

