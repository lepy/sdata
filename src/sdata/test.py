import sdata

class Test(sdata.Data):
    """Test Object, e.g. a single tension test"""
    def __init__(self, **kwargs):
        """"""
        sdata.Data.__init__(self, **kwargs)

    def __str__(self):
        return "(Test '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__
