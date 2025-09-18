# -*-coding: utf-8-*-

import logging

logger = logging.getLogger("sdata")
import collections
import pandas as pd
import numpy as np
from sdata.timestamp import TimeStamp
import sdata
from sdata.data import Data
from sdata.metadata import Metadata, Attribute
import json
import os
import hashlib
import uuid


class Workbook(Data):
    """Workbook with Sheets

    .. warning::

        highly experimental"""

    def __init__(self, **kwargs):
        """Workbook with Sheets

        :param name:
        :param kwargs:

        """
        Data.__init__(self, **kwargs)

        self._sheets = collections.OrderedDict()

    def create_sheet(self, name):
        """create a sheet to the Workbook

        :param data:
        :return: sdata.Data
        """
        if not isinstance(name, str):
            logger.error("{}.create_sheet: sheet name has to be a string!".format(self.__class__.__name__))
            return
        data = Data(name=name)
        self._sheets[name] = data
        return data

    def add_sheet(self, data):
        """create a sheet to the Workbook

        :param data:
        :return: sdata.Data
        """
        if isinstance(data, (Data, sdata.Data)):
            self._sheets[data.name] = data
        else:
            logger.error("{}.add_sheet: need sdata.Data, got {}".format(self.__class__.__name__, type(data)))

    @property
    def sheetnames(self):
        """return sheet names of the workbook"""
        return list(self._sheets.keys())

    def get_sheet(self, name, default=None):
        """get Sheet from Workbook

        :param name:
        :return: sheet data
        """
        return self._sheets.get(name, default)

    @property
    def sheets(self):
        """all sheets of the workbook"""
        return list(self._sheets.values())

    def __getitem__(self, name):
        return self.get(name)

    def __iter__(self):
        """

        :return:
        """
        self._isheet = 0
        return self

    def __next__(self):
        """

        :return:
        """
        if self._isheet <= (len(self._sheets.keys()) - 1):
            self._isheet += 1
            return self._sheets.get(list(self._sheets.keys())[self._isheet - 1])
        else:
            raise StopIteration

    def get(self, name, default=None):
        if self.get_sheet(name) is not None:
            return self.get_sheet(name)
        else:
            return default

    def keys(self):
        """

        :return: list of Attribute names
        """
        return list(self._sheets.keys())

    def values(self):
        """

        :return: list of Attribute values
        """
        return list(self._sheets.values())

    def items(self):
        """

        :return: list of Attribute items (keys, values)
        """
        return list(self._sheets.items())

    def to_hdf5(self, filepath, **kwargs):
        """export sdata.Data to hdf5

        :param filepath:
        :param complib: default='zlib' ['zlib', 'lzo', 'bzip2', 'blosc', 'blosc:blosclz', 'blosc:lz4', 'blosc:lz4hc', 'blosc:snappy', 'blosc:zlib', 'blosc:zstd']
        :param complevel: default=9 [0-9]

        :return:
        """
        if not isinstance(self.df, pd.DataFrame):
            df = pd.DataFrame()
        else:
            df = self.df
        kwargs["mode"] = "w"
        if kwargs.get("complib") is None:
            kwargs["complib"] = "zlib"

        if kwargs.get("complevel") is None:
            kwargs["complevel"] = 9

        with pd.HDFStore(filepath, **kwargs) as hdf:
            hdf.put('metadata', self.metadata.df, format='fixed', data_columns=True)
            hdf.put('table', df, format='fixed', data_columns=True)
            hdf.put('description', self.description_to_df(), format='fixed', data_columns=True)

            for sheet in self.sheets:
                if not isinstance(sheet.df, pd.DataFrame):
                    logger.warning("no df in sheet!")
                    df = pd.DataFrame()
                else:
                    df = sheet.df
                hdf.put(f'/sheets/uuid_{sheet.uuid}/metadata', sheet.metadata.df, format='fixed', data_columns=True)
                hdf.put(f'/sheets/uuid_{sheet.uuid}/table', df, format='fixed', data_columns=True)
                hdf.put(f'/sheets/uuid_{sheet.uuid}/description', sheet.description_to_df(), format='fixed',
                        data_columns=True)

    @classmethod
    def metadata_from_hdf5(cls, filepath, **kwargs):
        """import sdata.Data.Metadata from hdf5

        :param filepath:
        :return: sdata.Data
        """
        if not os.path.exists:
            logger.error("hdf5 file '{}' not available".format(filepath))
            return

        with pd.HDFStore(filepath, mode="r+") as hdf:
            metadata_path = "/metadata".format(uuid)
            df_metadata = hdf.get(metadata_path)
            metadata = Metadata.from_dataframe(df_metadata)
            return metadata

    @classmethod
    def from_hdf5(cls, filepath, **kwargs):
        """import sdata.Data from hdf5

        :param filepath:
        :return: sdata.Data
        """
        if not os.path.exists:
            logger.error("hdf5 file '{}' not available".format(filepath))
            return

        def read_data(nodepath):
            metadata_path = f"{nodepath}/metadata".format(uuid)
            table_path = f"{nodepath}/table".format(uuid)
            description_path = f"{nodepath}/description".format(uuid)
            df_metadata = hdf.get(metadata_path)
            # print(df_metadata)
            df_table = hdf.get(table_path)
            df_description = hdf.get(description_path)
            metadata = Metadata.from_dataframe(df_metadata)
            # logger.debug("hdf {}".format(metadata.get("!sdata_uuid").value))
            sheetdata = Data(metadata=metadata, table=df_table)
            sheetdata.metadata = metadata
            sheetdata.description_from_df(df_description)
            # print(sheetdata.df)
            return sheetdata

        with pd.HDFStore(filepath, mode="r+") as hdf:
            metadata_path = "/metadata".format(uuid)
            table_path = "/table".format(uuid)
            description_path = "/description".format(uuid)
            df_metadata = hdf.get(metadata_path)
            df_table = hdf.get(table_path)
            df_description = hdf.get(description_path)
            metadata = Metadata.from_dataframe(df_metadata)
            # logger.debug("hdf {}".format(metadata.get("!sdata_uuid").value))
            wb = Workbook(metadata=metadata, table=df_table)
            wb.metadata = metadata
            wb.description_from_df(df_description)
            s = hdf.get_node("/sheets")
            for g in s._v_groups:
                # print(g)
                nodepath = f"/sheets/{g}"
                sheetdata = read_data(nodepath)
                wb.add_sheet(sheetdata)
        return wb
