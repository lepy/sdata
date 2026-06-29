import pandas as pd
import io
import os
import base64
from typing import Any, Dict, Optional, Union, Iterable
import logging
from pathlib import Path
from sdata import SUUID
from sdata.metadata import Metadata, Attribute
from sdata.sclass.blob import Blob
from sdata.base import Base
import hashlib
import datetime
from sdata.timestamp import get_utc_timestamp

logger = logging.getLogger(__name__)


class FileReference(Blob):
    SDATA_CLS = "sdata.sclass.filereference.FileReference"

    def __init__(
            self,
            filetype: Optional[str] = '',  # Default to generic binary, e.g., '.pdf', '.png', '.jpg'
            **kwargs: Any
    ) -> None:
        """
        Initialize FileReference as a :class:`~sdata.sclass.blob.Blob` over a file URI.

        The file path is kept as the Blob ``uri`` content, so the reference also
        provides ``content_bytes``/``open``/``exists``/``verify``/``size`` from Blob.

        :param filetype: vestigial; the file suffix is derived from ``name``.
        :param kwargs: Keyword arguments passed to Base (e.g. ``name`` = file path).
        """
        filepath = kwargs.get("name", "noname")
        basename = os.path.basename(filepath)
        kwargs["name"] = basename
        path = Path(filepath)
        # Blob-Grundlage: die Datei als uri-Content -> behält den Pfad (zuvor verloren)
        super().__init__(content_type="uri", value=filepath,
                         filetype=path.suffix.lstrip(".").lower() or "binary", **kwargs)

        self.metadata.add("_sdata_name", basename, description="base name of the file without folder")
        self.metadata.add("_sdata_stem", path.stem, description="file name without suffix")
        self.metadata.add("_sdata_filetype", path.suffix.lower(), description="file suffix")
        self.metadata.add("_sdata_filesize", None, dtype="int", description="file size in bytes")
        self.metadata.add("_sdata_filectime", None, description="UTC file creation date")
        self.metadata.add("_sdata_sha3_256", None, description="SHA-3-256")

    @staticmethod
    def get_hash(filepath):
        sh = hashlib.sha3_256()
        with open(filepath, "rb") as fh:
            sh.update(fh.read())
        content_hash = sh.hexdigest()
        return content_hash

    @classmethod
    def from_file(cls, filepath: str):
        suuid = SUUID.from_file(class_name="FileReference", filepath=filepath)
        fr = cls(name=filepath, suuid=suuid)

        fr.metadata.add("_sdata_sha3_256", cls.get_hash(filepath))

        p = Path(filepath)
        ctime = p.stat().st_ctime
        fr.metadata.add("_sdata_filectime", get_utc_timestamp(datetime.datetime.fromtimestamp(ctime)))

        fr.metadata.add("_sdata_filesize", p.stat().st_size)

        return fr

    @property
    def filetype(self) -> str:
        # robust: _sdata_filetype wird erst nach super().__init__() gesetzt, Blobs
        # _autofill_metadata fragt filetype aber bereits währenddessen ab.
        attr = self.metadata.get("_sdata_filetype")
        return attr.value if attr is not None else ""

    @property
    def stem(self) -> str:
        return self.metadata.get("_sdata_stem").value

    @property
    def ctime(self) -> str:
        return self.metadata.get("_sdata_filectime").value

    def to_dataframe(self):
        df =  self.metadata.to_dataframe()[["value"]].T
        df.index = [self.sname]
        return df

class FileReferences(Base):
    SDATA_CLS = "sdata.sclass.filereference.FileReferences"

    def __init__(
            self,
            **kwargs: Any
    ) -> None:
        """
        Initialize FileReferences with content type, value, and filetype.
        :param kwargs: Keyword arguments passed to Base.__init__ (e.g., name, description).
        :raises ValueError: If invalid content_type or mismatched value type.
        """
        super().__init__(**kwargs)
        self.filereferences = {}

    def add(self, filereference: FileReference) -> None:
        self.filereferences[filereference.sname] = filereference

    def get_filereferences(self) -> Iterable[FileReference]:
        return self.filereferences.values()

    def get_filereferences_df(self) -> pd.DataFrame:
        filereferences = []
        for sname, filereference in self.filereferences.items():
            filereferences.append(filereference.to_dataframe())
        return pd.concat(filereferences)

if __name__ == '__main__':
    fr = FileReference("/tmp/test.xlsx")

    print(fr)