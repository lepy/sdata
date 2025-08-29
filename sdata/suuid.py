import uuid
import base64
import hashlib
import os
import re
import unicodedata

"""
SUUID
"""


class SUUID:
    """ SUUID = b64(huuid + class_name + SEP + name)

        Eine semantische UUID, die Klasse, Name und eine UUID kombiniert.

        Examples:
            >>> sid = SUUID.from_name(class_name="MyClass", name="MyName")
            >>> str(sid)
            '(MyClass@MyName@78bc2bf739005a7bbc14019f767dbdc1)'

            >>> sid.suuid
            b'NzhiyzJiZjczOTAwNWE3YmJjMTQwMTlmNzY3ZGJkYzFNeUNsYXNzQE15TmFtZQ=='

            >>> sid.suuid_str
            'NzhiyzJiZjczOTAwNWE3YmJjMTQwMTlmNzY3ZGJkYzFNeUNsYXNzQE15TmFtZQ=='

            >>> sid.to_dict()
            {'class_name': 'MyClass',
             'name': 'MyName',
             'huuid': '78bc2bf739005a7bbc14019f767dbdc1',
             'suuid': 'NzhiyzJiZjczOTAwNWE3YmJjMTQwMTlmNzY3ZGJkYzFNeUNsYXNzQE15TmFtZQ=='}
    """

    SEP = "@"

    def __init__(self, class_name, name=None, huuid=None):
        """Generiert ein SUUID-Objekt.

        :param class_name: Name der Klasse, z.B. 'Data' (erforderlich, nicht-leerer String)
        :param name: Name des Objekts, z.B. 'Otto' (optional, default: "")
        :param huuid: Hex-String einer UUID, z.B. 'e1e9eaa45eba5cc1b5f035317771b22c' (optional, default: uuid4().hex)
        """
        if not class_name or not isinstance(class_name, str):
            raise ValueError("class_name muss ein nicht-leerer String sein")
        self.class_name = class_name
        name = name or ""
        self.name = self.generate_safe_filename(name)
        self.huuid = huuid or uuid.uuid4().hex
        if len(self.huuid) != 32 or not all(c in '0123456789abcdefABCDEF' for c in self.huuid):
            raise ValueError("huuid muss ein 32-Zeichen langer Hex-String sein")

    @staticmethod
    def generate_safe_filename(original_name: str) -> str:
        r"""
        Generiert einen sicheren Dateinamen, der kompatibel mit Linux, Windows, AWS S3 und als Datenbank-Spaltenname oder Index-Name ist.

        - Konvertiert zu Lowercase.
        - Ersetzt Umlaute und Sonderzeichen durch ASCII-Äquivalente oder Unterstriche.
        - Erlaubt nur alphanumerische Zeichen (a-z, 0-9), Unterstriche (_) und Punkte (.).
        - Entfernt verbotene Zeichen für Windows (z.B. < > : " / \ | ? *).
        - Reduziert multiple Unterstriche zu einem.
        - Entfernt leading/trailing Unterstriche oder Punkte.
        - Stellt sicher, dass der Name mit einem Buchstaben oder Unterstrich beginnt (für DB-Kompatibilität).
        - Begrenzt die Länge auf 255 Zeichen (sichere Grenze für die meisten Dateisysteme).

        :param original_name: Der ursprüngliche Name (str).
        :return: Der sichere Dateiname (str).
        """
        if not isinstance(original_name, str):
            original_name = str(original_name)

        # Ersetze verbotene Zeichen für Windows und allgemeine Sicherheit
        forbidden = r'[<>:"/\\|?*]'
        original_name = re.sub(forbidden, '_', original_name)

        # Konvertiere Umlaute und andere diakritische Zeichen zu ASCII
        mapper = {
            "ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
            "ß": "ss", " ": "_", "!": "_", "@": "_", "#": "_", "$": "_",
            "%": "_", "^": "_", "&": "_", "*": "_", "(": "_", ")": "_",
            ";": "_", ",": "_", "+": "_", "=": "_", "[": "_", "]": "_",
            "{": "_", "}": "_", "`": "_", "~": "_"
        }
        for k, v in mapper.items():
            original_name = original_name.replace(k, v)

        # Normalisiere zu ASCII und entferne nicht-ASCII-Zeichen
        original_name = unicodedata.normalize('NFKD', original_name).encode('ascii', 'ignore').decode('ascii')

        # Zu Lowercase
        name = original_name.lower()

        # Ersetze ungültige Zeichen mit _
        # Erlaube nur a-z, 0-9, _, .
        name = re.sub(r'[^a-z0-9_.]', '_', name)

        # Reduziere multiple _ oder . zu _
        name = re.sub(r'[_.-]+', '_', name)

        # Entferne leading/trailing _ oder .
        name = name.strip('_.')

        # Stelle sicher, dass es mit einem Buchstaben oder _ beginnt (für DB)
        if name and (name[0].isdigit() or name[0] == '.'):
            name = '_' + name

        # Begrenze auf 255 Zeichen
        if len(name) > 255:
            name = name[:255]

        # Falls der Name leer wird, fallback zu einem Standard
        if not name:
            name = 'noname'

        return name

    def __str__(self):
        return f"({self.class_name}{self.SEP}{self.name}{self.SEP}{self.huuid})"

    def __repr__(self):
        return f"({self.class_name}{self.SEP}{self.name}{self.SEP}{self.huuid})"

    def get_uuid(self):
        """UUID-Objekt aus huuid."""
        return uuid.UUID(hex=self.huuid)

    @property
    def uuid(self):
        """UUID-Objekt aus huuid."""
        return uuid.UUID(hex=self.huuid)

    @property
    def hex(self):
        """Hex-String der UUID."""
        return self.huuid

    def to_list(self):
        """Gibt eine Liste mit [suuid_str, class_name, name, huuid] zurück."""
        return [self.suuid_str, self.class_name, self.name, self.huuid]

    def to_dict(self):
        """Gibt ein Dict mit class_name, name, huuid und suuid_str zurück."""
        return {
            "class_name": self.class_name,
            "name": self.name,
            "huuid": self.huuid,
            "suuid": self.suuid_str
        }

    @property
    def sname(self):
        """String-Repräsentation: class_name@name@huuid"""
        return self.SEP.join([self.class_name, self.name, self.huuid])

    @property
    def suuid_bytes(self):
        """Base64-kodierte Bytes: huuid + class_name + SEP + name"""
        s = self.huuid + self.class_name + self.SEP + self.name
        return base64.b64encode(s.encode())

    @property
    def suuid_str(self):
        """Base64-kodierter String (decoded von suuid)."""
        return self.suuid_bytes.decode().strip()

    @classmethod
    def from_uuid(cls, class_name, uuid_obj):
        """Erstellt SUUID aus class_name und UUID-Objekt (ohne name)."""
        return cls(class_name, name="", huuid=uuid_obj.hex)

    @classmethod
    def get_namespace_from_name(cls, name):
        """Generiert Namespace-UUID aus String."""
        return uuid.uuid5(uuid.NAMESPACE_OID, name.upper())

    @classmethod
    def get_uuid_from_name(cls, name, ns_name=None):
        """Generiert deterministische UUID aus name und optionalem Namespace."""
        nsuuid = uuid.NAMESPACE_OID if ns_name is None else cls.get_namespace_from_name(ns_name)
        return uuid.uuid5(nsuuid, name.upper())

    @classmethod
    def from_name(cls, class_name, name, ns_name=None):
        """Erstellt SUUID deterministisch aus class_name, name und optionalem Namespace."""
        cleaned_name = cls.generate_safe_filename(name)
        uid = cls.get_uuid_from_name(name=class_name + cleaned_name, ns_name=ns_name)
        return cls(class_name=class_name, name=cleaned_name, huuid=uid.hex)

    @classmethod
    def get_suuid_from_name(cls, class_name, name, ns_name=None):
        """Gibt den Base64-Bytes-SUUID aus from_name zurück."""
        suuid_obj = cls.from_name(class_name, name, ns_name)
        return suuid_obj.suuid_bytes

    @classmethod
    def get_sname_from_name(cls, class_name, name, ns_name=None):
        """Gibt den sname-String aus from_name zurück."""
        suuid_obj = cls.from_name(class_name, name, ns_name)
        return suuid_obj.sname

    @classmethod
    def from_file(cls, class_name, filepath, ns_name=None):
        """Erstellt SUUID aus Dateiinhalt (Hash) und Dateinamen."""
        sh = hashlib.sha3_256()
        with open(filepath, "rb") as fh:
            sh.update(fh.read())
        content_hash = sh.hexdigest()
        basename = os.path.basename(filepath)
        suuid_obj = cls.from_name(class_name=class_name, name=content_hash, ns_name=ns_name)
        suuid_obj.name = cls.generate_safe_filename(basename)  # Überschreibt name mit Dateinamen
        return suuid_obj

    @classmethod
    def from_str(cls, class_name, s, ns_name=None):
        """Erstellt SUUID aus String-Inhalt (Hash)."""
        sh = hashlib.sha3_256()
        sh.update(s.encode('utf-8', errors='strict'))  # Raise bei Encoding-Fehlern
        content_hash = "_" + sh.hexdigest()
        return cls.from_name(class_name=class_name, name=content_hash, ns_name=ns_name)

    @classmethod
    def from_suuid_bytes(cls, bytestring):
        """Erstellt SUUID aus Base64-Bytes."""
        id_string = base64.b64decode(bytestring).decode('utf-8')
        return cls.from_idstr(id_string)

    @classmethod
    def from_suuid_str(cls, string):
        """Erstellt SUUID aus Base64-String."""
        id_string = base64.b64decode(string.encode('utf-8')).decode('utf-8')
        return cls.from_idstr(id_string)

    @classmethod
    def from_suuid_sname(cls, s):
        """Erstellt SUUID aus sname-String (class_name@name@huuid)."""
        parts = s.split(cls.SEP)
        if len(parts) != 3:
            raise ValueError("Ungültiger sname-Format: Muss genau zwei Separatoren enthalten")
        class_name, name, huuid = parts
        return cls(class_name=class_name, name=name, huuid=huuid)

    @classmethod
    def from_idstr(cls, id_string):
        """Erstellt SUUID aus decoded Base64-String (huuidclass_name@name)."""
        if len(id_string) < 32:
            raise ValueError("Ungültiger id_string: Zu kurz")
        huuid = id_string[:32]
        rest = id_string[32:]
        try:
            class_name, name = rest.split(cls.SEP, maxsplit=1)
        except ValueError:
            class_name = rest
            name = ""
        return cls(class_name=class_name, name=name, huuid=huuid)


if __name__ == '__main__':
    sid = SUUID.from_name(class_name="DATA", name="otto")
    print(sid)
    print(sid.suuid)
    print(sid.to_dict())
