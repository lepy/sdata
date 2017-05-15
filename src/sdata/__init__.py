# -*-coding: utf-8-*-
from __future__ import division

__version__ = '0.5.4'
__revision__ = None
__version_info__ = tuple([ int(num) for num in __version__.split('.')])

'''
basic data types 
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
    ATTR_NAMES = []

    def __init__(self, **kwargs):
        self._uuid = None
        self._name = None
        self.uuid = kwargs.get("uuid") or uuid.uuid4()
        self.name = kwargs.get("name") or "N.N."
        self.metadata = kwargs.get("metadata") or Metadata()
        self.gen_default_attributes()

    def gen_default_attributes(self):
        for attr_name, value, dtype, unit, description, required in self.ATTR_NAMES:
            self.metadata.set_attr(name=attr_name, value=value, dtype=dtype, description=description)

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

    @staticmethod
    def _load_metadata(path):
        metadata_filepath = os.path.join(path, "metadata.csv")
        if os.path.exists(metadata_filepath):
            metadata = Metadata().from_csv(metadata_filepath)
        else:
            metadata = Metadata()
        return metadata

    @staticmethod
    def _get_class_from_metadata(metadata):
        classattr = metadata.get_attr("class")
        if classattr is not None:
            sdataclassname = classattr.value
            sdatacls = SDATACLS.get(sdataclassname)
            if sdataclassname not in SDATACLS:
                logging.warn("unsupported cls '{}'".format(sdataclassname))
                sdatacls = Data
        else:
            logging.warn("cls not defined '{}'".format(metadata))
            sdatacls = None
        return sdatacls

    @classmethod
    def from_folder(cls, path):
        """generate data instance from folder structure"""
        metadata = cls._load_metadata(path)
        sdataclass = cls._get_class_from_metadata(metadata)
        if sdataclass:
            data = sdataclass()
            data.metadata = metadata
            print(sdataclass)
            print("Metadata", metadata)
            # assert sdataclass=="TestProgram", "unsupported data type {}".format(sdataclass)
            data.uuid = data.metadata.get_attr("uuid").value
            data.name = data.metadata.get_attr("name").value
        else:
            logging.error("no metadata '{}'".format(path))

        return data

    def verify_attributes(self):
        """check mandatory attributes"""
        invalid_attrs = []
        # attr_defs = ["name", "value", "dtype", "unit", "description", "required"]
        for attr_defs in self.ATTR_NAMES:
            required = attr_defs[5]
            if required is False:
                continue
            attr = self.metadata.get_attr(attr_defs[0])
            if attr is None:
                invalid_attrs.append(attr_defs[0])
            elif attr.value is None:
                invalid_attrs.append(attr.name)
        return invalid_attrs

    def dir(self):
        """list contents"""
        return (self.name)

    def __str__(self):
        return "(Data '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__

class Table(Data):
    """table object"""
    ATTR_NAMES = []

    def __init__(self, **kwargs):
        Data.__init__(self, **kwargs)
        self._uuid = None
        self._group = OrderedDict()
        self.uuid = kwargs.get("uuid") or uuid.uuid4()
        self.metadata = kwargs.get("metadata") or Metadata()
        self._table = pd.DataFrame()
        self.gen_default_attributes()

    @classmethod
    def from_folder(cls, path):
        print("import_table", path)
        # data = Data.from_folder(path)
        files = [x for x in os.listdir(path) if not os.path.isdir(os.path.join(path, x)) and not x.startswith("metadata")]
        print("tablefiles", files, len(files))
        assert len(files)==1
        data = cls()
        data.metadata = data._load_metadata(path)
        data.uuid = data.metadata.get_attr("uuid").value
        data.name = data.metadata.get_attr("name").value
        importpath = os.path.join(path, files[0])
        data._table = pd.read_csv(importpath)
        return data

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
        return "(Table '%s':%s(%d))" % (self.name, self.uuid, len(self._table))

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
        self.gen_default_attributes()


    @classmethod
    def from_folder(cls, path):
        """generate data instance from folder structure"""
        metadata = cls._load_metadata(path)
        sdataclass = cls._get_class_from_metadata(metadata)
        if sdataclass:
            data = sdataclass()
            data.metadata = metadata
            print(sdataclass)
            print("Metadata", metadata)
            # assert sdataclass=="TestProgram", "unsupported data type {}".format(sdataclass)
            data.uuid = data.metadata.get_attr("uuid").value
            data.name = data.metadata.get_attr("name").value
        else:
            logging.error("no metadata '{}'".format(path))

        print("import_group", path)
        folders = [x for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))]
        if hasattr(data, "group"):
            # print("!!!", data, folders, os.listdir(path))
            for folder in folders:
                # print("!", folder)
                subfolder = os.path.join(path, folder)
                data_ = data.from_folder(subfolder)
                print("!!!, data_", data_)
                subdata = data_.from_folder(subfolder)
                # print("subdata", subdata)
                data.add_data(subdata)
        return data

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

    def to_folder(self, path):
        """export data to folder"""
        Data.to_folder(self, path)
        for data in self.group.values():
            exportpath = os.path.join(path, "{}_{}".format(data.__class__.__name__.lower(), data.uuid))
            # print("!",data, exportpath)
            data.to_folder(exportpath)

    def __str__(self):
        return "(group '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__

    def tree_folder(self, dir, padding="  ", print_files=True, hidden_files=False, last=True):
        """print tree folder structure"""
        if last is False:
            print(padding[:-1] + '├─' + os.path.basename(os.path.abspath(dir)))
        else:
            print(padding[:-1] + '└─' + os.path.basename(os.path.abspath(dir)))
        padding = padding + ' '
        files = []
        if print_files:
            files = [x for x in os.listdir(dir) if not x.startswith(".")]
        else:
            files = [x for x in os.listdir(dir) if os.path.isdir(dir + os.sep + x)]

        # metadata first
        metafiles = [f for f in files if f.startswith("metadata")]
        files = [x for x in files if x not in metafiles ]
        files = metafiles + files

        for count, file in enumerate(files):
            print(padding + '|')
            path = dir + os.sep + file
            if os.path.isdir(path):
                if count == (len(files)-1):
                    self.tree_folder(path, padding + ' ', print_files, last=True)
                else:
                    self.tree_folder(path, padding + '|', print_files, last=False)
            else:
                if count==(len(files)-1):
                    print(padding + '└─' + file)
                else:
                    print(padding + '├─' + file)


class Part(Group):
    """part object, e.g. test specimen (sheet) or a part of a specimen"""

    #["name", "value", "dtype", "unit", "description"]
    ATTR_NAMES = [["material_uuid", None, "uuid", "-", "Material UUID", True],
                  ]

    def __init__(self, **kwargs):
        Group.__init__(self, **kwargs)
        self.gen_default_attributes()


    def __str__(self):
        return "(part '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__

class Material(Group):
    """material object, e.g. a steel material"""

    #["name", "value", "dtype", "unit", "description"]
    ATTR_NAMES = [["material_type", None, "str", "-", "Material type, e.g. alu|steel|plastic|wood|glas|foam|soil|...", True],
                  ["material_grade", "-", "str", "-", "Material grade, e.g. T4", False],
                  ]

    def __init__(self, **kwargs):
        Group.__init__(self, **kwargs)
        self.gen_default_attributes()

    def __str__(self):
        return "(mat '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__


from sdata.test import Test
from sdata.testseries import TestSeries
from sdata.testprogram import TestProgram

SDATACLS = {"Data":Data,
            "Group":Group,
            "Table":Table,
            "Test":Test,
            "TestSeries":TestSeries,
            "TestProgram":TestProgram,
            "Part":Part,
            "Material":Material,
            }

# <class 'sdata.Data'>
# <class 'sdata.Group'>
# <class 'sdata.Material'>
# <class 'sdata.Part'>
# <class 'sdata.Table'>
# <class 'sdata.test.Test'>
# <class 'sdata.testprogram.TestProgram'>
# <class 'sdata.testseries.TestSeries'>

import sdata.timestamp as timestamp
__all__ = ["Data", "Table", "Group", "Test", "TestProgram", "TestSeries"]

import sys, inspect
def print_classes():
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj):
            print(obj)