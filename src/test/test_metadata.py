import sys
import os

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

import sdata

def test_metadata():
    metadata = sdata.Metadata()
    print(metadata.data)

if __name__ == '__main__':
    test_metadata()