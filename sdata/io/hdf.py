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
    def __init__(self, filepath, **kwargs):
        self.hdf = pd.HDFStore(filepath)

    def put(self, data):
        """store data in a pandas hdf5 store"""
        if not isinstance(data.df, pd.DataFrame):
            df = pd.DataFrame()
        else:
            df = data.df
        self.hdf.put('{}/metadata'.format(data.uuid), data.metadata.df, format='fixed', data_columns=True)
        self.hdf.put('{}/table'.format(data.uuid), df, format='fixed', data_columns=True)

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
        df_metadata = self.hdf.get(metadata_path)
        df_table = self.hdf.get(table_path)
        metadata = Metadata.from_dataframe(df_metadata)
        # logger.debug("hdf {}".format(metadata.get("!sdata_uuid").value))
        data = Data(metadata=metadata, table=df_table)
        return data

    def close(self):
        """close hdf store

        :return:
        """
        self.hdf.close()