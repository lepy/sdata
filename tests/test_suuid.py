# -*-coding: utf-8-*-
import logging
logger = logging.getLogger("sdata")

import sys
import os
import pandas as pd

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

import sdata
import uuid

def test_suuid():
