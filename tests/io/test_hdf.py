import sys
import os
import pandas as pd

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "..", "src"))

import sdata
import uuid
from sdata.io.hdf import FlatHDFDataStore

def test_flathdfstore():
    store = FlatHDFDataStore("/tmp/flatstore1.h5", mode="w")
    print(store)
    assert len(store.keys())==0
    data = sdata.Data(name="otto",
                      uuid=sdata.uuid_from_str("otto"),
                      table=pd.DataFrame({"a": [1, 2, 3]}),
                      description="Hallo\nSpencer")
    store.put(data)
    print(store.keys())

    datac = data.copy()
    datac.name = "otto2"
    datac.uuid = 'b8315be85d9945579cf8dc6a80a62524'
    datac.df["b"] = datac.df["a"] ** 2
    datac.df
    datac.metadata.add("force", 1.23, dtype="float", description="a force", label="F")
    datac.metadata.add("runid", 123, dtype="int", description="a int", label="r")
    print(datac)
    store.put(datac)
    store.keys()

    ldata = store.get_data_by_uuid(data.uuid)
    assert data.sha3_256 == ldata.sha3_256

    ldatac = store.get_data_by_uuid('b8315be85d9945579cf8dc6a80a62524')
    print(datac)
    ldatac.metadata.df
    print([ldatac.description])
    print(ldatac.describe())

    assert datac.sha3_256 == ldatac.sha3_256

    store.close()

def test_flatstoreexample():
    store = FlatHDFDataStore(filepath="/tmp/mystoreexample.h5")

    data = sdata.Data(name="otto",
                      uuid="d4e97cedca6238bea16732ce88c1922f",
                      table=pd.DataFrame({"a": [1, 2, 3]}),
                      description="Hallo\nSpencer")
    store.put(data)

    loaded_data = store.get_data_by_uuid("d4e97cedca6238bea16732ce88c1922f")
    assert data.sha3_256 == loaded_data.sha3_256
    store.close()