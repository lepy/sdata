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

    def __init__(self, **kwargs):
        """Binary Large Object"""
        Data.__init__(self, **kwargs)
        print("1")
        self.metadata.add("blob_name", "")
        self.metadata.add("blob_uuid", "")
        self.metadata.add("blob_sha1", "")
        self._blob = None
        print("2")
