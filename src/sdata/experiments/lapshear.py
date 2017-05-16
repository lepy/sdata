# -*- coding: utf-8 -*-
import sdata

class Lapshear_Sheet(sdata.Part):

    #["name", "value", "dtype", "unit", "description", "required"]
    ATTR_NAMES = [["rd", None, "float", "deg", "rolling direction", True],
                  ["t", None, "float", "mm", "thickness sheet", True],
                  ["l", None, "float", "mm", "length", True],
                  ["w", None, "float", "mm", "width", True],
                  ] + sdata.Part.ATTR_NAMES
    def __init__(self, **kwargs):
        """Lapshear Testseries"""
        sdata.Part.__init__(self, **kwargs)
        self.gen_default_attributes()


class Lapshear_TestSeries(sdata.TestSeries):
    """Lapshear-Test to determine connection properties"""

    #["name", "value", "dtype", "unit", "description", "required"]
    ATTR_NAMES = sdata.TestSeries.ATTR_NAMES

    def __init__(self, **kwargs):
        """Lapshear Testseries"""
        sdata.TestSeries.__init__(self, **kwargs)
        self.gen_default_attributes()

class Lapshear_Test(sdata.Test):
    """Lapshear-Test to determine connection properties"""

    #["name", "value", "dtype", "unit", "description", "required"]
    ATTR_NAMES = [] + sdata.Test.ATTR_NAMES

    def __init__(self, **kwargs):
        """Lapshear Testseries"""
        sdata.Test.__init__(self, **kwargs)
        self.gen_default_attributes()


sdata.SDATACLS["Lapshear_Sheet"] = Lapshear_Sheet
sdata.SDATACLS["Lapshear_TestSeries"] = Lapshear_TestSeries
sdata.SDATACLS["Lapshear_Test"] = Lapshear_Test
