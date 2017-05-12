# -*-coding: utf-8-*-
from __future__ import division

__version__ = '0.5.1'
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



from sdata.metadata import Metadata, Attribute




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
                logging.warning("data.uuid: %s" % exp)
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
                logging.warning("data.name: %s" % exp)
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

    #["name", "value", "dtype", "unit", "description"]
    ATTR_NAMES = []

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

    def verify_attributes(self):
        """check mandatory attributes"""
        invalid_attrs = []
        for attr_defs in self.ATTR_NAMES:
            attr = self.metadata.get_attr(attr_defs[0])
            if attr.value is None:
                invalid_attrs.append(attr.name)
        return invalid_attrs


    def __str__(self):
        return "(group '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__

class Part(Group):
    """part object, e.g. test specimen (sheet) or a part of a specimen"""

    #["name", "value", "dtype", "unit", "description"]
    ATTR_NAMES = [["Material", None, "str", "-", "Material name"],
                  ]

    def __init__(self, **kwargs):
        Group.__init__(self, **kwargs)
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
        return "(part '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__


from sdata.test import Test
from sdata.testseries import TestSeries
from sdata.testprogram import TestProgram

import sdata.timestamp as timestamp
__all__ = ["Data", "Table", "Group", "Test", "TestProgram", "TestSeries"]
