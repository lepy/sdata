import logging
from typing import Any, Dict, List, Optional
from sdata.base import Base
logger = logging.getLogger(__name__)

class FileGroup(Base):
    """
    A derived class from Base that manages a group of files.
    Stores file metadata in self.data['files'] as a dictionary where:
    - Keys are unique file identifiers (e.g., filenames or custom keys).
    - Values are dictionaries containing 'name', 'url' (relative or absolute path),
      'filetype' (e.g., 'pdf', 'txt'), and 'reference' (e.g., file content as bytes,
      or a file handle, or any other reference to the file data).
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize FileGroup.

        :param kwargs: Keyword arguments passed to Base.__init__.
        """
        super().__init__(**kwargs)
        # Initialize the files dictionary if not already present in data
        if 'files' not in self.data:
            self.data['files'] = {}

    def add_file(
            self,
            key: str,
            name: str,
            url: str,
            filetype: str,
            reference: Any,
            overwrite: bool = False
    ) -> None:
        """
        Add a file's metadata to the group.

        :param key: Unique key for the file (e.g., filename or custom identifier).
        :param name: The name of the file.
        :param url: Relative or absolute path to the file.
        :param filetype: The type of the file (e.g., 'pdf', 'csv', 'jpg').
        :param reference: Reference to the file, e.g., bytes content, file object, or other data.
        :param overwrite: If True, overwrite existing entry with the same key.
        :raises ValueError: If key already exists and overwrite is False.
        """
        if key in self.data['files'] and not overwrite:
            raise ValueError(f"File with key '{key}' already exists. Set overwrite=True to replace.")

        self.data['files'][key] = {
            'name': name,
            'url': url,
            'filetype': filetype,
            'reference': reference
        }
        logger.debug(f"Added file '{key}' to {self.sname}")

    def get_file(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a file's metadata by key.

        :param key: The unique key for the file.
        :return: Dictionary with file metadata if found, else None.
        """
        return self.data['files'].get(key)

    def remove_file(self, key: str) -> None:
        """
        Remove a file from the group by key.

        :param key: The unique key for the file.
        :raises KeyError: If the key does not exist.
        """
        if key not in self.data['files']:
            raise KeyError(f"File with key '{key}' not found.")
        del self.data['files'][key]
        logger.debug(f"Removed file '{key}' from {self.sname}")

    def list_files(self) -> List[str]:
        """
        List all file keys in the group.

        :return: List of file keys.
        """
        return list(self.data['files'].keys())

    def to_dict(self) -> Dict[str, Any]:
        """
        Extend Base.to_dict to include the files in data.
        Note: If 'reference' contains non-serializable objects (e.g., file handles),
        they may need custom handling for serialization.
        """
        return super().to_dict()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'FileGroup':
        """
        Create a FileGroup instance from a dictionary.
        Assumes 'data' contains 'files' if previously serialized.
        """
        instance = super().from_dict(d)
        # Ensure 'files' is initialized if missing
        if 'files' not in instance.data:
            instance.data['files'] = {}
        return instance

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    # Erstelle eine FileGroup-Instanz (z.B. für ein Projekt "Dokumentensammlung")
    group = FileGroup(name="Dokumentensammlung", description="Eine Sammlung von PDF- und Text-Dateien.")

    # Füge Dateien hinzu (hier mit Beispieldaten; 'reference' könnte z.B. Bytes oder ein File-Objekt sein)
    group.add_file(
        key="doc1",
        name="Bericht.pdf",
        url="/pfad/zum/bericht.pdf",  # Relativ- oder Absolutpfad
        filetype="pdf",
        reference=b"Beispiel-Inhalt als Bytes"  # Hier Bytes als Platzhalter; könnte auch ein File-Handle sein
    )

    group.add_file(
        key="doc2",
        name="Notizen.txt",
        url="C:\\Dokumente\\notizen.txt",  # Absolutpfad-Beispiel
        filetype="txt",
        reference="Text-Inhalt als String"  # String als Referenz
    )

    # Versuche, eine Datei zu überschreiben (mit overwrite=True)
    group.add_file(
        key="doc1",
        name="Aktualisierter_Bericht.pdf",
        url="/neuer/pfad/zum/bericht.pdf",
        filetype="pdf",
        reference=b"Neuer Inhalt",
        overwrite=True
    )

    # Liste alle Datei-Keys auf
    print("Verfügbare Dateien:", group.list_files())  # Ausgabe: ['doc1', 'doc2']

    # Hole Metadaten einer spezifischen Datei
    file_info = group.get_file("doc1")