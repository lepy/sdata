import sys
import os

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

import sdata
import pandas as pd
import numpy as np

def test_table():

    df = pd.DataFrame(np.random.random((3,20)))

    table = sdata.Table()
    table.data = df
    print(table.data)
    print(table.metadata)

if __name__ == '__main__':
    test_table()