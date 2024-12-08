import uuid
import hashlib
import json

NAMESPACE_SDATA = uuid.uuid5(uuid.NAMESPACE_DNS, "sdata")


def stable_hash_from_list(input_list):
    """
        data = [3.14159265, 42, "hello", 2.7182818]
        hashstr = sdata.iolib.hashtree.stable_hash_from_list(data)
        hashstr == "f54068f9b31cb94d56b454d36c1458877e5e45589684038b5c60097ad45b9052"
    """
    # Konvertiere die Liste in eine normalisierte Zeichenkette
    normalized_str = str([
        round(item, 8) if isinstance(item, float) else item
        for item in input_list
    ])
    # Erstelle einen Hash mit hashlib (z. B. SHA256)
    hash_object = hashlib.sha256(normalized_str.encode('utf-8'))
    return hash_object.hexdigest()


def generate_uuid_from_hash(hash_value):
    """
        data = [3.14159265, 42, "hello", 2.7182818]
        uid = sdata.iolib.hashtree.stable_uuid_from_list(data)
        uid.hex == "f09e3370d8f953398366753ca7e16eb9"
    """
    # Konvertiere den Hashwert in einen String (falls nötig)
    hash_string = str(hash_value)
    namespace = uuid.uuid5(uuid.NAMESPACE_DNS, "sdata")
    return uuid.uuid5(namespace, hash_string).hex


def stable_uuid_from_list(input_list):
    hashstr = stable_hash_from_list(input_list)
    return generate_uuid_from_hash(hashstr)


def stable_hash_from_nested_list(nested_list):
    """
        nested_list = [[3.14159265, 42, "hello", 2.7182818],
                       [1, 1.2,"ssd"],
                       ["a"],
                      ]

        ['f54068f9b31cb94d56b454d36c1458877e5e45589684038b5c60097ad45b9052',
         'ce6bc57403f6d39b1dd30fe7aca428d5de956758551facfbca290500ad9100b3',
         'a326618a43c0b61aff497f4d8a82f4857fe952c5fae156ab94facf4adbf7dcb4']
    """
    return [stable_hash_from_list(x) for x in nested_list]


def stable_uuids_from_nested_list(nested_list):
    """
        nested_list = [[3.14159265, 42, "hello", 2.7182818],
                       [1, 1.2,"ssd"],
                       ["a"],
                      ]

        ['f09e3370d8f953398366753ca7e16eb9',
         'b0465a6b35ce5fd28338e04233c422d7',
         '68bb365dbf5c556faf848a6c8c72b205']
    """
    return [stable_uuid_from_list(x) for x in nested_list]


class TreeNode:
    def __init__(self, name, parent=None):
        self.name = name  # Der Name des Knotens
        self.children = {}  # Kinderknoten
        self.parent = parent  # Elternknoten

    def __lt__(self, other):
        """
        Ermöglicht die Sortierung von TreeNode-Objekten basierend auf ihrem Namen.
        """
        return self.name < other.name

    def get_child(self, path):
        """
        Navigiert den Pfad und gibt den Zielknoten zurück, falls vorhanden.
        :param path: Ein Pfad in der Form "child1/child2".
        :return: Der Zielknoten oder None, falls der Pfad nicht existiert.
        """
        path_list = path.strip("/").split("/")  # Pfad in eine Liste umwandeln
        current_node = self
        for part in path_list:
            if part in current_node.children:
                current_node = current_node.children[part]
            else:
                return None  # Pfad existiert nicht
        return current_node

    def add_path(self, path):
        path_list = path.strip("/").split("/")
        self.add_path_list(path_list)

    def add_path_list(self, path_list):
        if not path_list:
            return

        head, *tail = path_list
        if head not in self.children:
            self.children[head] = TreeNode(head, parent=self)
        self.children[head].add_path_list(tail)

    def repr(self, level=0):
        ret = "  " * level + repr(self.name) + "\n"
        for child in self.children.values():
            ret += child.__repr__(level + 1)
        return ret

    def __repr__(self):
        return self.full_name()

    def __str__(self):
        return self.full_name()

    def to_dict(self):
        """
        Konvertiert den Baum in ein verschachteltes Dictionary.
        """
        return {
            "name": self.name,
            "children": {name: child.to_dict() for name, child in self.children.items()}
        }

    def to_json(self):
        """
        Exportiert den Baum in JSON-Format.
        """
        return json.dumps(self.to_dict(), indent=2)

    def print_tree(self, padding="", is_last=True, is_root=True):
        """
        Druckt den Baum in einer visuellen Struktur mit Verzweigungen.
        :param padding: Aktuelle Einrückung.
        :param is_last: Ob der aktuelle Knoten das letzte Kind ist.
        :param is_root: Ob der aktuelle Knoten der Root-Knoten ist.
        """
        if is_root:
            print(self.name)  # Root-Knoten ohne Verzweigungssymbol
        else:
            branch = "└─" if is_last else "├─"
            print(padding + branch + self.name)
            padding += "   " if is_last else "│  "

        children = sorted(self.children.values())  # Alphabetische Sortierung
        for count, child in enumerate(children):
            child.print_tree(padding, count == (len(children) - 1), is_root=False)

    def full_name(self):
        """
        Gibt den vollständigen Pfad des Knotens zurück, von der Wurzel bis zu diesem Knoten.
        :return: Ein String, der den vollständigen Pfad darstellt.
        """
        if self.parent is None:
            return self.name  # Root-Knoten
        return f"{self.parent.full_name()}/{self.name}"

    def get_subtree_by_name(self, name):
        """
        Sucht im Baum nach einem Knoten mit dem angegebenen Namen.
        :param name: Der Name des gesuchten Knotens.
        :return: Der Knoten (TreeNode), wenn gefunden, sonst None.
        """
        if self.name == name:
            return self  # Aktueller Knoten passt

        for child in self.children.values():
            result = child.get_subtree_by_name(name)
            if result:
                return result  # Knoten gefunden

        return None  # Kein Knoten mit dem Namen gefunden
