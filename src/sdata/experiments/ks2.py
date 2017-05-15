# -*- coding: utf-8 -*-
import sdata

class KS2_Sheet(sdata.Part):

    #["name", "value", "dtype", "unit", "description"]
    ATTR_NAMES = [["rd", None, "float", "deg", "rolling direction"],
                  ["t", None, "float", "mm", "thickness sheet"],
                  ["r", None, "float", "mm", "bending radius sheet"],
                  ["bi", None, "float", "mm", "inner width"],
                  ["hi", None, "float", "mm", "inner height"],
                  ["l", None, "float", "mm", "length"],
                  ]
    def __init__(self, **kwargs):
        """KS2 Testseries"""
        sdata.Part.__init__(self, **kwargs)

        for attr_name, value, dtype, unit, description in self.ATTR_NAMES:

            self.metadata.set_attr(name=attr_name, value=None, dtype=dtype, description=description)


class KS2_Test(sdata.TestSeries):
    """KS2-Test to determine connection properties"""

    #["name", "value", "dtype", "unit", "description"]
    ATTR_NAMES = [["angle", None, "float", "deg", "loading angle"],
                  ]
def __init__(self, parts, **kwargs):
    """KS2 Testseries"""
    sdata.TestSeries.__init__(self, **kwargs)

    # set mandatory attribute
    for attr_name, value, dtype, unit, description in self.ATTR_NAMES:
        self.metadata.set_attr(name=attr_name, value=None, dtype=dtype, description=description)

    [self.group.add_data(part) for part in parts]



