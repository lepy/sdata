# -*- coding: utf-8 -*-
"""Abdeckung von sdata/iolib/hashtree.py (cumulative_hash_list + TreeNode)."""
from sdata.iolib.hashtree import cumulative_hash_list, TreeNode


def test_cumulative_hash_empty():
    assert cumulative_hash_list([]) == []


def test_treenode_paths_and_navigation():
    root = TreeNode("root")
    root.add_path("a/b/c")
    root.add_path("/a/b/d/")
    root.add_path_list([])                     # leer -> return
    assert root.get_child("a/b/c") is not None
    assert root.get_child("a/x") is None       # Pfad existiert nicht
    node = root.get_child("a/b/c")
    assert node.full_name() == "root/a/b/c"
    assert root.full_name() == "root"


def test_treenode_repr_str_lt():
    root = TreeNode("root")
    assert str(root) == "root" and repr(root) == "root"
    assert TreeNode("a") < TreeNode("b")
    assert TreeNode("leaf").repr() == "'leaf'\n"   # kinderlos -> Schleife leer


def test_treenode_serialise_and_search():
    root = TreeNode("root")
    root.add_path("a/b")
    d = root.to_dict()
    assert d["name"] == "root" and "a" in d["children"]
    assert isinstance(root.to_json(), str)
    root.print_tree()                          # visuelle Ausgabe (mehrere Ebenen)
    assert root.get_subtree_by_name("b") is not None
    assert root.get_subtree_by_name("zzz") is None
