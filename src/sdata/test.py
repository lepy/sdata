import sdata

class Test(sdata.Group):
    """Test Object, e.g. a single tension test"""
    def __init__(self, **kwargs):
        """"""
        sdata.Group.__init__(self, **kwargs)

    def get_results(self):
        """get dict uf results"""
        return self.group

    def get_result(self, uuid):
        """get result by uuid"""
        return self.group.get(uuid)

    def add_result(self, data):
        """add result"""
        sdata.Group.add_data(self, data)

    def __str__(self):
        return "(Test '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__
