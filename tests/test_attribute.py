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