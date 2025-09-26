import os
from minio import Minio
from minio.error import S3Error
import pandas as pd
from pathlib import Path
from io import BytesIO
import io
import mimetypes
from typing import Optional, Dict, Iterable, BinaryIO

class MinioBucket:
    """Eine Klasse zur Verwaltung eines einzelnen MinIO-Buckets"""

    def __init__(self, endpoint, bucket_name, access_key=None, secret_key=None, secure=True):
        """
        Initialisiert den MinIO-Client und den spezifischen Bucket

        Args:
            endpoint (str): MinIO Server Endpunkt (z.B. 'minio.scale.eu')
            bucket_name (str): Name des Buckets
            access_key (str, optional): Zugriffsschlüssel. Default aus Umgebungsvariablen
            secret_key (str, optional): Geheimer Schlüssel. Default aus Umgebungsvariablen
            secure (bool): HTTPS verwenden wenn True
        """
        self.bucket_name = bucket_name
        self.client = Minio(
            endpoint,
            access_key=access_key or os.environ.get("MINIO_ACCESS_KEY_ID"),
            secret_key=secret_key or os.environ.get("MINIO_SECRET_ACCESS_KEY"),
            secure=secure
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """
        Prüft, ob der Bucket existiert, und erstellt ihn, falls nicht

        Raises:
            Exception: Wenn ein Fehler beim Zugriff oder Erstellen des Buckets auftritt
        """
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"Bucket '{self.bucket_name}' wurde erstellt")
            else:
                print(f"Bucket '{self.bucket_name}' existiert bereits")
        except S3Error as e:
            raise Exception(f"Fehler beim Überprüfen/Erstellen des Buckets {self.bucket_name}: {e}")

    def objectnames(self, recursive: bool=True, filter: str=None):
        try:
            objects = self.client.list_objects(self.bucket_name, recursive=recursive)

            if filter:
                return sorted([obj.object_name for obj in objects if filter in obj.object_name])
            else:
                return sorted([obj.object_name for obj in objects])
        except S3Error as e:
            raise Exception(f"Fehler beim Auflisten der Objekte in {self.bucket_name}: {e}")

    def list(self, recursive: bool=True, filter: str=None):
        """
        Listet alle Objekte im Bucket auf

        Args:
            recursive (bool): Rekursives Auflisten wenn True

        Returns:
            list: Liste der Objekte mit Namen, Größe und letzter Änderung
        """
        try:
            objects = self.client.list_objects(self.bucket_name, recursive=recursive)

            if filter:
                return [(obj.object_name, obj.size, obj.last_modified, Path(obj.object_name).suffix.lower()) for obj in objects if filter in obj.object_name]
            else:
                return [(obj.object_name, obj.size, obj.last_modified, Path(obj.object_name).suffix.lower()) for obj in objects]
        except S3Error as e:
            raise Exception(f"Fehler beim Auflisten der Objekte in {self.bucket_name}: {e}")

    def list_df(self, recursive=True, filter=None):
        """Listet alle Objekte im Bucket auf"""
        object_list = self.list(recursive=recursive, filter=filter)
        return pd.DataFrame(object_list, columns=["filename", "size", "mtime", "suffix"])

    @property
    def df(self):
        """Listet alle Objekte im Bucket auf"""
        return self.list_df()

    def exists(self, object_name):
        """
        Überprüft, ob eine Datei im Bucket existiert

        Args:
            object_name (str): Name des Objekts

        Returns:
            bool: True wenn die Datei existiert, False sonst
        """
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return False
            raise Exception(f"Fehler beim Überprüfen der Datei {object_name}: {e}")

    def upload(self, filepath, objectname=None, force=False):
        """
        Lädt eine Datei in den Bucket hoch, wenn sie nicht existiert oder force=True

        Args:
            file_path (str): Lokaler Pfad zur Datei
            object_name (str, optional): Zielname des Objekts, default ist der Dateiname aus file_path
            force (bool): Wenn True, überschreibt existierende Datei

        Returns:
            bool: True wenn Upload erfolgreich, False wenn Datei existiert und force=False
        """
        try:
            # Wenn object_name nicht angegeben, Dateinamen aus file_path extrahieren
            if objectname is None:
                objectname = os.path.basename(filepath)

            if not force and self.exists(objectname):
                print(
                    f"Datei {objectname} existiert bereits in {self.bucket_name} und wird nicht überschrieben (force=False)")
                return False

            self.client.fput_object(self.bucket_name, objectname, filepath)
            print(f"Datei {objectname} erfolgreich in {self.bucket_name} hochgeladen")
            return True
        except S3Error as e:
            raise Exception(f"Fehler beim Hochladen der Datei {objectname}: {e}")

    def download(self, objectname, filepath=None):
        """
        Lädt eine Datei aus dem Bucket herunter

        Args:
            objectname (str): Name des Objekts im Bucket
            filepath (str, optional): Lokaler Pfad zum Speichern, default ist der gleiche Name im aktuellen Verzeichnis

        Returns:
            bool: True wenn Download erfolgreich, False wenn Datei nicht existiert
        """
        try:
            if not self.exists(objectname):
                print(f"Datei {objectname} existiert nicht in {self.bucket_name}")
                return False

            # Wenn file_path nicht angegeben, Dateinamen im aktuellen Verzeichnis verwenden
            if filepath is None:
                filepath = objectname

            self.client.fget_object(self.bucket_name, objectname, filepath)
            print(f"Datei {objectname} erfolgreich aus {self.bucket_name} heruntergeladen nach {filepath}")
            return True
        except S3Error as e:
            raise Exception(f"Fehler beim Herunterladen der Datei {objectname}: {e}")

    def download_bytes(self, objectname):
        try:
            if not self.exists(objectname):
                print(f"Datei {objectname} existiert nicht in {self.bucket_name}")
                return False

            response = self.client.get_object(self.bucket_name, objectname)
            print(f"Datei bytes {objectname} erfolgreich aus {self.bucket_name} heruntergeladen.")
            data = response.read()
            return data
        except S3Error as e:
            raise Exception(f"Fehler beim Herunterladen der Datei {objectname}: {e}")

    def delete(self, object_name):
        """
        Löscht eine Datei aus dem Bucket

        Args:
            object_name (str): Name des Objekts

        Returns:
            bool: True wenn Löschung erfolgreich, False wenn Datei nicht existiert
        """
        try:
            if not self.exists(object_name):
                print(f"Datei {object_name} existiert nicht in {self.bucket_name}")
                return False

            self.client.remove_object(self.bucket_name, object_name)
            print(f"Datei {object_name} erfolgreich aus {self.bucket_name} gelöscht")
            return True
        except S3Error as e:
            raise Exception(f"Fehler beim Löschen der Datei {object_name}: {e}")

    def upload_bytes(self, data: bytes, objectname: str, *, force: bool=False,
                     content_type: Optional[str]="application/octet-stream",
                     metadata: Optional[Dict[str, str]]=None) -> bool:
        """Bytes direkt hochladen (ohne Datei auf Platte)."""
        try:
            if not force and self.exists(objectname):
                print(f"Datei {objectname} existiert bereits in {self.bucket_name} und wird nicht überschrieben (force=False)")
                return False

            data_stream = BytesIO(data)
            self.client.put_object(
                self.bucket_name,
                objectname,
                data_stream,
                length=len(data),
                content_type=content_type,
                metadata=metadata or {}
            )
            print(f"Bytes -> {objectname} erfolgreich hochgeladen")
            return True
        except S3Error as e:
            raise Exception(f"Fehler beim Hochladen des Objektes {objectname}: {e}")

    def upload_stream(self, stream: BinaryIO, objectname: str, *,
                      length: int = -1,
                      part_size: int = 16 * 1024 * 1024,
                      content_type: Optional[str] = None,
                      metadata: Optional[Dict[str, str]] = None,
                      force: bool = False) -> bool:
        """
        Beliebige Streams (Datei-Handle, HTTP-Stream, BytesIO, Pipe) hochladen.
        - length = -1  -> unbekannte Länge, es wird Multipart-Upload mit part_size genutzt.
        - length >= 0  -> bekannte Länge (performanter, wenn möglich).
        """
        try:
            if not force and self.exists(objectname):
                print(f"Datei {objectname} existiert bereits in {self.bucket_name} und wird nicht überschrieben (force=False)")
                return False

            # Content-Type aus Dateiendung ableiten, falls nicht gesetzt
            if content_type is None:
                guessed, _ = mimetypes.guess_type(objectname)
                content_type = guessed or "application/octet-stream"

            self.client.put_object(
                self.bucket_name,
                objectname,
                data=stream,
                length=length,
                part_size=part_size if length == -1 else None,
                content_type=content_type,
                metadata=metadata or {}
            )
            print(f"Stream -> {objectname} erfolgreich hochgeladen")
            return True
        except S3Error as e:
            raise Exception(f"Fehler beim Stream-Upload {objectname}: {e}")

    def upload_fileobj(self, fileobj: BinaryIO, objectname: str, *,
                       force: bool=False, content_type: Optional[str]=None,
                       metadata: Optional[Dict[str, str]]=None) -> bool:
        """
        Komfortmethode für geöffnete Dateien mit bekannter Größe (seek + tell).
        """
        # Versuche Länge über seek/tell zu bestimmen
        try:
            pos = fileobj.tell()
            fileobj.seek(0, io.SEEK_END)
            length = fileobj.tell() - pos
            fileobj.seek(pos)
        except Exception:
            # Fallback: unbekannte Länge
            length = -1
        return self.upload_stream(fileobj, objectname,
                                  length=length,
                                  content_type=content_type,
                                  metadata=metadata,
                                  force=force)

    @staticmethod
    def iter_to_stream(chunks: Iterable[bytes]) -> io.BufferedReader:
        """
        Wandelt einen Byte-Iterator in ein file-like Objekt mit .read(n) um,
        damit er in put_object() genutzt werden kann.
        """
        class _IterStream(io.RawIOBase):
            def __init__(self, iterator):
                self._it = iter(iterator)
                self._buf = bytearray()
            def readable(self): return True
            def read(self, n=-1):
                if n == -1:
                    return b"".join(list(self._it)) if self._buf == b"" else bytes(self._buf) + b"".join(list(self._it))
                while len(self._buf) < n:
                    try:
                        self._buf += next(self._it)
                    except StopIteration:
                        break
                out = bytes(self._buf[:n])
                del self._buf[:n]
                return out
        return io.BufferedReader(_IterStream(chunks))
