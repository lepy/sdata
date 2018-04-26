import sys
import os

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

import sdata
import pandas as pd
import numpy as np

def test_table():

    df = pd.DataFrame(np.random.random((10,3)), columns=["a", "b", "c"])

    table = sdata.Data()
    table.data = df
    table.metadata.set_attr(name="a", value="Column a", description="bar")
    table.metadata.set_attr(name="b", value="Column a", description="bar", unit="kN")
    table.metadata.set_attr(name="c", value="Column a", description="bar", unit="mm")
    print(table.data)
    print(table.metadata)

if __name__ == '__main__':
    test_table()
