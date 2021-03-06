# -*-coding: utf-8-*-
from __future__ import division

__version__ = '0.17.0'
__revision__ = None
__version_info__ = tuple([int(num) for num in __version__.split('.')])

'''
basic sdata types 
'''

import sys
import uuid
import logging
from sdata.metadata import Metadata, Attribute
from sdata.data import Data
from sdata.blob import Blob

# import sdata.timestamp as timestamp
from sdata.timestamp import today_str, now_utc_str, now_local_str
import inspect

try:
    import openpyxl
except:
    logging.warning("openpyxl is not available -> no xlsx import")
    openpyxl = None


def uuid_from_str(name):
    return uuid.uuid3(uuid.NAMESPACE_DNS, name)



SDATACLS = {"Data": Data,
            "Blob": Blob,
            }

__all__ = ["Data", "Blob"]


def print_classes():
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj):
            print(obj)
