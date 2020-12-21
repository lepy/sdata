import sys
import os

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

import sdata.metadata
import numpy as np

def test_attribute():
    a = sdata.metadata.Attribute(name="otto", value="foo")
    print(a)
    assert a.name=="otto"
    assert a.value=="foo"

    a = sdata.metadata.Attribute(name=" otto", value="foo ")
    print(a)
    assert a.name == "otto"
    assert a.value == "foo "

    a = sdata.metadata.Attribute(name="a", value="1.2", dtype="float", description="a float value")
    print(a)
    print(a.dtype, type(a.dtype))
    assert a.name == "a"
    print(a.value, type(a.value))
    assert np.isclose(a.value, 1.2)

    a = sdata.metadata.Attribute(name="a", value="1", dtype="int", description="a int value")
    print(a)
    print(a.dtype, type(a.dtype))
    assert a.name == "a"
    print(a.value, type(a.value))
    assert np.isclose(a.value, 1)
    assert a.dtype=="int"

def test_empty_attribute():
    a = sdata.metadata.Attribute(name="nanstr", value="", dtype="str")
    print(a)
    assert a.name == "nanstr"
    assert a.value == ""

    a = sdata.metadata.Attribute(name="nan", value="")
    print(a)
    assert a.name == "nan"
    assert a.value == ""

def test_attribute_required():
    a = sdata.metadata.Attribute(name="nanstr", value="", dtype="str", required=True)
    assert a.required is True
    a = sdata.metadata.Attribute(name="nanstr", value="", dtype="str", required="true")
    assert a.required is True
    a = sdata.metadata.Attribute(name="nanstr", value="", dtype="str", required=1)
    assert a.required is True
    a = sdata.metadata.Attribute(name="nanstr", value="", dtype="str")
    assert a.required is False
    a = sdata.metadata.Attribute(name="nanstr", value="", dtype="str", required="False")
    assert a.required is False
    a = sdata.metadata.Attribute(name="nanstr", value="", dtype="str", required=False)
    assert a.required is False
    a = sdata.metadata.Attribute(name="nanstr", value="", dtype="str", required=0)
    assert a.required is False
    a = sdata.metadata.Attribute(name="nanstr", value="", dtype="str", required=0)
    a.required = "true"
    assert a.required is True
    a = sdata.metadata.Attribute(name="nanstr", value="", dtype="str", required=0)
    a.required = "True"
    assert a.required is True
    a = sdata.metadata.Attribute(name="nanstr", value="", dtype="str", required=0)
    a.required = 1
    assert a.required is True
    a = sdata.metadata.Attribute(name="nanstr", value="", dtype="str", required=0)
    a.required = "wahr"
    assert a.required is False

def test_to_dict():
    a = sdata.metadata.Attribute(name="nanstr", value="", dtype="str", required=0)
    d = a.to_dict()
    assert d["required"] is False
    a = sdata.metadata.Attribute(name="nanstr", value="", dtype="str", required=1)
    d = a.to_dict()
    assert d["required"] is True
