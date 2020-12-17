# -*-coding: utf-8-*-
import logging
logger = logging.getLogger("sdata")
import pandas as pd
import numpy as np
from sdata import Data
from sdata.data import Sdata_Uuid_Exeption
import uuid

# import sdata.experiments.ks2
# import sdata.experiments.lapshear
# import sdata.experiments.material
#
# # ["name", "default_value", "dtype", "unit", "description", "required"]
# part_default_attributes = [
#     ["part_id", None, "str", "-", "Part ID", True],
# ]


class TestProgram(Data):
    """A sdata Testprogram

    """

    SDATA_TESTPROGRAM_NAME = "!sdata_testprogram_name"
    SDATA_TESTPROGRAM_UUID = "!sdata_testprogram_uuid"

    def __init__(self, **kwargs):
        """

        :param kwargs:
        """
        Data.__init__(self, **kwargs)

        self.metadata.add(name=self.SDATA_CLASS, value=self.__class__.__name__, dtype="str")
        self.metadata.add(name=self.SDATA_TESTPROGRAM_NAME, value="N.N.", dtype="str")
        self.metadata.add(name=self.SDATA_TESTPROGRAM_UUID, value="", dtype="str")

        print("set testprogram", kwargs)

        if kwargs.get("uuid_testprogram") is not None:
            try:
                self.uuid_testprogram = kwargs.get("uuid_testprogram") # store given uuid str or generate a new uuid
            except Sdata_Uuid_Exeption as exp:
                if self.auto_correct is True:
                    logger.warning("got invald uuid -> generate a new uuid")
                    self.uuid_testprogram = uuid.uuid4().hex
                else:
                    raise

        if kwargs.get("name_testprogram") is not None:
            self.name_testprogram = kwargs.get("name_testprogram")


    def _get_uuid_testprogram(self):
        return self.metadata.get(self.SDATA_TESTPROGRAM_UUID).value
        # return self._uuid

    def _set_uuid_testprogram(self, value):
        print("set uuid", value)
        if isinstance(value, str):
            try:
                uuid.UUID(value)
                self.metadata.set_attr(self.SDATA_TESTPROGRAM_UUID, uuid.UUID(value).hex)
            except ValueError as exp:
                logger.warning("data.uuid: %s" % exp)
                raise Sdata_Uuid_Exeption("got invalid uuid str '{}'".format(str(value)))
        elif isinstance(value, uuid.UUID):
            self.metadata.set_attr(self.SDATA_TESTPROGRAM_UUID, value.hex)
        else:
            logger.error("Data.uuid: invalid uuid '{}'".format(value))
            raise Exception("Data.uuid: invalid uuid '{}'".format(value))

    uuid_testprogram = property(fget=_get_uuid_testprogram, fset=_set_uuid_testprogram, doc="uuid of the testprogram")

    def _get_name_testprogram(self):
        # return self._name
        return self.metadata.get(self.SDATA_TESTPROGRAM_NAME).value

    def _set_name_testprogram(self, value):
        if isinstance(value, str):
            try:
                self.metadata.set_attr(self.SDATA_TESTPROGRAM_NAME, str(value)[:256])
            except ValueError as exp:
                logger.warning("data.name_testprogram: %s" % exp)
        else:
            # self._name = str(value)[:256]
            self.metadata.set_attr(self.SDATA_TESTPROGRAM_NAME, str(value)[:256])

    name_testprogram = property(fget=_get_name_testprogram, fset=_set_name_testprogram, doc="name of the testprogram")

__all__ = []
