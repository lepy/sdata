# -*- coding: utf-8 -*-

from sdata import Blob
import pandas as pd
import numpy as np

def test_blob():

    b = Blob(name="blob")
    print(b)
    assert b.name == "blob"


# def test_table():
#
#     sdf = DataFrame(name="table#s!")
#     sdf.blob = pd.DataFrame(np.random.random((10, 3)), columns=["a", "b", "c"])
#     print(sdf)
#     print(sdf.filename)
#     assert sdf.name == "table#s!"
#     assert sdf.filename == "table_s_"
#     print(sdf.columns.to_dataframe())
#
#     # sdf.to_xlsx(path="/tmp")
#
