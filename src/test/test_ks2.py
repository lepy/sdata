import sys
import os

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

import sdata.test
import sdata.experiments.ks2
import pandas as pd
import numpy as np

def test_ks2():
    mat1 = sdata.Material(name="HX340LAD")
    mat1.metadata.set_attr("material_type", "steel")
    print(mat1.metadata)
    invalid_attrs = mat1.verify_attributes()
    print(invalid_attrs)
    assert len(invalid_attrs)==0
    print(mat1.metadata.to_dataframe())

    mat2 = sdata.Material(name="AW6016")
    mat2.metadata.set_attr("material_type", "alu")
    mat2.metadata.set_attr("material_grade", "T4")

    part1 = sdata.experiments.ks2.KS2_Sheet(name="upper sheet")
    part1.metadata.set_attr("material_uuid", mat1.uuid)
    part2 = sdata.experiments.ks2.KS2_Sheet(name="bottom sheet")
    part2.metadata.set_attr("material_uuid", mat1.uuid)
    invalid_attrs = part1.verify_attributes()
    print(invalid_attrs)
    assert len(invalid_attrs)>0
    part1.metadata.set_attr("rd", 0)
    part1.metadata.set_attr("t", 1.1)
    part1.metadata.set_attr("r", 2)
    part1.metadata.set_attr("bi", 34.)
    part1.metadata.set_attr("hi", 29.)
    part1.metadata.set_attr("l", 50.)
    invalid_attrs = part1.verify_attributes()
    print(invalid_attrs)
    assert len(invalid_attrs)==0

    print(part2.metadata.get_attr("t"))
    part2.metadata.set_attr("material_uuid", mat2.uuid)
    part2.metadata.set_attr("rd", 0)
    part2.metadata.get_attr("t").value=2.0
    part2.metadata.set_attr("r", 4)
    part2.metadata.set_attr("bi", 34.)
    part2.metadata.set_attr("hi", 29.)
    part2.metadata.set_attr("l", 50.)

    invalid_attrs = part2.verify_attributes()
    print(invalid_attrs)
    assert len(invalid_attrs)==0



    ks2 = sdata.experiments.ks2.KS2_Test(name="KS2 testseries A1", parts=[part1, part2])
    print(ks2)
    assert ks2.name=="KS2 testseries A1"
    print(ks2.metadata)
    ks2.metadata.set_attr("angle", 30.)
    print(ks2.metadata.get_attr("t3"))

    print(part1.metadata.to_dataframe())


if __name__ == '__main__':
    test_ks2()