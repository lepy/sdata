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
        hdf.put(self.INDEXDATAFRAME, self.df, format='fixed', data_columns=True)
        hdf.close()

    def get_names(self):
        """get all data names from index"""
        return sorted(list(self.df[[Data.SDATA_NAME]].drop_duplicates().iloc[:,0]))

    def update_from_sdft(self, sdft):
        self.df = self.df.append(sdft)

class Vault():
    """data vault
    
    """
    INDEXFILENAME = "index"
    OBJECTPATH = "objects"

    def __init__(self, **kwargs):
        """data vault

        :param kwargs:
        """
        self._index = VaultIndex()


class FileSystemVault(Vault):
    """data vault on the filesystem"""


    def __init__(self, rootpath, **kwargs):
        Vault.__init__(self, **kwargs)
        self._rootpath = None

        try:
            os.makedirs(os.path.dirname(rootpath), exist_ok=True)
            self._rootpath = rootpath
        except OSError as exp:
            logging.error("Vault Error: {}".format(exp))
            raise exp
        logging.info("create/open vault {}".format(self.rootpath))

        indexpath = os.path.join(rootpath, 'index')
        if os.path.exists(indexpath):
            logging.debug("load vault index {}".format(self.rootpath))
            self._index = VaultIndex.from_hdf5(indexpath)

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
        objectpath = os.path.join(self.rootpath, self.OBJECTPATH)
        for root, dirs, files in os.walk(objectpath, topdown=False):
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
        objectpath = os.path.join(self.rootpath, self.OBJECTPATH)
        for root, dirs, files in os.walk(objectpath, topdown=False):
            for name in files:
                blob_uuid = name
                dfs.append(self.load_blob_metadata_value_df(blob_uuid))
        df =  pd.concat(dfs)
        self.index.df = df
        self.index.to_hdf5(os.path.join(self.rootpath, self.INDEXFILENAME))
        return df

    def dump_hdf5_index(self):
        self.index.to_hdf5(os.path.join(self.rootpath, self.INDEXFILENAME))

    def keys(self):
        keys = []
        objectpath = os.path.join(self.rootpath, self.OBJECTPATH)
        for root, dirs, files in os.walk(objectpath, topdown=False):
            for name in files:
                keys.append(name)
        return keys

    def _update_index(self, metadata):
        return metadata.sdft

    def dump_blob(self, blob):
        """store blob in vault"""
        path = os.path.join(self.rootpath, self.OBJECTPATH, blob.uuid[:2], blob.uuid[-2:]) + os.sep
        logging.info("dump blob {}".format(path))
        try:
            if not os.path.exists(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
        except OSError as exp:
            logging.error("Vault Error: {}".format(exp))
            raise exp
        filepath = os.path.join(path, blob.uuid)
        blob.to_hdf5(filepath)
        self.index.update_from_sdft(blob.metadata.sdft)

    def load_blob(self, blob_uuid):
        """get blob from vault"""
        path = os.path.join(self.rootpath, self.OBJECTPATH, blob_uuid[:2], blob_uuid[-2:]) + os.sep
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

    def load_blob_metadata_value_df(self, blob_uuid):
        """get blob.metadata attribute.value(s) from vault"""
        metadata = self.load_blob_metadata(blob_uuid)
        return metadata.sdft

    def get_blob_by_name(self, name):
        """get blob by name

        :param name:
        :return:
        """
        df_selected = self.index.df[(self.index.df[Data.SDATA_NAME]==name)]
        print("df_selected", len(df_selected))

        datas = []
        for uid, row in self.index.df[(self.index.df[Data.SDATA_NAME]==name)].iterrows():
            logging.debug("get_blob_by_name: load {}".format(uid))
            data = self.load_blob(uid)
            datas.append(data)
        return datas

