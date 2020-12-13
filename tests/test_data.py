import sys
import os
import pandas as pd

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

import sdata
import uuid

def test_data():
    testname = "testdata"
    data = sdata.Data(name=testname)
    print(data)
    print(data.uuid)
    assert data.name == testname

    uuidstr = "b1fd2643af554b33b04422070a0dc7c7"
    # uuidstr2 = "b1fd2643-af55-4b33-b044-22070a0dc7c7"
    uuidobj = uuid.UUID(uuidstr)
    data2 = sdata.Data(name=testname+"2", uuid=uuidstr)
    print(data2, uuidobj)
    print(data2.uuid,uuidobj.hex)

    assert data2.uuid == uuidobj.hex

def test_group():

    data1 = sdata.Data(name="data1", uuid="38b26864e7794f5182d38459bab8584f")
    data2 = sdata.Data(name="data2", uuid="b1fd2643-af55-4b33-b044-22070a0dc7c7")
    data3 = sdata.Data(name="data3", uuid=uuid.UUID("664577c2d3134b598bc4d6c13f20b71a"))
    print(data3.uuid)

    group1 = sdata.Data(name="group1", uuid="dbc894745fb04f7e87a990bdd4ba97c4")
    print(group1)
    group1.add_data(data1)
    group1.add_data(data2)
    group1.add_data(data3)
    print(group1.group)
    data1a = group1.get_data_by_uuid(uid="38b26864e7794f5182d38459bab8584f")
    assert data1a.name == "data1"
    assert data1a.uuid == "38b26864e7794f5182d38459bab8584f"

    data3a = group1.get_data_by_uuid(uid="664577c2d3134b598bc4d6c13f20b71a")
    print(data3a)
    assert data3a.name == "data3"
    assert data3a.uuid == "664577c2d3134b598bc4d6c13f20b71a"

def test_filename():
    data = sdata.Data(name="data1#2/3!4")
    print(data.filename)
    assert data.filename=="data1_2_3_4"

def test_to_json():
    df = pd.DataFrame({'a': ['x', 'y', '', 'z'], 'b': [1, 2, 2, 3.2]})
    data = sdata.Data(name="data", uuid="38b26864e7794f5182d38459bab8584d", table=df, comment="abc")
    js = data.to_json()
    data2 = sdata.Data.from_json(s=js)
    print(data.name, data2.name)
    assert data.name==data2.name
    assert data.uuid==data2.uuid
    assert data.description==data2.description
    assert data.sha3_256==data2.sha3_256




if __name__ == '__main__':
    test_data()
    test_group()
