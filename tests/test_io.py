# -*-coding: utf-8-*-
import logging
logger = logging.getLogger("sdata")

import sys
import os
import pandas as pd

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

import sdata
import uuid

def test_data_to_html():
    df = pd.DataFrame({'a': ['x', 'y', '', 'z'], 'b': [1, 2, 2, 3.2]})
    data = sdata.Data(name="data", uuid="38b26864e7794f5182d38459bab8584d", table=df, description="abc")
    data.to_html("/tmp/data.html")

    # js = data.to_json()
    # data2 = sdata.Data.from_json(s=js)
    # print(data.name, data2.name)
    # assert data.name == data2.name
    # assert data.uuid == data2.uuid
    # assert data.description == data2.description
    # assert data.sha3_256 == data2.sha3_256

def test_hdf5():
    df = pd.DataFrame({"a": [1.1, 2.1, 3.5],
                       "b": [2.4, 1.2, 2.2]})
    d = sdata.Data(name="basic example", uuid="38b26864e7794f5182d38459bab85842", table=df, description="hallo")
    d.metadata.add("Temperatur", value=25.4, dtype="float", unit="degC", description="Temperatur")
    export_path = "/tmp/{}.h5".format(d.osname)
    d.to_hdf5(export_path)
    d2 = sdata.Data.from_hdf5(export_path)
    print(d2.describe())
    assert d2.sha3_256 == d.sha3_256