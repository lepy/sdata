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

def test_prefix():
    m = sdata.metadata.Metadata()
    m.set_attr("foo", "bar")
    assert m.get("foo").name == "foo"

    m = sdata.metadata.Metadata()
    m.set_attr("foo", "bar", prefix="pre/")
    assert m.get("foo") is None
    assert m.get("pre/foo").name == "foo"

    foo = sdata.metadata.Attribute(name="foo", value="1", dtype="int", description="a int value")
    m.set_attr(foo, prefix="pre/")
    assert m.get("foo") is None
    assert m.get("pre/foo").name == "foo"

    foo = sdata.metadata.Attribute(name="foo", value="1", dtype="int", description="a int value")
    m.add(foo, prefix="pre/")
    assert m.get("foo") is None
    assert m.get("pre/foo").name == "foo"

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

    filepath = "/tmp/metadata.json"
    meta_json = m4.to_json(filepath=filepath)
    print("meta_json", meta_json)
    m6 = sdata.metadata.Metadata.from_json(filepath=filepath)
    print(m6)
    assert m.get_attr("foo").name==m6.get_attr("foo").name
    assert m.get_attr("foo").value==m6.get_attr("foo").value
    print(m.to_dataframe())

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

# def test_attr_timestamp():
#     attr = sdata.metadata.Attribute(name="create", dtype="timestamp", value='2017-04-27', description="creation date")
#     print(attr)
#     print(type(attr.value))
#     print(attr.value.utc)
#     print(attr.value.local)
#     print(attr.to_dict())
#     print(type(attr.to_dict().get("value")))
#     assert attr.value.utc=='2017-04-27T00:00:00+00:00'
#     # assert attr.value.local=='2017-04-27T02:00:00+02:00'

def test_attr_bool():
    ok = sdata.metadata.Attribute(name="valid", dtype="bool", value=True, description="1/0")
    print(ok)
    print(type(ok.value))
    print("!", ok.value, ok.value is True)
    assert ok.value is True
    # ok.value = 1
    # assert ok.value is True
    nio = sdata.metadata.Attribute(name="invalid", dtype="bool", value=False, description="1/0")
    print(nio)
    assert nio.value is False
    nio.value=0
    # assert nio.value is False
    # print(nio.to_dict())

def test_empty_metadata():
    m = sdata.metadata.Metadata()
    print(m.to_dataframe())

def test_guess_dtype():
    m = sdata.Metadata()

    assert m.guess_dtype_from_value('1.23')[1] == 'float'
    assert m.guess_dtype_from_value('otto1.23')[1] == 'str'
    assert m.guess_dtype_from_value('1.e-3')[1] == 'float'
    assert m.guess_dtype_from_value('1')[1] == 'int'
    assert m.guess_dtype_from_value(1)[1] == 'int'
    assert m.guess_dtype_from_value(False)[1] == 'bool'
    assert m.guess_dtype_from_value(True)[1] == 'bool'
    assert m.guess_dtype_from_value("False")[1] == 'bool'
    # '1.23' -> 'float'
    # 'otto1.23' -> 'str'
    # 1 -> 'int'
    # False -> 'bool'

def test_metadata_from_dict():
    d = {"i":1, "f":1.1, "ii":'1', "ff":'1.1', 'fff':'1.e-4',
         'b':True, 'bb':'True', 'bbb':"false", 'bbbb':False,
         "s":"otto"}
    m = sdata.Metadata()
    m.update_from_dict(d)
    print(m.attributes)
    assert m["i"].dtype == 'int'
    assert m["ii"].dtype == 'int'
    assert m["f"].dtype == 'float'
    assert m["ff"].dtype == 'float'
    assert m["fff"].dtype == 'float'
    assert m["b"].dtype == 'bool'
    assert m["bb"].dtype == 'bool'
    assert m["bbb"].dtype == 'bool'
    assert m["bbbb"].dtype == 'bool'
    assert m["s"].dtype == 'str'

    m = sdata.Metadata.from_dict(d)
    print(m.attributes)
    assert m["i"].dtype == 'int'
    assert m["ii"].dtype == 'int'
    assert m["f"].dtype == 'float'
    assert m["ff"].dtype == 'float'
    assert m["fff"].dtype == 'float'
    assert m["b"].dtype == 'bool'
    assert m["bb"].dtype == 'bool'
    assert m["bbb"].dtype == 'bool'
    assert m["bbbb"].dtype == 'bool'
    assert m["s"].dtype == 'str'

def test_required():
    m = sdata.metadata.Metadata()
    m.set_attr("foo", "bar")
    assert m.is_complete() is True
    m.set_attr("r1", "bar", required=True)
    assert m.is_complete() is True
    m.set_attr("r2", "", required=True)
    assert m.is_complete() is False

if __name__ == '__main__':
    # test_attribute()
    # test_metadata()
    # test_timestamp()
    # test_attr_timestamp()
    # test_attr_bool()
    test_empty_metadata()