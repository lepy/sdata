import os
import sdata

class TestProgram(sdata.Group):
    """Test Program Object"""
    def __init__(self, **kwargs):
        """"""
        sdata.Group.__init__(self, **kwargs)

    def add_series(self, test):
        """add test to test series"""
        self.add_data(test)

    # def to_folder(self, path):
    #     """export data to folder"""
    #     # TestProgram.to_folder(self, path)
    #     for testseries in self.group.values():
    #         exportpath = os.path.join(path, testseries.uuid)
    #         testseries.to_folder(exportpath)

    def __str__(self):
        return "(test '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__
