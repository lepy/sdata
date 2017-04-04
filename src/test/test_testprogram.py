import sys
import os

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

import sdata.test
import pandas as pd
import numpy as np


def test_test():
    t = sdata.test.Test(name="test 001")
    print(t)
    assert t.name=="test 001"

def test_testseries():
    ts = sdata.testseries.TestSeries(name="testseries A1")
    print(ts)
    assert ts.name=="testseries A1"

def test_testprogram():
    t1 = sdata.test.Test(name="test 001")
    t2 = sdata.test.Test(name="test 002")
    t3 = sdata.test.Test(name="test 003")
    ts1 = sdata.testseries.TestSeries(name="testseries A1")
    ts1.add_test(t1)
    ts1.add_test(t2)
    ts1.add_test(t3)

    t1b = sdata.test.Test(name="test 001b")
    t2b = sdata.test.Test(name="test 002b")
    ts2 = sdata.testseries.TestSeries(name="testseries A2")
    ts2.add_test(t1b)
    ts2.add_test(t2b)
    tp = sdata.testprogram.TestProgram(name="testprogram FOO")
    tp.add_series(ts1)
    tp.add_series(ts2)
    print(tp)
    assert tp.name=="testprogram FOO"
    print(tp.dir())

if __name__ == '__main__':
    test_test()
    test_testseries()
    test_testprogram()
