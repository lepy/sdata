# -*-coding: utf-8-*-
from __future__ import division

__version__ = '0.1.0'
__revision__ = None
__version_info__ = tuple([ int(num) for num in __version__.split('.')])

'''
Docu not available
'''

import uuid
from collections import OrderedDict
import logging

class Data(object):
    """run object, e.g. single tension test simulation"""

    def __init__(self, **kwargs):
        self._uuid = None
        self._name = None
        self.uuid = kwargs.get("uuid") or uuid.uuid4()
        self.name = kwargs.get("name") or "N.N."
        self.metadata = kwargs.get("metadata") or {}

    def _get_uuid(self):
        return self._uuid
    def _set_uuid(self, value):
        if isinstance(value, str):
            try:
                self._uuid = uuid.UUID(value).hex
            except ValueError as exp:
                logging.warn("data.uuid: %s" % exp)
        elif isinstance(value, uuid.UUID):
            self._uuid = value.hex
    uuid = property(fget=_get_uuid, fset=_set_uuid)

    def _get_name(self):
        return self._name
    def _set_name(self, value):
        if isinstance(value, str):
            try:
                self._name = value[:256]
            except ValueError as exp:
                logging.warn("data.name: %s" % exp)
        else:
            self._name = str(value)[:256]

    name = property(fget=_get_name, fset=_set_name)

    def __str__(self):
        return "(data '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__

class Group(Data):
    """group object, e.g. single tension test simulation"""

    def __init__(self, **kwargs):
        Data.__init__(self, **kwargs)
        self._uuid = None
        self._group = OrderedDict()
        self.uuid = kwargs.get("uuid") or uuid.uuid4()

        self.metadata = kwargs.get("metadata") or {}

    def get_group(self):
        return self._group
    group = property(get_group)

    def add_data(self, data):
        if isinstance(data, Data):
            self.group[data.uuid.hex] = data
        else:
            logging.warn("ignore run %s (wrong type!)" % data)

    def __str__(self):
        return "(group '%s':%s)" % (self.name, self.uuid)

    __repr__ = __str__