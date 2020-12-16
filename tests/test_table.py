import sys
import os

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

import sdata
import pandas as pd
import numpy as np


def test_table():

    ts = sdata.Data(name="testseries A1", uuid="a6fc7decdb1441518f762e3b5d798ba8")

    df = pd.DataFrame(np.random.random((10, 3)), columns=["a", "b", "c"])

    table = sdata.Data(name="Table2", uuid="a6fc7decdb1441518f762e3b5d798ba9")
    table.table = df
    table.data = df
    table.metadata.set_attr(name="a", value="Column a", description="bar")
    table.metadata.set_attr(name="b", value="Column a", description="bar", unit="kN")
    table.metadata.set_attr(name="c", value="Column a", description="bar", unit="mm")
    print(table.data)
    print(table.metadata)
    ts.add_data(table)

    print(ts.group)

    ts.to_folder("/tmp/sdata_table")

    table.to_xlsx("/tmp/sdata_table.xlsx")
    print(table.metadata.to_dataframe())

    # table2 = table.from_xlsx("/tmp/sdata_table.xlsx")
    # print("table2", table2)
    # print(table2.metadata.to_dataframe())
    #
    # print(ts.tree_folder("/tmp/sdata_table"))

if __name__ == '__main__':
    test_table()
