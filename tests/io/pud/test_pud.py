# -*- coding: utf-8 -*-

import sys
import os
import sdata.io.pud

modulepath = os.path.dirname(__file__)

def test_pud():
    filepath = os.path.join(modulepath, "ut_flat.txt")
    pud = sdata.io.pud.Pud.from_file(filepath)
    print(pud)
    print(pud.metadata)
    # print(pud.data.head())

if __name__ == '__main__':
    test_pud()

