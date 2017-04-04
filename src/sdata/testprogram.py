import sdata

class TestProgram(sdata.Group):
    """Test Program Object"""
    def __init__(self, **kwargs):
        """"""
        sdata.Group.__init__(self, **kwargs)

    def add_series(self, test):
        """add test to test series"""
        self.add_data(test)

    def __str__(self):
        return "(test '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__
