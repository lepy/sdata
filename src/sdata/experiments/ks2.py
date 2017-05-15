# -*- coding: utf-8 -*-
import sdata

class KS2_Sheet(sdata.Part):

    #["name", "value", "dtype", "unit", "description", "required"]
    ATTR_NAMES = [["rd", None, "float", "deg", "rolling direction", True],
                  ["t", None, "float", "mm", "thickness sheet", True],
                  ["r", None, "float", "mm", "bending radius sheet", True],
                  ["bi", None, "float", "mm", "inner width", True],
                  ["hi", None, "float", "mm", "inner height", True],
                  ["l", None, "float", "mm", "length", True],
                  ] + sdata.Part.ATTR_NAMES
    def __init__(self, **kwargs):
        """KS2 Testseries"""
        sdata.Part.__init__(self, **kwargs)
        self.gen_default_attributes()


class KS2_Test(sdata.TestSeries):
    """KS2-Test to determine connection properties"""

    #["name", "value", "dtype", "unit", "description", "required"]
    ATTR_NAMES = [["angle", None, "float", "deg", "loading angle", True],
                  ] + sdata.TestSeries.ATTR_NAMES

    def __init__(self, **kwargs):
        """KS2 Testseries"""
        sdata.TestSeries.__init__(self, **kwargs)
        self.gen_default_attributes()

sdata.SDATACLS["KS2_Sheet"] = KS2_Sheet
sdata.SDATACLS["KS2_Test"] = KS2_Test
