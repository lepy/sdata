# -*-coding: utf-8-*-

import logging
import collections
import pandas as pd
import numpy as np
from sdata.timestamp import TimeStamp
from sdata.data import Data
from sdata.metadata import Metadata, Attribute
import json
import os
import hashlib


class Blob(Data):
    """Binary Large Object as reference

    .. warning::

        highly experimental"""

    VAULT_TYPES = ["filesystem", "hdf5", "db", "www"]

    def __init__(self, **kwargs):
        """Binary Large Object"""
        Data.__init__(self, **kwargs)
        self.metadata.add("blob_name", "")
        self.metadata.add("blob_sha1", "")
        self.metadata.add("blob_url", "")
        self.metadata.add("blob_type", "")
        self.metadata.add("vault", "")

    def _get_url(self):
        # return self._name
        return self.metadata.get("blob_url").value

    def _set_url(self, value):
        if isinstance(value, str):
            try:
                self.metadata.set_attr("blob_url", str(value)[:256])
            except ValueError as exp:
                logging.warning("blob.url: %s" % exp)
        else:
            # self._name = str(value)[:256]
            self.metadata.set_attr("blob_url", str(value)[:256])

    url = property(fget=_get_url, fset=_set_url, doc="url of the blob")

    def set_reference(self, url, **kwargs):
        """set refence to file object

        :param url: url to the external blob
        :param name: name of the blob
        :param btype: blob file type, e.g. pdf, csv
        :return:
        """
        self.metadata.add("blob_name", kwargs.get("name"))
        self.metadata.add("blob_uuid", "")
        self.metadata.add("vault", "")
        self.metadata.add("blob_sha1", "")
        self.metadata.add("blob_url", url)
        self.metadata.add("blob_format", "")

    def exists(self, vault="filesystem"):
        """Test whether a object under the blob.url exists.

        :param vault:
        :return:
        """
        if vault == "filesystem":
            if os.path.exists(self.url):
                return True
            else:
                return False
        else:
            return False

    @property
    def sha1(self):
        """

        :return:
        """

    def update_hash(self, fh, hash):
        """A hash represents the object used to calculate a checksum of a
        string of information.

        .. code-block:: python

            hash = hashlib.md5()
            df = pd.DataFrame([1,2,3])
            url = "/tmp/blob.csv"
            df.to_csv(url)
            blob = sdata.Blob(url=url)
            fh = open(url, "rb")
            blob.update_hash(fh, hash)
            hash.hexdigest()

        :param fh: file handle
        :param hash: hash object, e.g. hashlib.sha1()
        :return: hash
        """

        # BUF_SIZE is totally arbitrary, change for your app!
        BUF_SIZE = 65536  # lets read stuff in 64kb chunks!

        with fh as f:
            while True:
                data = f.read(BUF_SIZE)
                if not data:
                    break
                hash.update(data)
        return hash