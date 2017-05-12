import sdata

class Test(sdata.Data):
    """Test Object, e.g. a single tension test"""
    def __init__(self, **kwargs):
        """"""
        sdata.Data.__init__(self, **kwargs)
        self._results = {}

    def _get_results(self):
        return self._results

    def get_results(self, uuid):
        return self._results.get(uuid)

    def set_result(self, data):
        self._results[data.uuid] = data

    def __str__(self):
        return "(Test '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__
