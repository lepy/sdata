print(1)
from tinydb import TinyDB, Query

# TinyDB Datenbank initialisieren
db = TinyDB('db.json')

# Daten einfügen
def insert_data():
    db.insert({'typ': 'Frucht', 'name': 'Apfel'})
    db.insert({'typ': 'Gemüse', 'name': 'Karotte'})
    print("Daten eingefügt.")

# Daten lesen
def read_data():
    # Alle Dokumente lesen
    alle_dokumente = db.all()
    print("Alle Dokumente:", alle_dokumente)

    # Spezifisches Dokument suchen
    Frucht = Query()
    frucht_dokumente = db.search(Frucht.typ == 'Frucht')
    print("Frucht Dokumente:", frucht_dokumente)

# Daten aktualisieren
def update_data():
    Gemuese = Query()
    db.update({'name': 'Tomate'}, Gemuese.name == 'Karotte')
    print("Daten aktualisiert.")

# Daten löschen
def delete_data():
    Frucht = Query()
    db.remove(Frucht.typ == 'Frucht')
    print("Frucht Daten gelöscht.")

# Beispielverwendung
insert_data()
read_data()
update_data()
read_data()
delete_data()
read_data()
