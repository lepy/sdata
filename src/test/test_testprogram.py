import sys
import os

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

import sdata.test
import pandas as pd
import numpy as np

def gen_dummy_testprogram():
    ts1 = sdata.testseries.TestSeries(name="testseries A1")
    t1 = sdata.test.Test(name="test 001")
    ts1.add_test(t1)

    df = pd.DataFrame(np.random.random((10,3)), columns=["a", "b", "c"])
    table = sdata.Table()
    table.data = df
    table.metadata.set_attr(name="a", value="Column a", description="bar")
    table.metadata.set_attr(name="b", value="Column a", description="bar", unit="kN")
    table.metadata.set_attr(name="c", value="Column a", description="bar", unit="mm")
    t1.add_result(table)
    print(t1.get_results())

    t2 = sdata.test.Test(name="test 002")
    ts1.add_test(t2)

    t3 = sdata.test.Test(name="test 003")
    ts1.add_test(t3)

    ts2 = sdata.testseries.TestSeries(name="testseries A2")

    t1b = sdata.test.Test(name="test 001b")
    t2b = sdata.test.Test(name="test 002b")
    ts2.add_test(t1b)
    ts2.add_test(t2b)
    tp = sdata.testprogram.TestProgram(name="testprogram FOO")
    tp.add_series(ts1)
    tp.add_series(ts2)

    return tp

def test_test():
    t = sdata.test.Test(name="test 001")
    print(t)
    assert t.name=="test 001"
    t.to_folder("/tmp/mytest")


def test_testseries():
    ts = sdata.testseries.TestSeries(name="testseries A1")
    print(ts)
    assert ts.name=="testseries A1"

def test_testprogram():
    # t1 = sdata.test.Test(name="test 001")
    # t2 = sdata.test.Test(name="test 002")
    # t3 = sdata.test.Test(name="test 003")
    # ts1 = sdata.testseries.TestSeries(name="testseries A1")
    # ts1.add_test(t1)
    # ts1.add_test(t2)
    # ts1.add_test(t3)
    #
    # t1b = sdata.test.Test(name="test 001b")
    # t2b = sdata.test.Test(name="test 002b")
    # ts2 = sdata.testseries.TestSeries(name="testseries A2")
    # ts2.add_test(t1b)
    # ts2.add_test(t2b)
    # tp = sdata.testprogram.TestProgram(name="testprogram FOO")
    # tp.add_series(ts1)
    # tp.add_series(ts2)
    tp = gen_dummy_testprogram()
    print(tp)
    assert tp.name=="testprogram FOO"
    print(tp.dir())
    tp.to_folder("/tmp/mytestprogram")
if __name__ == '__main__':
    test_test()
    test_testseries()
    test_testprogram()
