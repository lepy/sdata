# -*-coding: utf-8-*-
from __future__ import division

__version__ = '0.9.0'
__revision__ = None
__version_info__ = tuple([int(num) for num in __version__.split('.')])

'''
basic sdata types 
'''

import sys
import os
import uuid
from collections import OrderedDict
import logging
import numpy as np
import pandas as pd
import shutil
from sdata.metadata import Metadata, Attribute
from sdata.data import Data
from sdata.blob import Blob
import sdata.timestamp as timestamp
import inspect
import json
import hashlib
import base64
from io import BytesIO, StringIO

if sys.version_info < (3, 6):
    import sha3

try:
    import openpyxl
except:
    logging.warning("openpyxl is not available -> no xlsx import")


def uuid_from_str(name):
    return uuid.uuid3(uuid.NAMESPACE_DNS, name)


SDATACLS = {"Data": Data,
            "Blob": Blob
            }

__all__ = ["Data", "Blob"]


def print_classes():
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj):
            print(obj)
