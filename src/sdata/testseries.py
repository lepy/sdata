import sdata

class TestSeries(sdata.Group):
    """Test Series Object, e.g. a set of single tension tests"""
    def __init__(self, **kwargs):
        """"""
        sdata.Group.__init__(self, **kwargs)

    def add_test(self, test):
        """add test to test series"""
        sdata.Group.add_data(self, test)

    def dir(self):
        return [x.name for x in self.group.values()]

    def __str__(self):
        return "(TestSeries '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__
