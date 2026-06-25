import pandas as pd
import io
import os
import base64
from typing import List, Dict, Any, Optional, Type, Literal, Union, Tuple, BinaryIO, Iterable
import logging
from pathlib import Path
from sdata import SUUID
from sdata.metadata import Metadata, Attribute
# from sdata.sclass.blob import Blob  # Assuming Blob is in sdata.blob or adjust import
from sdata.base import Base
import hashlib
import datetime
from sdata.timestamp import get_utc_timestamp
import zipfile

logger = logging.getLogger(__name__)
from sdata.sclass.filereference import FileReference, FileReferences


class ZipFile(Base):
    SDATA_CLS = "sdata.sclass.zipfile.ZipFile"

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

    def add(self, filepath) -> None:
        filereference = FileReference.from_file(filepath)
        self.filereferences[filereference.sname] = filereference

    def get_filereferences(self) -> Iterable[FileReference]:
        return self.filereferences.values()

    def get_filereferences_df(self) -> pd.DataFrame:
        filereferences = []
        for sname, filereference in self.filereferences.items():
            filereferences.append(filereference.to_dataframe())
        return pd.concat(filereferences)

    def to_zip(
        self,
        filepath: Optional[Union[str, Path]] = None,
        *,
        compresslevel: int = 6,
        deterministic: bool = True,
    ) -> io.BytesIO:
        """
        Serialisiert das Objekt via to_json() und packt es als data.json in ein ZIP.
        - Wenn 'filepath' gesetzt ist, wird die ZIP-Datei geschrieben.
        - Rückgabe ist immer ein BytesIO, beginnend bei Position 0.
        """


        buf = io.BytesIO()
        compression = zipfile.ZIP_DEFLATED

        # Optional: deterministische ZIPs (feste Timestamp -> reproduzierbar)
        for filereference in self.filereferences.values():
            arcname = f"{filereference.sname}.sjson"
            json_str = filereference.to_json()
            if deterministic:
                info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = compression
                with zipfile.ZipFile(buf, mode="w", compression=compression, compresslevel=compresslevel) as zf:
                    zf.writestr(info, json_str)
            else:
                with zipfile.ZipFile(buf, mode="w", compression=compression, compresslevel=compresslevel) as zf:
                    zf.writestr(arcname, json_str)

            buf.seek(0)

            if filepath is not None:
                p = Path(filepath)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(buf.getvalue())
                buf.seek(0)

        return buf

    @classmethod
    def from_zip(
        cls,
        src: Union[str, Path, bytes, io.BytesIO, BinaryIO],
        *,
        member: Optional[str] = None,
        encoding: str = "utf-8",
    ):
        """
        Erzeugt eine Instanz aus einem ZIP, das eine JSON-Datei enthält.
        'src' kann ein Dateipfad, Bytes, BytesIO oder beliebiger file-like Stream sein.
        - 'member': Name des JSON-Eintrags im ZIP. Wenn None:
            * nimm die einzige .json-Datei
            * oder, wenn nur ein Eintrag existiert, nimm diesen
            * sonst Fehler (Mehrdeutigkeit).
        """
        def _open_zipfile(source):
            # Gibt einen Kontextmanager zurück, der ein ZipFile liefert
            if isinstance(source, (str, Path)):
                return zipfile.ZipFile(source, mode="r")
            if isinstance(source, bytes):
                return zipfile.ZipFile(io.BytesIO(source), mode="r")
            if isinstance(source, io.BytesIO):
                source.seek(0)
                return zipfile.ZipFile(source, mode="r")
            # generischer file-like Stream
            try:
                source.seek(0)
            except Exception:  # pragma: no cover - defensiv; ZipFile braucht danach seek
                pass
            return zipfile.ZipFile(source, mode="r")

        with _open_zipfile(src) as zf:
            names = zf.namelist()
            chosen = member
            if chosen is None:
                json_members = [n for n in names if n.lower().endswith(".sjson")]
                if len(json_members) == 1:
                    chosen = json_members[0]
                elif len(json_members) == 0 and len(names) == 1:
                    chosen = names[0]
                else:
                    raise ValueError(
                        f"ZIP enthält {len(names)} Einträge ({names}). Bitte 'member' angeben."
                    )
            data = zf.read(chosen).decode(encoding)
            return cls.from_json(data)
