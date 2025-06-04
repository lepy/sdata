# DigiPro2Green owncloud tools

from webdav3.client import Client
from pathlib import Path
import os
import logging
from pathlib import Path
from webdav3.client import Client
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OwnCloudVault:
    """
    OwnCloudVault verwaltet einen öffentlichen OwnCloud-Ordner über WebDAV.
    """

    def __init__(self, hostname: str, share_id: str, password: str = ""):
        """
        :param hostname: Basis-URL der OwnCloud, z.B. "https://cloud.example.com"
        :param share_id: Freigabe-Token (aus dem Public-Link)
        :param password: Passwort der Freigabe (leer, wenn keines gesetzt)
        """

        url = f"{hostname.rstrip('/')}/public.php/webdav/"
        options = {
            "webdav_hostname": url,
            "webdav_login":    share_id,
            "webdav_password": password,
        }
        self.client = Client(options)

    def list_remote(self, remote_path: str = "/") -> List[str]:
        """
        Listet Dateien und Unterordner im Remote-Verzeichnis (nicht rekursiv).
        :return: Liste von Namen (Dateien enden nicht auf '/')
        """
        items = self.client.list(remote_path)
        logger.info(f"Remote '{remote_path}': {items}")
        return items

    def upload_file(self, local_path: Path, remote_path: str) -> None:
        """
        Lädt eine einzelne Datei nach Remote hoch.
        """
        logger.info(f"Upload {local_path} → {remote_path}")
        self.client.upload_sync(
            remote_path=str(remote_path),
            local_path=str(local_path)
        )

    def download_file(self, remote_path: str, local_path: Path) -> None:
        """
        Lädt eine einzelne Datei vom Remote herunter.
        """
        local_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Download {remote_path} → {local_path}")
        self.client.download_sync(
            remote_path=remote_path,
            local_path=str(local_path)
        )

    def sync_local_to_remote(self, local_folder: Path, remote_folder: str = "/") -> None:
        """
        Rekursives Hochladen aller Dateien aus local_folder nach remote_folder.
        """
        for file in local_folder.rglob("*"):
            if file.is_file():
                # Pfad relativ zum Basis-Ordner berechnen
                rel = file.relative_to(local_folder).as_posix()
                target = f"{remote_folder.rstrip('/')}/{rel}"
                self.upload_file(file, target)

    def sync_remote_to_local(self, remote_folder: str = "/", local_folder: Path = Path(".")) -> None:
        """
        Rekursives Herunterladen aller Dateien aus remote_folder nach local_folder.
        """
        def _recurse(rpath: str, lpath: Path):
            items = self.client.list(rpath)
            for name in items:
                if name in (".", ".."):
                    continue
                full_r = rpath.rstrip("/") + "/" + name
                full_l = lpath / name
                # Prüfen, ob Verzeichnis (WebDAV markiert Ordner mit '/')
                if name.endswith("/"):
                    _recurse(full_r, full_l)
                else:
                    self.download_file(full_r, full_l)

        local_folder.mkdir(parents=True, exist_ok=True)
        _recurse(remote_folder, local_folder)

if __name__ == '__main__':
    # 1. Vault initialisieren
    vault = OwnCloudVault(
        hostname=None, # "https://cloud.example.com",
        share_id=None, # "abcdefghijklmno",   # Token aus dem Public-Link
        password=None   # leer, falls kein Passwort gesetzt
    )

    # 2. Remote-Inhalt anzeigen
    items = vault.list_remote(remote_path="/")
    print("Remote-Ordner Wurzel enthält:", items)
