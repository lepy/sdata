# -*- coding: utf-8 -*-

import logging
logger = logging.getLogger("sdata")
import os
import uuid
import numpy as np
import pandas as pd
from sdata.io import PID
from sdata import Data
from sdata.metadata import Metadata


class FlatHDFDataStore():
    """Flat HDF5 Store

    .. code-block:: python

        store = FlatHDFDataStore(filepath="/tmp/mystore.h5")

        data = sdata.Data(name="otto",
                          uuid="d4e97cedca6238bea16732ce88c1922f",
                          table=pd.DataFrame({"a": [1, 2, 3]}),
                          description="Hallo\nSpencer")
        store.put(data)

        loaded_data = store.get_data_by_uuid("d4e97cedca6238bea16732ce88c1922f")
        assert data.sha3_256 == loaded_data.sha3_256


    """
    def __init__(self, filepath, **kwargs):
        """Flat HDF5 Store on file system

        :param filepath: e.g. /tmp/mystore.h5
        :param kwargs:
        """
        self.hdf = pd.HDFStore(filepath, **kwargs)

    def put(self, data):
        """store data in a pandas hdf5 store"""
        if not isinstance(data.df, pd.DataFrame):
            df = pd.DataFrame()
        else:
            df = data.df
        self.hdf.put('{}/metadata'.format(data.uuid), data.metadata.df, format='fixed', data_columns=True)
        self.hdf.put('{}/table'.format(data.uuid), df, format='fixed', data_columns=True)
        self.hdf.put('{}/description'.format(data.uuid), data.description_to_df(), format='fixed', data_columns=True)

    def keys(self):
        return [x.split("/")[1] for x in self.hdf.keys() if "metadata" in x]

    def get_all_metadata(self):
        metadata_pathes = [x for x in self.hdf.keys() if "metadata" in x]
        datas= []
        for metadata_path in metadata_pathes:
            metadata_df = self.hdf.get(metadata_path)
            metadata = Metadata.from_dataframe(metadata_df)
            metadata.name = metadata.get("!sdata_uuid").value
            datas.append(metadata)
        return datas

    def get_dict(self):
        d = dict()
        for metadata in self.get_all_metadata():
            d[metadata.get("!sdata_name").value] = metadata.get("!sdata_uuid").value
        return d

    def get_data_by_uuid(self, uuid):
        """get table by uuid

        :param uuid:
        :return:
        """
        if uuid not in self.keys():
            logger.error("nod data with uuid '{}'".format(uuid))
            return None
        metadata_path = "/{}/metadata".format(uuid)
        table_path = "/{}/table".format(uuid)
        description_path = "/{}/description".format(uuid)
        df_metadata = self.hdf.get(metadata_path)
        df_table = self.hdf.get(table_path)
        df_description = self.hdf.get(description_path)
        metadata = Metadata.from_dataframe(df_metadata)
        # logger.debug("hdf {}".format(metadata.get("!sdata_uuid").value))
        data = Data(metadata=metadata, table=df_table)
        data.description_from_df(df_description)
        return data

    def close(self):
        """close hdf store

        :return:
        """
        self.hdf.close()