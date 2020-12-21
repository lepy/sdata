# -*-coding: utf-8-*-

import logging
logger = logging.getLogger("sdata")
import collections
import pandas as pd
import numpy as np
from sdata.timestamp import TimeStamp
from sdata.data import Data
from sdata.metadata import Metadata, Attribute
import json
import os
import hashlib

class Workbook(Data):
    """Workbook with Sheets

    .. warning::

        highly experimental"""


    def __init__(self, **kwargs):
        """Workbook with Sheets

        :param name:
        :param kwargs:

        """
        Data.__init__(self, **kwargs)

        self._sheets = collections.OrderedDict()


    def create_sheet(self, name):
        """create a sheet to the Workbook

        :param data:
        :return: sdata.Data
        """
        if not isinstance(name, str):
            logger.error("{}.create_sheet: sheet name has to be a string!".format(self.__class__.__name__))
            return
        data = Data(name=name)
        self._sheets[name] = data
        return data

    def add_sheet(self, data):
        """create a sheet to the Workbook

        :param data:
        :return: sdata.Data
        """
        if isinstance(data, Data):
            self._sheets[data.name] = data
        else:
            logger.error("{}.add_sheet: need sdata.Data, got {}".format(self.__class__.__name__, type(data)))

    @property
    def sheetnames(self):
        """return sheet names of the workbook"""
        return list(self._sheets.keys())

    def get_sheet(self, name):
        """get Sheet from Workbook

        :param name:
        :return: df
        """

    @property
    def sheets(self):
        """all sheets of the workbook"""
        return list(self._sheets.values())

    def __iter__(self):
        """

        :return:
        """
        self._isheet = 0
        return self

    def __next__(self):
        """

        :return:
        """
        if self._isheet <= (len(self._sheets.keys()) - 1):
            self._isheet += 1
            return self._sheets.get(list(self._sheets.keys())[self._isheet-1])
        else:
            raise StopIteration