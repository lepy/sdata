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

def test_metadata():
    m = sdata.metadata.Metadata()
    m.set_attr("foo", "bar")
    m.set_attr(name="a", value=1.2, unit="MPa", description="a float", dtype="float")
    m.set_attr(name="b", value=1, unit="-", description="a int", dtype="int")
    print(m.attributes)
    a = m.get_attr("a")
    print(a)
    assert a.dtype=="float"
    d = m.to_dict()
    print(d)
    m2 = sdata.metadata.Metadata()
    m2.update_from_dict(d)
    print(m2.to_dict())
    assert m.get_attr("foo").name==m2.get_attr("foo").name
    assert m.get_attr("foo").value==m2.get_attr("foo").value
    m3 = sdata.metadata.Metadata.from_dict(d)
    print("m3", m3.to_dict())
    assert m.get_attr("foo").name==m3.get_attr("foo").name
    assert m.get_attr("foo").value==m3.get_attr("foo").value

    df = m.to_dataframe()
    print(df)
    m4 = sdata.metadata.Metadata.from_dataframe(df)
    print("m4", m4.to_dict())
    assert m.get_attr("foo").name==m4.get_attr("foo").name
    assert m.get_attr("foo").value==m4.get_attr("foo").value

    filepath = "/tmp/metadata.csv"
    m.to_csv(filepath)
    m5 = sdata.metadata.Metadata.from_csv(filepath)
    print("m5", m5.to_dict())
    assert m.get_attr("foo").name==m5.get_attr("foo").name
    assert m.get_attr("foo").value==m5.get_attr("foo").value

def test_timestamp():
    t = sdata.timestamp.TimeStamp()
    print(t)
    print("utc  ", t.utc)
    print("local", t.local)

    t2str = '2017-04-27T13:45:09.039244+02:00'
    t2 = sdata.timestamp.TimeStamp(t2str)
    print(t2)
    print("utc  ", t2.utc)
    print("local", t2.local)
    assert t2.utc=='2017-04-27T11:45:09.039244+00:00'

    t3str = '2017-04-27T13:45:09'
    t3 = sdata.timestamp.TimeStamp(t3str)
    print(t3)
    print("utc  ", t3.utc)
    print("local", t3.local)
    assert t3.utc=='2017-04-27T13:45:09+00:00'

    t4str = '2017-04-27'
    t4 = sdata.timestamp.TimeStamp(t4str)
    print(t4)
    print("utc  ", t4.utc)
    print("local", t4.local)
    assert t4.utc=='2017-04-27T00:00:00+00:00'


if __name__ == '__main__':
    # test_attribute()
    # test_metadata()
    test_timestamp()
