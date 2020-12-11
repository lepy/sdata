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
        """Binary Large Object

        :param name:
        :param url:
        :param filetype:
        :param vault:
        :param kwargs:

        """
        Data.__init__(self, **kwargs)
        self.metadata.add("blob_name", kwargs.get("name", ""))
        self.metadata.add("blob_type", "unknown")
        self.url = kwargs.get("url", "")
        self.metadata.add("blob_sha1", self.sha1)
        self.metadata.add("blob_md5", self.md5)
        self.metadata.add("vault", kwargs.get("vault", ""))
        self.metadata.add("blob_filetype", kwargs.get("filetype", "unknown"))


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
        """calculate the sha1 hash of the blob

        :return: sha1
        """
        hash = hashlib.sha1()
        if self.url and os.path.exists(self.url):
            with open(self.url, "rb") as fh:
                self.update_hash(fh, hash)
            return hash.hexdigest()
        else:
            logging.error("can't open external url '{}'".format(str(self.url)))

    @property
    def md5(self):
        """calculate the md5 hash of the blob

        :return: sha1
        """
        hash = hashlib.md5()
        if self.url and os.path.exists(self.url):
            with open(self.url, "rb") as fh:
                self.update_hash(fh, hash)
            return hash.hexdigest()
        else:
            logging.error("can't open external url '{}'".format(str(self.url)))

    def update_hash(self, fh, hashobject, buffer_size = 65536):
        """A hash represents the object used to calculate a checksum of a
        string of information.

        .. code-block:: python

            hashobject = hashlib.md5()
            df = pd.DataFrame([1,2,3])
            url = "/tmp/blob.csv"
            df.to_csv(url)
            blob = sdata.Blob(url=url)
            fh = open(url, "rb")
            blob.update_hash(fh, hashobject)
            hashobject.hexdigest()

        :param fh: file handle
        :param hashobject: hash object, e.g. hashlib.sha1()
        :param buffer_size: buffer size (default buffer_size=65536)
        :return: hashobject
        """


        with fh as f:
            while True:
                data = f.read(buffer_size)
                if not data:
                    break
                hash.update(data)
        return hash

