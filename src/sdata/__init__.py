# -*-coding: utf-8-*-
from __future__ import division

__version__ = '0.3.0'
__revision__ = None
__version_info__ = tuple([ int(num) for num in __version__.split('.')])

'''
Docu not available
'''

import uuid
from collections import OrderedDict
import logging
import numpy as np
import pandas as pd

class Data(object):
    """run object, e.g. single tension test simulation"""

    def __init__(self, **kwargs):
        self._uuid = None
        self._name = None
        self.uuid = kwargs.get("uuid") or uuid.uuid4()
        self.name = kwargs.get("name") or "N.N."
        self.metadata = kwargs.get("metadata") or Metadata()

    def _get_uuid(self):
        return self._uuid
    def _set_uuid(self, value):
        if isinstance(value, str):
            try:
                self._uuid = uuid.UUID(value).hex
            except ValueError as exp:
                logging.warn("data.uuid: %s" % exp)
        elif isinstance(value, uuid.UUID):
            self._uuid = value.hex
    uuid = property(fget=_get_uuid, fset=_set_uuid)

    def _get_name(self):
        return self._name
    def _set_name(self, value):
        if isinstance(value, str):
            try:
                self._name = value[:256]
            except ValueError as exp:
                logging.warn("data.name: %s" % exp)
        else:
            self._name = str(value)[:256]

    name = property(fget=_get_name, fset=_set_name)

    def dir(self):
        return (self.name)

    def __str__(self):
        return "(data '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__

class Table(Data):
    """table object"""

    def __init__(self, **kwargs):
        Data.__init__(self, **kwargs)
        self._uuid = None
        self._group = OrderedDict()
        self.uuid = kwargs.get("uuid") or uuid.uuid4()
        self.metadata = kwargs.get("metadata") or Metadata()
        self._table = pd.DataFrame()

    def _get_table(self):
        return self._table
    def _set_table(self, df):
        if isinstance(df, pd.DataFrame):
            self._table = df
    data = property(fget=_get_table, fset=_set_table)

    def __str__(self):
        return "(table '%s':%s(%d))" % (self.name, self.uuid, len(self.table))

    __repr__ = __str__

class Group(Data):
    """group object, e.g. single tension test simulation"""

    def __init__(self, **kwargs):
        Data.__init__(self, **kwargs)
        self._uuid = None
        self._group = OrderedDict()
        self.uuid = kwargs.get("uuid") or uuid.uuid4()
        self.metadata = kwargs.get("metadata") or Metadata()

    def get_group(self):
        return self._group
    group = property(get_group)

    def add_data(self, data):
        if isinstance(data, Data):
            self.group[data.uuid] = data
        else:
            logging.warning("ignore data %s (wrong type!)" % data)
    def get_data(self, uuid):
        return self.group.get(uuid)

    def dir(self):
        return [(x.name, x.dir()) for x in self.group.values()]

    def __str__(self):
        return "(group '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__


class Metadata(object):
    """Metadata container class
    
    each Metadata entry has has a 
        * name (32)
        * value
        * unit
        * description (256)
        * type (int, str, float)
        """

    columns = ["name", "value", "unit", "dtype", "description"]

    def __init__(self, df=None):
        """create metadata instance"""
        self._data = pd.DataFrame(columns=self.columns)

    def _get_data(self):
        return self._data[self.columns]
    def _set_data(self, data):
        self._data = data
    data = property(fget=_get_data, fset=_set_data)

    def update_value(self, **kwargs):
        """add/update metadata"""
        d = {name:kwargs.get(name) for name in self.columns}
        dfd = pd.DataFrame.from_dict({d["name"]:d}, orient="index").to_dict(orient='index')
        d0 = self.data.to_dict(orient='index')
        d0.update(dfd)
        self._data = pd.DataFrame.from_dict(d0, orient='index')
        self.fix_cols()

    def _map_dtype(self, x):
        return type(x).__name__

    def _map_description(self, x):
        if isinstance(x, str):
            return x[:256]
        else:
            return ""

    def _map_unit(self, x):
        if isinstance(x, str):
            return x[:256]
        else:
            return "-"

    def fix_cols(self):
        self._data["dtype"] = self._data["value"].apply(self._map_dtype)
        self._data["description"] = self._data["description"].apply(self._map_description)
        self._data["unit"] = self._data["unit"].apply(self._map_unit)

    def from_dict(self, d):
        """add/update metadata from dict"""
        d0 = self.data.to_dict(orient='index')
        d0.update(d)
        self._data = pd.DataFrame.from_dict(d0, orient='index')
        self.fix_cols()

    def __str__(self):
        return "(Metadata\n%s)" % (self.data)

    def __repr__(self):
        return "(Metadata %d)" % (len(self.data))

    def to_csv(self, filepath):
        """serialize metadata to csv"""
        with open(filepath, "w") as fh:
            self.data.to_csv(fh, index=False, sep=";")
        
    def from_csv(self, filepath):
        """serialize metadata to csv"""
        self.data = pd.read_csv(filepath, sep=";")
        self._data.set_index(self._data.name, inplace=True)
        def fix_dtype(x):
            if x["dtype"]=="int":
                x["value"] = int(x["value"])
            elif x["dtype"]=="float":
                x["value"] = float(x["value"])
            return x
        self._data = self._data.apply(fix_dtype, axis=1)
        self.fix_cols()


from sdata.test import Test
from sdata.testseries import TestSeries
from sdata.testprogram import TestProgram