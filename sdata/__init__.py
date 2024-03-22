# -*-coding: utf-8-*-
from __future__ import division

__version__ = '0.23.0'
__revision__ = None
__version_info__ = tuple([int(num) for num in __version__.split('.')])

'''
basic sdata types 
'''

import sys
import uuid
import logging

# fix "ValueError: unsupported pickle protocol: 5"
import pickle
pickle.HIGHEST_PROTOCOL = 4
import pandas

from sdata.metadata import Metadata, Attribute
from sdata.data import Data
from sdata.blob import Blob
from sdata.suuid import SUUID
from sdata.image import Image

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


def osname(name, lower=True):
    mapper = [("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"),
              ("ß", "sz"), (" ", "_"), ("/", "_"), ("\\", "_")]
    for k, v in mapper:
        name = name.replace(k, v)
    if lower is True:
        name = name.lower()
    return name.encode('ascii', 'replace').decode("ascii")


SDATACLS = {"Data": Data,
            "Image": Image,
            "Blob": Blob,
            "SUUID": SUUID,
            }

__all__ = ["Data", "Image", "Blob", "SUUID"]


def print_classes():
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj):
            print(obj)
