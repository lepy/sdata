import os
import uuid
from collections import OrderedDict
#import logging

import numpy as np
import pandas as pd

class PID(object):
    """Process object, which has an uuid and metadata"""

    def __init__(self, *args, **kwargs):
        self._metadata = kwargs.get("metadata") or {}
        try:
            self.uuid = uuid.UUID(kwargs.get("uuid"))
        except:
            self.uuid = uuid.uuid4()
        self.name = kwargs.get("name") or "N.N."


    def get_attr(self, key, default=None):
        return self.metadata.get(key, default)

    def add_attr(self, key, value):
        self.metadata[str(key)] = value

    def set_attr(self, key, value):
        self.metadata[str(key)] = value

    def get_metadata(self):
        return self._metadata
    def set_metadata(self, metadata):
        self._metadata.update(metadata)
    metadata = property(get_metadata, set_metadata)

    def get_uuid(self):
        return uuid.UUID(self._metadata.get("uuid"))
    def set_uuid(self, uuid):
        self._metadata["uuid"] = uuid.hex
    uuid = property(get_uuid, set_uuid)

    def get_name(self):
        return self._metadata.get("name")
    def set_name(self, name):
        self._metadata["name"] = name
    name = property(get_name, set_name)

    def __str__(self):
        return "({0.__class__.__name__}:'{0.name}':{0.uuid.hex})".format(self)

    __repr__ = __str__
