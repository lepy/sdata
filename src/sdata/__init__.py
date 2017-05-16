# -*-coding: utf-8-*-
from __future__ import division

__version__ = '0.5.8'
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
import shutil
from sdata.metadata import Metadata, Attribute

class Data(object):
    """run object, e.g. single tension test simulation"""
    ATTR_NAMES = []

    def __init__(self, **kwargs):
        self._uuid = None
        self._name = None
        self._prefix = None
        self.uuid = kwargs.get("uuid") or uuid.uuid4()
        self.name = kwargs.get("name") or "N.N."
        self.prefix = kwargs.get("prefix") or ""
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
    uuid = property(fget=_get_uuid, fset=_set_uuid, doc="uuid of the object")

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

    def _get_prefix(self):
        return self._prefix
    def _set_prefix(self, value):
        if isinstance(value, str):
            try:
                self._prefix = value[:256]
            except ValueError as exp:
                logging.warning("data.prefix: %s" % exp)
        else:
            self._prefix = str(value)[:256]
    prefix = property(fget=_get_prefix, fset=_set_prefix, doc="prefix of the object name")

    def to_folder(self, path):
        """export data to folder"""
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError as exp:
                logging.error(exp)
        else:
            self.clear_folder(path)
        metadata_filepath = os.path.join(path, "metadata.csv")
        self.metadata.set_attr(name="class", value=self.__class__.__name__, description="object class", unit="-", dtype="str")
        self.metadata.set_attr(name="uuid", value=self.uuid, description="object uuid", unit="-", dtype="str")
        self.metadata.set_attr(name="name", value=self.name, description="object name", unit="-", dtype="str")
        self.metadata.to_csv(metadata_filepath)

    @staticmethod
    def clear_folder(path):
        """delete subfolder in export path"""
        def is_valid(path):
            prefix = path.split("-")[0]
            if prefix in [x.lower() for x in SDATACLS.keys()]:
                return True
            else:
                return False

        subfolders = [x for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))]
        valid_subfolders = [x for x in subfolders if is_valid(x)]
        for subfolder in valid_subfolders:
            try:
                subfolder = os.path.join(path, subfolder)
                logging.debug("clear_folder: rm {}".format(subfolder))
                shutil.rmtree(subfolder)
            except OSError as exp:
                raise

    @staticmethod
    def _load_metadata(path):
        """load metadata from csv"""
        metadata_filepath = os.path.join(path, "metadata.csv")
        if os.path.exists(metadata_filepath):
            metadata = Metadata().from_csv(metadata_filepath)
        else:
            metadata = Metadata()
        return metadata

    @staticmethod
    def _get_class_from_metadata(metadata):
        """get class object from metadata"""
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
            data.uuid = data.metadata.get_attr("uuid").value
            data.name = data.metadata.get_attr("name").value
        else:
            logging.error("no metadata '{}'".format(path))
        return data

    @property
    def osname(self):
        """:return os compatible name"""
        return self.name.replace(" ","_").lower()

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
        # data = Data.from_folder(path)
        files = [x for x in os.listdir(path) if not os.path.isdir(os.path.join(path, x)) and not x.startswith("metadata")]
        assert len(files)==1, "to many files for Table"
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
        exportpath = os.path.join(path, "{}.csv".format(self.osname))
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
        self._group = OrderedDict()
        self.gen_default_attributes()


    @classmethod
    def from_folder(cls, path):
        """generate data instance from folder structure"""
        if not os.path.exists(path):
            return cls()
        metadata = cls._load_metadata(path)
        sdataclass = cls._get_class_from_metadata(metadata)
        if sdataclass:
            data = sdataclass()
            data.metadata = metadata
            data.uuid = data.metadata.get_attr("uuid").value
            data.name = data.metadata.get_attr("name").value
        else:
            logging.error("no metadata '{}'".format(path))

        folders = [x for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))]
        if hasattr(data, "group"):
            for folder in folders:
                subfolder = os.path.join(path, folder)
                data_ = data.from_folder(subfolder)
                subdata = data_.from_folder(subfolder)
                data.add_data(subdata)
        return data

    def get_group(self):
        return self._group
    group = property(get_group, doc="get group")

    def clear_group(self):
        """clear group dict"""
        self._group = OrderedDict()

    def add_data(self, data):
        """add data, if data.name is unique"""
        if isinstance(data, Data):
            names = [dat.name.lower() for uid, dat in self.group.items()]
            if data.name.lower() in names:
                logging.error("{}: name '{}' aready exists".format(data.__class__.__name__, data.name))
                return
            self.group[data.uuid] = data
        else:
            logging.warning("ignore data %s (wrong type!)" % data)

    def get_data_by_uuid(self, uid):
        """get data by uuid"""
        return self.group.get(uid)

    def get_data_by_name(self, name):
        """:return obj by name"""
        d = dict([(obj.name, uid) for uid, obj in self.group.items()])
        uid = d.get(name)
        return self.get_data_by_uuid(uid)

    def dir(self):
        return [(x.name, x.dir()) for x in self.group.values()]

    def to_folder(self, path):
        """export data to folder"""
        Data.to_folder(self, path)
        for data in self.group.values():
            exportpath = os.path.join(path, "{}-{}".format(data.__class__.__name__.lower(), data.osname))
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
            # print(padding + '|')
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


from sdata.test import Test
from sdata.testseries import TestSeries
from sdata.testprogram import TestProgram, Part, Parts, Material, Materials

SDATACLS = {"Data":Data,
            "Group":Group,
            "Table":Table,
            "Test":Test,
            "TestSeries":TestSeries,
            "TestProgram":TestProgram,
            "Part":Part,
            "Material":Material,
            "Parts":Parts,
            "Materials":Materials,
            }

import sdata.timestamp as timestamp
__all__ = ["Data", "Table", "Group", "Test", "TestProgram", "TestSeries", "Part", "Parts", "Material", "Materials"]

import sys, inspect
def print_classes():
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj):
            print(obj)