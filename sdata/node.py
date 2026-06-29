import uuid
import os
import json
import logging
from datetime import datetime
from sdata.contrib.simple_graph_db import Database
from sdata.iolib.vault import FileSystemVault

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class Node:
    def __init__(self, name, vault):
        logging.debug(f"[Node] Creating node: {name}")
        self.name = name
        self.uuid = uuid.uuid4().hex
        self.parents = set()
        self.children = set()
        self.direct_links = set()
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.attributes = {
            "uuid": self.uuid,
            "class_name": self.__class__.__name__
        }  # Key-Value-Attribute für den Node
        self.vault = vault
        self.folder_path = self.vault.create_folder(self)

        self.notes_path = os.path.join(self.folder_path, "notes.md")
        self.json_path = os.path.join(self.folder_path, "node.json")
        self._initialize_notes()

    def _initialize_notes(self):
        if not os.path.exists(self.notes_path):
            with open(self.notes_path, 'w') as notes_file:
                notes_file.write(f"# Notes for Node: {self.name}\n\n")
                logging.debug(f"[Node] Initialized notes for node: {self.name}")

    def add_parent(self, parent_node):
        logging.debug(f"[Node] Adding parent: {parent_node.name} to node: {self.name}")
        self.parents.add(parent_node)
        parent_node.children.add(self)
        self.update_timestamp()
        self.serialize()
        parent_node.update_timestamp()
        parent_node.serialize()

    def add_child(self, child_node):
        logging.debug(f"[Node] Adding child: {child_node.name} to node: {self.name}")
        self.children.add(child_node)
        child_node.parents.add(self)
        self.update_timestamp()
        self.serialize()
        child_node.update_timestamp()
        child_node.serialize()

    def add_direct_link(self, linked_node):
        logging.debug(f"[Node] Adding direct link to node: {linked_node.name} from node: {self.name}")
        self.direct_links.add(linked_node)
        linked_node.direct_links.add(self)
        self.update_timestamp()
        self.serialize()
        linked_node.update_timestamp()
        linked_node.serialize()

    def add_attribute(self, key, value):
        logging.debug(f"[Node] Adding attribute: {key} = {value} to node: {self.name}")
        self.attributes[key] = value
        self.update_timestamp()
        self.serialize()

    def add_note(self, note_text):
        logging.debug(f"[Node] Adding note to node: {self.name}")
        with open(self.notes_path, 'a') as notes_file:
            notes_file.write(f"{note_text}\n\n")
        self.update_timestamp()
        self.serialize()

    def get_siblings(self):
        logging.debug(f"[Node] Getting siblings for node: {self.name}")
        siblings = set()
        for parent in self.parents:
            siblings.update(parent.children)
        siblings.discard(self)  # Entferne den aktuellen Node selbst
        return siblings

    def update_timestamp(self):
        self.updated_at = datetime.now().isoformat()
        self.attributes["updated_at"] = self.updated_at

    def serialize(self):
        logging.debug(f"[Node] Serializing node: {self.name}")
        data = {
            "uuid": self.uuid,
            "name": self.name,
            "parents": [parent.uuid for parent in self.parents],
            "children": [child.uuid for child in self.children],
            "direct_links": [link.uuid for link in self.direct_links],
            "attributes": self.attributes
        }
        with open(self.json_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)

    def __repr__(self):
        return f"Node({self.name}, id={self.uuid})"

    def display(self):
        logging.debug(f"[Node] Displaying node: {self.name} (ID: {self.uuid})")
        print(f"  Parents: {[parent.name for parent in self.parents]}")
        print(f"  Children: {[child.name for child in self.children]}")
        print(f"  Direct Links: {[link.name for link in self.direct_links]}")
        print(f"  Siblings: {[sibling.name for sibling in self.get_siblings()]}")
        print(f"  Attributes: {self.attributes}")


# Beispiel zur Verwendung der Node- und FileSystemVault-Klassen
if __name__ == "__main__":
    logging.debug("[Main] Initializing FileSystemVault and Nodes")
    vault = FileSystemVault("/tmp/vault")
    node_a = Node("A", vault)
    node_b = Node("B", vault)
    node_c = Node("C", vault)
    node_d = Node("D", vault)
    node_e = Node("E", vault)

    logging.debug("[Main] Creating relationships between nodes")
    node_a.add_child(node_b)
    node_a.add_child(node_c)
    node_b.add_parent(node_d)
    node_c.add_direct_link(node_e)

    logging.debug("[Main] Adding attributes and notes")
    node_a.add_attribute("priority", "high")
    node_b.add_attribute("status", "in-progress")

    node_a.add_note("This is a note for Node A.")
    node_b.add_note("This is a note for Node B.")
    node_c.add_note("This is a note for Node C with an image: ![example](example.png)")

    logging.debug("[Main] Displaying nodes")
    node_a.display()
    node_b.display()
    node_c.display()
    node_d.display()
    node_e.display()
