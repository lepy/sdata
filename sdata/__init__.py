# -*-coding: utf-8-*-
from __future__ import division

__version__ = '0.6.0'
__revision__ = None
__version_info__ = tuple([int(num) for num in __version__.split('.')])

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
import sdata.timestamp as timestamp
import sys, inspect


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
        self._gen_default_attributes(kwargs.get("default_attributes") or self.ATTR_NAMES)
        self._group = OrderedDict()
        self._table = None#pd.DataFrame()

    def _gen_default_attributes(self, default_attributes):
        """create default Attributes in data.metadata"""
        for attr_name, value, dtype, unit, description, required in default_attributes:
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

    @property
    def filename(self):

        validchars = "-_.() "
        out = ""

        name = "{}".format(self.name)

        for c in name:
            if str.isalpha(c) or str.isdigit(c) or (c in validchars):
                out += c
            else:
                out += "_"
        return out

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

    def _get_table(self):
        return self._table

    def _set_table(self, df):
        if isinstance(df, pd.DataFrame):
            self._table = df

    table = property(fget=_get_table, fset=_set_table, doc="table object(pandas.DataFrame)")

    def to_folder(self, path, dtype="xlsx"):
        """export data to folder"""
        if dtype not in ["csv", "xlsx"]:
            dtype = "xlsx"
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError as exp:
                logging.error(exp)
        else:
            self.clear_folder(path)

        self.metadata.set_attr(name="class", value=self.__class__.__name__, description="object class", unit="-",
                               dtype="str")
        self.metadata.set_attr(name="uuid", value=self.uuid, description="object uuid", unit="-", dtype="str")
        self.metadata.set_attr(name="name", value=self.name, description="object name", unit="-", dtype="str")

        if dtype == "csv":
            print("Export csv")
            metadata_filepath = os.path.join(path, "metadata.csv")
            self.metadata.to_csv(metadata_filepath)

            # table export
            if isinstance(self._table, pd.DataFrame) and len(self._table) > 0:
                exportpath = os.path.join(path, "{}.csv".format(self.osname))
                self._table.to_csv(exportpath, index=False)
        if dtype == "xlsx":
            if not isinstance(self._table, pd.DataFrame):
                self.table = pd.DataFrame()
            exportpath = os.path.join(path, "{}.xlsx".format(self.osname))
            self.to_xlsx(exportpath)
        # group export
        for data in self.group.values():
            exportpath = os.path.join(path, "{}-{}".format(data.__class__.__name__.lower(), data.osname))
            data.to_folder(exportpath, dtype=dtype)

    @classmethod
    def from_folder(cls, path):
        """:returns: sdata object instance"""
        # data = Data.from_folder(path)

        data = cls()
        if not os.path.exists(path):
            logging.error("from_folder error: path '{}' not exists.".format(path))
            return data

        data.metadata = data._load_metadata(path)
        data.uuid = data.metadata.get_attr("uuid").value
        data.name = data.metadata.get_attr("name").value

        # table import
        files = [x for x in os.listdir(path) if
                 not os.path.isdir(os.path.join(path, x)) and not x.startswith("metadata")]
        if len(files) == 1:
            assert len(files) == 1, "invalid number of files for Table '{}'".format(files)
            importpath = os.path.join(path, files[0])
            print("read table {}".format(importpath))
            # data._table = pd.read_csv(importpath)

        if not os.path.exists(path):
            return cls()
        metadata = cls._load_metadata(path)
        data = cls()
        data.metadata = metadata
        data.uuid = data.metadata.get_attr("uuid").value
        data.name = data.metadata.get_attr("name").value

        folders = [x for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))]
        for folder in folders:
            subfolder = os.path.join(path, folder)
            data_ = data.from_folder(subfolder)
            subdata = data_.from_folder(subfolder)
            data.add_data(subdata)
        return data

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
        """load metadata from csv
        
        :returns: Metadata instance"""
        metadata_filepath = os.path.join(path, "metadata.csv")
        if os.path.exists(metadata_filepath):
            metadata = Metadata().from_csv(metadata_filepath)
        else:
            metadata = Metadata()
        return metadata

    @staticmethod
    def _get_class_from_metadata(metadata):
        """get class object from metadata
        
        :returns: relevant sdata class object"""
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

    @property
    def osname(self):
        """:returns: os compatible name (ascii?)"""
        return self.name.replace(" ", "_").lower()

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

    def __str__(self):
        return "(Data '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__

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

    def tree_folder(self, dir, padding="  ", print_files=True, hidden_files=False, last=True):
        """print tree folder structure"""
        if last is False:
            print(padding[:-1] + '├─' + os.path.basename(os.path.abspath(dir)))
        else:
            print(padding[:-1] + '└─' + os.path.basename(os.path.abspath(dir)))
        padding = padding + ' '
        files = []
        if print_files:
            files = [x for x in sorted(os.listdir(dir)) if not x.startswith(".")]
        else:
            files = [x for x in sorted(os.listdir(dir)) if os.path.isdir(dir + os.sep + x)]

        # metadata first
        metafiles = [f for f in files if f.startswith("metadata")]
        files = [x for x in files if x not in metafiles]
        files = metafiles + sorted(files)

        for count, file in enumerate(sorted(files)):
            # print(padding + '|')
            path = dir + os.sep + file
            if os.path.isdir(path):
                if count == (len(files) - 1):
                    self.tree_folder(path, padding + ' ', print_files, last=True)
                else:
                    self.tree_folder(path, padding + '|', print_files, last=False)
            else:
                if count == (len(files) - 1):
                    print(padding + '└─' + file)
                else:
                    print(padding + '├─' + file)

    def dir(self):
        return [(x.name, x.dir()) for x in self.group.values()]

    def to_xlsx(self, filepath):
        """export atrributes and data to excel

        :param filepath:
        :return:
        """

        def adjust_col_width(sheetname, df, writer, width=40):
            worksheet = writer.sheets[sheetname]  # pull worksheet object
            worksheet.set_column(0, 0, width)
            for idx, col in enumerate(df):  # loop through all columns
                # series = df[col]
                # max_len = max((
                #     series.astype(str, raise_on_error=False).map(len).max(),  # len of largest item
                #     len(str(series.name))  # len of column name/header
                #     )) + 1  # adding a little extra space
                worksheet.set_column(idx+1, idx+1, width)

        with pd.ExcelWriter(filepath) as writer:

            # metadata
            # dfm = pd.DataFrame.from_dict(self.metadata, orient="index", columns=["value"])
            dfm = self.metadata.to_dataframe()

            dfm = dfm.sort_index()
            dfm.index.name = "key"
            dfm.to_excel(writer, sheet_name='metadata')
            adjust_col_width('metadata', dfm, writer)

            # data
            if self.table is not None:
                self.table.index.name = "index"
                self.table.to_excel(writer, sheet_name='table')
                adjust_col_width('table', self.table, writer, width=15)

            # # raw data
            # self.df_raw.index.name = "index"
            # self.df_raw.to_excel(writer, sheet_name='df_raw')
            # adjust_col_width('df_raw', self.df_raw, writer, width=15)

    @classmethod
    def from_xlsx(cls, filepath):
        """save table as xlsx

        :param filepath:
        :return:
        """
        tt = cls(name=filepath)
        tt.table = pd.read_excel(filepath, sheet_name="table")
        dfm = pd.read_excel(filepath, sheet_name="metadata")
        dfm = dfm.set_index("key")
        tt.metadata = tt.metadata.from_dataframe(dfm)
        return tt


class Blob(Data):
    """Binary Large Object"""

    def __init__(self, **kwargs):
        """Binary Large Object"""
        Data.__init__(self, **kwargs)
        self._blob = None

    def _get_blob(self):
        return self._blob

    def _set_blob(self, blob):
        self._blob = blob

    blob = property(fget=_get_blob, fset=_set_blob, doc="blob object")

class DataFrame(Blob):
    """Data Frame aka Table"""

    def __init__(self, **kwargs):
        """DataFrame"""
        Blob.__init__(self, **kwargs)
        self.columns = kwargs.get("columns") or Metadata()

    def _get_blob(self):
        return self._blob

    def _set_blob(self, blob):
        if isinstance(blob, pd.DataFrame):
            self._blob = blob
            self.guess_columns()

    blob = property(fget=_get_blob, fset=_set_blob, doc="blob object")

    def guess_columns(self):
        """extract column names and dtypes from dataframe"""
        if self.blob is not None:
            for icol, col in enumerate(self.blob.columns):
                self.columns.set_attr(col, value=icol, dtype=self.blob[col].dtype.name)

    def to_xlsx(self, path, **kwargs):
        """export atrributes and data to excel

        :param filepath:
        :return:
        """

        filepath = os.path.join(path, "{}.xlsx".format(self.filename))

        def adjust_col_width(sheetname, df, writer, width=40):
            worksheet = writer.sheets[sheetname]  # pull worksheet object
            worksheet.set_column(0, 0, width)
            for idx, col in enumerate(df):  # loop through all columns
                worksheet.set_column(idx+1, idx+1, width)

        with pd.ExcelWriter(filepath) as writer:
            dfm = self.metadata.to_dataframe()
            dfm = dfm.sort_index()
            dfm.index.name = "key"
            dfm.to_excel(writer, sheet_name='metadata')
            adjust_col_width('metadata', dfm, writer)

            dfc = self.columns.to_dataframe()
            dfc = dfc.sort_index()
            dfc.index.name = "key"
            dfc.to_excel(writer, sheet_name='columns')
            adjust_col_width('columns', dfc, writer)

            # data
            if self.blob is not None:
                self.blob.index.name = "index"
                self.blob.to_excel(writer, sheet_name='dataframe')
                adjust_col_width('dataframe', self.blob, writer, width=15)


    @classmethod
    def from_xlsx(cls, filepath, **kwargs):
        """save table as xlsx

        :param filepath:
        :return:
        """
        tt = cls(name=filepath)
        tt.blob = pd.read_excel(filepath, sheet_name="dataframe")
        dfm = pd.read_excel(filepath, sheet_name="metadata")
        dfm = dfm.set_index("key")
        tt.metadata = tt.metadata.from_dataframe(dfm)

        dfc = pd.read_excel(filepath, sheet_name="columns")
        dfc = dfc.set_index("key")
        tt.columns = tt.metadata.from_dataframe(dfc)
        return tt



SDATACLS = {"Data": Data,
            }

__all__ = ["Data"]



def print_classes():
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj):
            print(obj)