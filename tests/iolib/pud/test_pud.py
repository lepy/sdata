# -*- coding: utf-8 -*-

import sys
import os
import sdata.iolib.pud

modulepath = os.path.dirname(__file__)

import pytest


def test_pud():
    filepath = os.path.join(modulepath, "ut_flat.txt")
    pud = sdata.iolib.pud.Pud.from_file(filepath)
    print(pud)
    print(pud.metadata)
    # print(pud.data.head())


def test_pud_file_not_exists():
    with pytest.raises(Exception):
        sdata.iolib.pud.Pud.from_file("/does/not/exist.txt")

if __name__ == '__main__':
    test_pud()

