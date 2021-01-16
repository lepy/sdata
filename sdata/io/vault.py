# -*- coding: utf-8 -*-

import logging
logger = logging.getLogger("sdata")
import os
import uuid
from sdata import Data
import pandas as pd

class VaultIndex():
    """Index of a Vault

    """

    INDEXDATAFRAME = "indexdataframe"

    def __init__(self):
        """Vault Index

        """
        self._df = pd.DataFrame(columns=Data.SDATA_ATTRIBUTES)

    def _get_df(self):
        return self._df

    def _set_df(self, df):
        self._df = df

    df = name = property(fget=_get_df, fset=_set_df, doc="index dataframe")

    @classmethod
    def from_hdf5(cls, filepath):
        """read index dataframe from hdf5

        :param filepath:
        :return: VaultIndex
        """
        index = cls()
        if os.path.exists(filepath):
            hdf = pd.HDFStore(filepath)
            index.df = hdf.get(cls.INDEXDATAFRAME)
            hdf.close()
        else:
            logger.error("Index file '{}' is not available".format(filepath))
            raise Exception("Index file is not available")
        return index

    def to_hdf5(self, filepath, **kwargs):
        """store Vault Index in hdf5 store

        :param filepath:
        :param kwargs:
        :return:
        """
        hdf = pd.HDFStore(filepath, **kwargs)
        hdf.put(self.INDEXDATAFRAME, self._df, format='fixed', data_columns=True)
        hdf.close()

class Vault():
    """data vault"""

    INDEXFILENAME = "index"

    def __init__(self, rootpath):
        self._rootpath = None
        self._index = VaultIndex()
        try:
            os.makedirs(os.path.dirname(rootpath), exist_ok=True)
            self._rootpath = rootpath
        except OSError as exp:
            logging.error("Vault Error: {}".format(exp))
            raise exp
        logging.info("create/open vault {}".format(self.rootpath))

        indexpath = os.path.join(rootpath, 'index')
        if os.path.exists(indexpath):
            self.index.from_hdf(indexpath)

    @property
    def rootpath(self):
        return self._rootpath

    def __str__(self):
        return "({}:{})".format(self.__class__.__name__, self.rootpath)

    def __repr__(self):
        return "({}:{})".format(self.__class__.__name__, self.rootpath)

    def list(self):
        """get index from vault

        :return:
        """
        for root, dirs, files in os.walk(self.rootpath, topdown=False):
            for name in files:
                print(os.path.join(root, name))

    @property
    def index(self):
        return self._index

    def reindex(self):
        """get index from vault

        :return: df
        """
        dfs = []
        for root, dirs, files in os.walk(self.rootpath, topdown=False):
            for name in files:
                blob_uuid = name
                dfs.append(self.load_metadata_value_df(blob_uuid))
        df =  pd.concat(dfs)
        self.index.df = df
        self.index.to_hdf5(os.path.join(self.rootpath, self.INDEXFILENAME))
        return df

    def keys(self):
        keys = []
        for root, dirs, files in os.walk(self.rootpath, topdown=False):
            for name in files:
                keys.append(name)
        return keys

    def dump_blob(self, blob):
        """store blob in vault"""
        path = os.path.join(self.rootpath, 'objects', blob.uuid[:2], blob.uuid[-2:]) + os.sep
        logging.info("dump blob {}".format(path))
        try:
            if not os.path.exists(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
        except OSError as exp:
            logging.error("Vault Error: {}".format(exp))
            raise exp
        filepath = os.path.join(path, blob.uuid)
        blob.to_hdf5(filepath)

    def load_blob(self, blob_uuid):
        """get blob from vault"""
        path = os.path.join(self.rootpath, 'objects', blob_uuid[:2], blob_uuid[-2:]) + os.sep
        logging.info("load blob {}".format(path))
        filepath = os.path.join(path, blob_uuid)
        data = Data.from_hdf5(filepath)
        return data

    def load_blob_metadata(self, blob_uuid):
        """get blob.metadata from vault"""
        path = os.path.join(self.rootpath, 'objects', blob_uuid[:2], blob_uuid[-2:]) + os.sep
        logging.info("get blob metadata {}".format(path))
        filepath = os.path.join(path, blob_uuid)
        metadata = Data.metadata_from_hdf5(filepath)
        return metadata

    def load_metadata_value_df(self, blob_uuid):
        """get blob.metadata attribute.value(s) from vault"""
        metadata = self.load_blob_metadata(blob_uuid)
        return metadata.sdft

