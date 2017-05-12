# -*-coding: utf-8-*-
from __future__ import division

__version__ = '0.5.3'
__revision__ = None
__version_info__ = tuple([ int(num) for num in __version__.split('.')])

'''
Docu not available
'''

import os
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

    name = property(fget=_get_name, fset=_set_name, doc="name of the object")

    def to_folder(self, path):
        """export data to folder"""
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError as exp:
                logging.error(exp)
        metadata_filepath = os.path.join(path, "metadata.csv")
        self.metadata.set_attr(name="class", value=self.__class__.__name__, description="object class", unit="-", dtype="str")
        self.metadata.set_attr(name="uuid", value=self.uuid, description="object uuid", unit="-", dtype="str")
        self.metadata.set_attr(name="name", value=self.name, description="object name", unit="-", dtype="str")
        self.metadata.to_csv(metadata_filepath)

    @classmethod
    def from_folder(cls, path):
        """generate data instance from folder structure"""
        data = cls()
        metadata_filepath = os.path.join(path, "metadata.csv")
        if os.path.exists(metadata_filepath):
            Metadata().from_csv(metadata_filepath)
        else:
            logging.error("no metadata '{}'".format(metadata_filepath))
        return data

    def dir(self):
        """list contents"""
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

    def to_folder(self, path):
        """export data to folder"""
        Data.to_folder(self, path)
        exportpath = os.path.join(path, "{}.csv".format(self.uuid))
        self._table.to_csv(exportpath, index=False)

    def __str__(self):
        return "(table '%s':%s(%d))" % (self.name, self.uuid, len(self._table))

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

    def to_folder(self, path):
        """export data to folder"""
        Data.to_folder(self, path)
        for data in self.group.values():
            exportpath = os.path.join(path, "{}_{}".format(data.__class__.__name__.lower(), data.uuid))
            print("!",data, exportpath)
            data.to_folder(exportpath)

    def __str__(self):
        return "(group '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__

    def tree_folder(self, dir, padding="  ", print_files=True, hidden_files=False):
        print(padding[:-1] + '+-' + os.path.basename(os.path.abspath(dir)) + '/')
        padding = padding + ' '
        files = []
        if print_files:
            files = [x for x in os.listdir(dir) if not x.startswith(".")]
        else:
            files = [x for x in os.listdir(dir) if os.path.isdir(dir + os.sep + x)]
        count = 0
        for file in files:
            count += 1
            print(padding + '|')
            path = dir + os.sep + file
            if os.path.isdir(path):
                if count == len(files):
                    self.tree_folder(path, padding + ' ', print_files)
                else:
                    self.tree_folder(path, padding + '|', print_files)
            else:
                print(padding + '+-' + file)

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
