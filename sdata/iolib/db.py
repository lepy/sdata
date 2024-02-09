from abc import ABC, abstractmethod
from tinydb import TinyDB, Query
#from google.cloud import firestore

class Database(ABC):
    @abstractmethod
    def insert(self, data):
        pass

    @abstractmethod
    def read(self, identifier):
        pass

    @abstractmethod
    def update(self, identifier, data):
        pass

    @abstractmethod
    def delete(self, identifier):
        pass

class TinyDBWrapper(Database):
    def __init__(self, filepath):
        self.db = TinyDB(filepath)

    def insert(self, data):
        # Implementieren Sie die Einfüge-Logik für TinyDB
        obj = Query()
        i = self.db.upsert(data, obj.uuid==data["uuid"])
        print(f"Daten eingefügt: {data}: [{i}]")

    def read(self, identifier):
        # Implementieren Sie die Lese-Logik für TinyDB
        obj = Query()
        result = self.db.search(obj.uuid == identifier)
        print(f"Gefundene Daten: {result}")
        return result

    def update(self, identifier, data):
        # Implementieren Sie die Aktualisierungs-Logik für TinyDB
        obj = Query()
        self.db.update(data, obj.uuid == identifier)
        print(f"Daten aktualisiert: von {identifier} zu {data}")

    def delete(self, identifier):
        # Implementieren Sie die Lösch-Logik für TinyDB
        obj = Query()
        self.db.remove(obj.uuid == identifier)
        print(f"Daten gelöscht für: {identifier}")


# class FirestoreDB(Database):
#     def __init__(self):
#         self.db = firestore.Client()
#
#     def insert(self, data):
#         # Implementieren Sie die Einfüge-Logik für Firestore
#         pass
#
#     def read(self, identifier):
#         # Implementieren Sie die Lese-Logik für Firestore
#         pass
#
#     def update(self, identifier, data):
#         # Implementieren Sie die Aktualisierungs-Logik für Firestore
#         pass
#
#     def delete(self, identifier):
#         # Implementieren Sie die Lösch-Logik für Firestore
#         pass

# Verwendung der API
def main():
    # Wählen Sie das Backend (FirestoreDB oder TinyDBWrapper)
    db = TinyDBWrapper("/tmp/tdb.json")  # oder TinyDBWrapper('path_to_db.json')

    # Fügen Sie Daten ein
    db.insert({"name": "Beispiel", "wert": 123, "uuid": 'c224fddec28245309cc4fe4912ac951f'})

    # Lesen, Aktualisieren und Löschen Sie Daten entsprechend

if __name__ == "__main__":
    print("!")

    main()

