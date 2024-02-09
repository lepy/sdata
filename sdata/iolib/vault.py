# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger("sdata")
import os
import uuid
from sdata import Data
from sdata.metadata import Metadata
from sdata.timestamp import now_utc_str
from sdata.contrib.simple_graph_db import Database

import pandas as pd

class VaultException(Exception): pass
class FilesystemVaultException(VaultException): pass
class Hdf5VaultException(VaultException): pass

class VaultIndex:
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
        return sorted(list(self.df[[Data.SDATA_NAME]].drop_duplicates().iloc[:, 0]))

    def update_from_sdft(self, sdft):
        self.df = self.df.append(sdft)


class VaultSqliteIndex:
    """Index of a Vault

    """

    def __init__(self, db_file):
        """Vault Index

        .. code-block:: python

                db_file = "/tmp/test_sqlitevault.sqlite"
                vi = VaultSqliteIndex(db_file=db_file)
                vi.drop_db()

                d1 = Data(name="d1", uuid=sdata.uuid_from_str("d1"))
                vi.update_from_metadata(d1.metadata)

                vi.get_all_metadata()


        """
        self.db_file = db_file
        self.initialize()

    def initialize(self):
        """initialize index db

        :return:
        """
        logger.debug(f"initialize db {self.db_file}")
        self.db = Database(db_file=self.db_file)

    def get_all_metadata(self):
        """get all blob metadata

        :return:
        """
        return self.db.get_all_nodes()

    def update_from_metadata(self, metadata):
        """store sdata metadata"""
        d = metadata.get_sdict()
        uid = d.get("!sdata_uuid")
        logger.debug(f"add '{uid}' to vault index")
        self.db.upsert_node(identifier=uid, data=d)
        puid = d.get("!sdata_parent")
        if len(puid) > 0:
            if len(self.db.find_node(puid)) == 0:
                self.db.upsert_node(identifier=puid, data={"!sdata_uuid": puid, '!sdata_name': "?"})
            self.db.connect_nodes(puid, uid, {"con_type": "parent"})

    def drop_db(self):
        """create new database"""
        os.remove(self.db_file)
        self.initialize()

    @property
    def df(self):
        """index dataframe

        :return: pd.DataFrame
        """
        df = pd.DataFrame(self.get_all_metadata())
        return df.set_index(keys=["id"])


class Vault:
    """data vault
    
    """
    INDEXFILENAME = "index"
    OBJECTPATH = "objects"

    def __init__(self, rootpath, **kwargs):
        """data vault

        :param kwargs:
        """
        self._index = VaultIndex()
        if isinstance(rootpath, str):
            self._rootpath = rootpath
        else:
            raise VaultException("invalid rootpath")

    @property
    def rootpath(self):
        return self._rootpath

    def __str__(self):
        return "({}:{})".format(self.__class__.__name__, self.rootpath)

    def __repr__(self):
        return "({}:{})".format(self.__class__.__name__, self.rootpath)

    @property
    def index(self):
        """get vault index

        :return:
        """
        raise NotImplementedError()

    def reindex(self):
        """create index from vault

        :return:
        """
        raise NotImplementedError()

    def keys(self):
        raise NotImplementedError()

    def dump_blob(self, blob):
        """store blob in vault"""
        raise NotImplementedError()

    def load_blob(self, blob_uuid):
        """get blob from vault"""
        raise NotImplementedError()

    def find_blobs(self, name=None, **kwargs):
        """find blobs in vault"""
        raise NotImplementedError()

    def items(self):
        """get vault items

        :return: (key, blob)
        """
        keys = self.keys()
        if len(keys) > 10:
            logger.warning("Consider vault.iteritems!")
        items = []
        for key in keys:
            items.append((key, self.load_blob(key)))
        return items

    def iteritems(self):
        raise NotImplementedError()

    def itervalues(self):
        raise NotImplementedError()

    def values(self):
        """get vault values

        :return: (key, blob)
        """
        keys = self.keys()
        if len(keys) > 10:
            logger.warning("Consider vault.iteritems ")
        values = []
        for key in keys:
            values.append(self.load_blob(key))
        return values

class Hdf5Vault(Vault):
    """data vault on the filesystem"""

    def __init__(self, rootpath, **kwargs):
        """

        :param rootpath:
        :param kwargs:
        """
        Vault.__init__(self, rootpath, **kwargs)
        self.initialize(mode="a")

    def initialize(self, **kwargs):
        logger.info(f"initialize {self.rootpath}")
        metadata = Metadata()
        metadata.add("ctime", now_utc_str())
        with pd.HDFStore(self.rootpath, **kwargs) as hdf:
            hdf.put('metadata', metadata.df, format='fixed', data_columns=True)

    def _objectpath(self, data_uuid):
        return "/" + "/".join([self.OBJECTPATH, data_uuid[:2], data_uuid[-2:], data_uuid])

    def dump_blob(self, data):
        """store blob in vault"""
        path = self._objectpath(data.uuid)
        with pd.HDFStore(self.rootpath, mode="a") as hdf:
            if not isinstance(data.df, pd.DataFrame):
                df = pd.DataFrame()
            else:
                df = data.df
            logger.debug(f"store {path}/metadata")
            hdf.put(f'{path}/metadata', data.metadata.df, format='fixed', data_columns=True)
            hdf.put(f'{path}/table', df, format='fixed', data_columns=True)
            hdf.put(f'{path}/description', data.description_to_df(), format='fixed',
                         data_columns=True)
        return path

    def load_blob(self, data_uuid, ignore_errors=True):
        """get blob from vault"""
        path = self._objectpath(data_uuid)
        logging.info("load blob {}".format(path))
        logger.debug (f'try to load {path}/metadata')

        with pd.HDFStore(self.rootpath, mode="r") as hdf:
            metadata_path = f'{path}/metadata'
            table_path = f'{path}/table'
            description_path = f'{path}/description'

            try:
                df_metadata = hdf.get(metadata_path)
                df_table = hdf.get(table_path)
                df_description = hdf.get(description_path)
                metadata = Metadata.from_dataframe(df_metadata)
                # logger.debug("hdf {}".format(metadata.get("!sdata_uuid").value))
                data = Data(metadata=metadata, table=df_table)
                data.description_from_df(df_description)
                return data
            except KeyError as exp:
                logger.warning(exp)
                if ignore_errors is False:
                    raise Hdf5VaultException(exp)

    def keys(self):
        """get all blob keys

        .. code-block:: python

            >>> keys = vault.keys()
            ['b5d2d05638db48d69d044a34e83aaa41', '21b83703d98e38a7be2e50e38326d0ce']

        :return: list of keys
        """
        keys = set()
        with pd.HDFStore(self.rootpath, mode="r") as hdf:
            hdf5_keys = hdf.keys()

        for key in hdf5_keys:
            kp = key.split("/")
            if len(kp) == 5:
                print(kp, len(kp))
                keys.add(kp[4])
        return list(keys)

    def iteritems(self):
        hdf = pd.HDFStore(self.rootpath, mode="r")
        # todo: close hdf
        return hdf.iteritems()

class FileSystemVault(Vault):
    """data vault on the filesystem"""

    def __init__(self, rootpath, **kwargs):
        """

        :param rootpath:
        :param kwargs:
        """
        Vault.__init__(self, rootpath, **kwargs)
        self._rootpath = None

        try:
            rootpath = os.path.dirname(rootpath)
            os.makedirs(rootpath, exist_ok=True)
            self._rootpath = rootpath
        except OSError as exp:
            logging.error("Vault Error: '{}'".format(exp))
            raise exp
        logging.info("create/open vault '{}'".format(rootpath))

        print(os.path.exists(self.rootpath))

        indexpath = os.path.join(rootpath, 'vaultindex.sqlite')
        logging.info(f"create/open vaultindex '{indexpath}'")
        self._index = VaultSqliteIndex(indexpath)

        # indexpath = os.path.join(rootpath, 'index')
        # if os.path.exists(indexpath):
        #      logging.debug("load vault index {}".format(self.rootpath))
        #     self._index = VaultIndex.from_hdf5(indexpath)

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
        """get vault index

        :return:
        """
        return self._index

    def reindex(self):
        """create index from vault

        :return:
        """
        self.index.drop_db()
        objectpath = os.path.join(self.rootpath, self.OBJECTPATH)
        for root, dirs, files in os.walk(objectpath, topdown=False):
            for name in files:
                blob_uuid = name
                self.index.update_from_metadata(self.load_blob_metadata(blob_uuid))

    def reindex_hfd5(self):
        """get index from vault

        :return: df
        """
        dfs = []
        objectpath = os.path.join(self.rootpath, self.OBJECTPATH)
        for root, dirs, files in os.walk(objectpath, topdown=False):
            for name in files:
                blob_uuid = name
                dfs.append(self.load_blob_metadata_value_df(blob_uuid))
        df = pd.concat(dfs)
        self.index.df = df
        self.index.to_hdf5(os.path.join(self.rootpath, self.INDEXFILENAME))
        return df

    # def dump_hdf5_index(self):
    #     self.index.to_hdf5(os.path.join(self.rootpath, self.INDEXFILENAME))

    def keys(self):
        keys = []
        objectpath = os.path.join(self.rootpath, self.OBJECTPATH)
        for root, dirs, files in os.walk(objectpath, topdown=False):
            for name in files:
                keys.append(name)
        return keys

    # def _update_index(self, metadata):
    #     return metadata.sdft

    def dump_blob(self, blob):
        """store blob in vault"""
        path = os.path.join(self.rootpath, self.OBJECTPATH, blob.uuid[:2], blob.uuid[-2:]) + os.sep
        logging.debug("dump blob {}".format(path))
        try:
            if not os.path.exists(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
        except OSError as exp:
            logging.error("Vault Error: {}".format(exp))
            raise exp
        filepath = os.path.join(path, blob.uuid)
        blob.to_hdf5(filepath)
        # self.index.update_from_sdft(blob.metadata.sdft)
        self.index.update_from_metadata(blob.metadata)

    def load_blob(self, blob_uuid):
        """get blob from vault"""
        path = os.path.join(self.rootpath, self.OBJECTPATH, blob_uuid[:2], blob_uuid[-2:]) + os.sep
        logging.debug("load blob {}".format(path))
        filepath = os.path.join(path, blob_uuid)
        data = Data.from_hdf5(filepath)
        return data

    def load_blob_metadata(self, blob_uuid):
        """get blob.metadata from vault"""
        path = os.path.join(self.rootpath, 'objects', blob_uuid[:2], blob_uuid[-2:]) + os.sep
        logging.debug("get blob metadata {}".format(path))
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
        df_selected = self.index.df[(self.index.df[Data.SDATA_NAME] == name)]
        print("df_selected", len(df_selected))

        datas = []
        for uid, row in self.index.df[(self.index.df[Data.SDATA_NAME] == name)].iterrows():
            logging.debug("get_blob_by_name: load {}".format(uid))
            data = self.load_blob(uid)
            datas.append(data)
        return datas
