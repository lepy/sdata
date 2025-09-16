import pytest
import uuid
import json
import os
import unicodedata
import logging
from typing import Dict, Any
from sdata.base import Base, sdata_factory
import pandas
from sdata import __version__, SUUID, Metadata, Attribute


# Assuming the provided code is in a module, but for testing, we'll paste it here or import.
# For this pytest file, we'll assume the code is executable in the same context.
# To make it work, we'll define the necessary stubs if needed.


@pytest.fixture
def base_instance():
    base = Base(name="test_name", ns_name="test_ns_name")
    print(base.sname)
    print(base.suuid_str)

    return base

def test_base_init_required_name():
    with pytest.raises(ValueError, match="Name cannot be empty"):
        Base(name="")

def test_base_init_default():
    b = Base(name="test")
    assert b.name == "test"
    assert isinstance(b.suuid, SUUID)
    assert b.class_name == "Base"
    assert b.metadata.get(Base.SDATA_VERSION).value == __version__  # Assume __version__ is defined
    assert b.metadata.get(Base.SDATA_CLASS).value == "sdata.base:Base"
    assert b.metadata.get(Base.SDATA_NAME).value == "test"
    assert b.metadata.get(Base.SDATA_SUUID).value == b.suuid.suuid_str
    assert b.metadata.get(Base.SDATA_SNAME).value == b.sname
    assert b.metadata.get(Base.SDATA_PARENT_SNAME).value == ""
    assert b.metadata.get(Base.SDATA_PROJECT_SNAME).value == ""

def test_base_init_with_parent(base_instance):
    parent = Base(name="parent")
    b = Base(name="child", parent=parent)
    assert b.metadata.get(Base.SDATA_PARENT_SNAME).value == parent.sname

def test_base_init_with_project(base_instance):
    project = Base(name="project")
    b = Base(name="child", project=project)
    assert b.metadata.get(Base.SDATA_PROJECT_SNAME).value == project.sname

def test_base_init_with_ns_name():
    b = Base(name="test", ns_name="namespace")
    # Since SUUID.from_name is called, assume it's reproducible
    assert b.suuid.sname.startswith("Base@")  # Based on stub

def test_osname(base_instance):
    base_instance.name = "Häl[l]o.csv"
    assert base_instance.osname == 'hael_l_o_csv'

def test_suuid_properties(base_instance):
    assert isinstance(base_instance.uuid, uuid.UUID)
    assert isinstance(base_instance.huuid, str)
    assert len(base_instance.huuid) == 32
    assert base_instance.suuid_str == "MmY1YzY5MjQ0OWU5NWY5MGE3MTU4NjFmMjgzM2QzNWFCYXNlQHRlc3RfbmFtZQ=="
    assert base_instance.suuid_bytes == b"MmY1YzY5MjQ0OWU5NWY5MGE3MTU4NjFmMjgzM2QzNWFCYXNlQHRlc3RfbmFtZQ=="

# def test_set_suuid_invalid(base_instance):
#     with pytest.raises(SdataUuidException, match="Invalid SUUID string"):
#         base_instance.suuid_str = "invalid"

def test_name_setter(base_instance):
    base_instance.name = "new_name"
    assert base_instance.name == "new_name"
    with pytest.raises(ValueError, match="Name cannot be empty"):
        base_instance.name = ""

def test_description_setter(base_instance):
    base_instance.description = "short"
    assert base_instance.description == "short"
    long_desc = "a" * 1001
    base_instance.description = long_desc
    assert base_instance.description == "a" * 1000 + "..."
    with pytest.raises(ValueError, match="description must be a string"):
        base_instance.description = 123

def test_data_setter(base_instance):
    base_instance.data = {"key": "value"}
    assert base_instance.data == {"key": "value"}
    with pytest.raises(ValueError, match="data must be a dict"):
        base_instance.data = "not dict"

def test_update_data(base_instance):
    base_instance.data = {"a": 1, "b": {"c": 2}}
    base_instance.update_data({"b": {"d": 3}, "e": 4})
    assert base_instance.data == {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
    with pytest.raises(ValueError, match="data must be a dict"):
        base_instance.update_data("not dict")

def test_get_parent(base_instance):
    assert base_instance.get_parent() is None
    parent = Base(name="parent")
    child = Base(name="child", parent=parent)
    assert child.get_parent().sname == parent.sname

def test_get_project(base_instance):
    assert base_instance.get_project() is None
    project = Base(name="project")
    child = Base(name="child", project=project)
    assert child.get_project().sname == project.sname

def test_str_repr(base_instance):
    assert str(base_instance) == f"<{base_instance.sname}>"
    assert repr(base_instance) == str(base_instance)

def test_udf_sdf_mdf(base_instance):
    assert isinstance(base_instance.mdf, pandas.DataFrame)
    assert isinstance(base_instance.udf, pandas.DataFrame)
    assert isinstance(base_instance.sdf, pandas.DataFrame)

def test_set_default_attributes():
    default_attrs = [{"name": "test_attr", "value": 42, "dtype": "int"}]
    b = Base(name="test", default_attributes=default_attrs)
    assert b.metadata.get("test_attr").value == 42

def test_to_dict(base_instance):
    d = base_instance.to_dict()
    assert "metadata" in d
    assert "data" in d
    assert "description" in d
    assert d["data"] == {}
    assert d["description"] == ""
    assert d["metadata"][Base.SDATA_NAME]["value"] == "test_name"

def test_from_dict():
    original = Base(name="test")
    d = original.to_dict()
    restored = Base.from_dict(d)
    assert restored.name == "test"
    assert restored.suuid_str == original.suuid_str
    assert restored.class_name == "Base"

def test_to_json(base_instance):
    json_str = base_instance.to_json()
    assert json.loads(json_str)["metadata"][Base.SDATA_NAME]["value"] == "test_name"

    filepath = "test.json"
    base_instance.to_json(filepath)
    assert os.path.exists(filepath)
    with open(filepath, "r") as f:
        data = json.load(f)
    assert data["metadata"][Base.SDATA_NAME]["value"] == "test_name"
    os.remove(filepath)

def test_from_json():
    original = Base(name="test")
    json_str = original.to_json()
    restored = Base.from_json(json_str)
    assert restored.name == "test"
    assert restored.class_name == "Base"

    filepath = "test.json"
    original.to_json(filepath)
    restored_file = Base.from_json(filepath)
    assert restored_file.name == "test"
    os.remove(filepath)

def test_sdata_factory():
    Material = sdata_factory("Material", name="DP800")
    assert isinstance(Material, Base)
    assert Material.class_name == "Material"
    assert Material.name == "DP800"

    default_attrs = [{"name": "a", "value": 1.2, "dtype": "float"}]
    Material_with_attrs = sdata_factory("Material", name="DP800", default_attributes=default_attrs)
    assert Material_with_attrs.metadata.get("a").value == 1.2

def test_sdata_factory_with_parent():
    parent = Base(name="parent")
    child = sdata_factory("Child", name="child", parent=parent)
    assert child.metadata.get(Base.SDATA_PARENT_SNAME).value == parent.sname

def test_roundtrip_serialization():
    original = Base(name="test", description="desc", data={"key": "value"})
    json_str = original.to_json()
    restored = Base.from_json(json_str)
    assert restored.name == original.name
    assert restored.description == original.description
    assert restored.data == original.data
    assert restored.suuid_str == original.suuid_str

def test_init_with_parent_sname():
    b = Base(name="test", parent_sname="parent_sname")
    assert b.metadata.get(Base.SDATA_PARENT_SNAME).value == "parent_sname"

def test_init_with_project_sname():
    b = Base(name="test", project_sname="project_sname")
    assert b.metadata.get(Base.SDATA_PROJECT_SNAME).value == "project_sname"

def test_invalid_parent_type(caplog):
    with caplog.at_level(logging.WARNING):
        b = Base(name="test", parent="invalid")
    assert "parent must be of type Base" in caplog.text

def test_invalid_project_type(caplog):
    with caplog.at_level(logging.WARNING):
        b = Base(name="test", project="invalid")
    assert "project must be of type Base" in caplog.text