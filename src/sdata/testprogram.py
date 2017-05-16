import os
import sdata

class TestProgram(sdata.Group):
    """Test Program Object"""
    def __init__(self, **kwargs):
        """"""
        sdata.Group.__init__(self, **kwargs)

    def add_series(self, test):
        """add data to testprogram"""
        sdata.Group.add_data(self, test)

    def __str__(self):
        return "(TestProgram '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__

class Parts(sdata.Group):
    """Test Program Object"""
    def __init__(self, **kwargs):
        """"""
        sdata.Group.__init__(self, **kwargs)

    def __str__(self):
        return "(Parts '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__

class Part(sdata.Group):
    """part object, e.g. test specimen (sheet) or a part of a specimen"""

    #["name", "value", "dtype", "unit", "description"]
    ATTR_NAMES = [["material_uuid", None, "uuid", "-", "Material UUID", True],
                  ]

    def __init__(self, **kwargs):
        sdata.Group.__init__(self, **kwargs)
        self.gen_default_attributes()

    def __str__(self):
        return "(Part '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__

class Materials(sdata.Group):
    """Test Program Object"""
    def __init__(self, **kwargs):
        """"""
        sdata.Group.__init__(self, **kwargs)

    def __str__(self):
        return "(Materials '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__

class Material(sdata.Group):
    """material object, e.g. a steel material"""

    #["name", "value", "dtype", "unit", "description"]
    ATTR_NAMES = [["material_type", None, "str", "-", "Material type, e.g. alu|steel|plastic|wood|glas|foam|soil|...", True],
                  ["material_grade", "-", "str", "-", "Material grade, e.g. T4", False],
                  ]

    def __init__(self, **kwargs):
        sdata.Group.__init__(self, **kwargs)
        self.gen_default_attributes()

    def __str__(self):
        return "(Material '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__

