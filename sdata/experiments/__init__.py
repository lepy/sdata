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

    def __init__(self, **kwargs):
        """

        :param kwargs:
        """
        Data.__init__(self, **kwargs)
        self.metadata.add(name=self.SDATA_CLASS, value=self.__class__.__name__, dtype="str")

        # if kwargs.get("uuid_testprogram") is not None:
        #     try:
        #         self.uuid_testprogram = kwargs.get("uuid_testprogram") # store given uuid str or generate a new uuid
        #     except Sdata_Uuid_Exeption as exp:
        #         if self.auto_correct is True:
        #             logger.warning("got invald uuid -> generate a new uuid")
        #             self.uuid_testprogram = uuid.uuid4().hex
        #         else:
        #             raise

        self.name_testprogram = self.name
        self.uuid_testprogram = self.uuid

        if kwargs.get("name_testprogram") is not None:
            self._set_name(kwargs.get("name_testprogram"))
        if kwargs.get("uuid_testprogram") is not None:
            self._set_uuid(kwargs.get("uuid_testprogram"))

    def gen_testseries(self, **kwargs):
        """generate TestSeries instance

        :param kwargs:
        :return: TestSeries()
        """
        ts = TestSeries(**kwargs)
        ts.project = self.project
        ts.name_testprogram = self.name_testprogram
        ts.uuid_testprogram = self.uuid_testprogram
        ts.metadata.add(self.SDATA_PARENT, self.uuid)
        return ts

    @property
    def longname(self):
        return "_".join([self.name_testprogram])

class TestSeries(TestProgram):
    """A sdata TestSeries

    """

    SDATA_TESTPROGRAM_NAME = "!sdata_testprogram_name"
    SDATA_TESTPROGRAM_UUID = "!sdata_testprogram_uuid"

    SDATA_TESTTYPE = "!sdata_testtype"

    def __init__(self, **kwargs):
        """Test Series

        :param kwargs:
        """
        TestProgram.__init__(self, **kwargs)

        self.metadata.add(name=self.SDATA_CLASS, value=self.__class__.__name__, dtype="str")
        self.metadata.add(name=self.SDATA_TESTPROGRAM_NAME, value="N.N.", dtype="str", description="name of the testprogram")
        self.metadata.add(name=self.SDATA_TESTPROGRAM_UUID, value="", dtype="str", description="uuid of the testprogram")
        self.metadata.add(name=self.SDATA_TESTTYPE, value="", dtype="str", description="test type")

        # if kwargs.get("name_testprogram") is not None:
        #     self.name_testprogram = kwargs.get("name_testprogram")
        #
        # if kwargs.get("uuid_testseries") is not None:
        #     try:
        #         self.uuid_testseries = kwargs.get("uuid_testseries") # store given uuid str or generate a new uuid
        #     except Sdata_Uuid_Exeption as exp:
        #         if self.auto_correct is True:
        #             logger.warning("got invald uuid -> generate a new uuid")
        #             self.uuid_testseries = uuid.uuid4().hex
        #         else:
        #             raise

        self.uuid_testseries = self.uuid
        self.name_testseries = self.name

        # if kwargs.get("name") is not None:
        #     self._set_name(kwargs.get("name"))
        # if kwargs.get("uuid") is not None:
        #     self._set_uuid(kwargs.get("uuid"))

        # if kwargs.get("name_testseries") is not None:
        #     self.name_testseries = kwargs.get("name_testseries")

        if kwargs.get("testtype") is not None:
            self._set_testtype(kwargs.get("testtype"))
        if kwargs.get("name_testseries") is not None:
            self._set_name(kwargs.get("name_testseries"))
        if kwargs.get("uuid_testseries") is not None:
            self._set_uuid(kwargs.get("uuid_testseries"))
        if kwargs.get("name_testprogram") is not None:
            self._set_name_testprogram(kwargs.get("name_testprogram"))
        if kwargs.get("uuid_testprogram") is not None:
            self._set_uuid_testprogram(kwargs.get("uuid_testprogram"))

    uuid_testseries = property(fget=TestProgram._get_uuid, fset=TestProgram._set_uuid, doc="uuid of the testseries")
    name_testseries = property(fget=TestProgram._get_name, fset=TestProgram._set_name, doc="name of the testseries")

    def _get_uuid_testprogram(self):
        return self.metadata.get(self.SDATA_TESTPROGRAM_UUID).value
        # return self._uuid

    def _set_uuid_testprogram(self, value):
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

    def _get_testtype(self):
        return self.metadata.get(self.SDATA_TESTTYPE).value

    def _set_testtype(self, value):
        if isinstance(value, str):
            try:
                self.metadata.set_attr(self.SDATA_TESTTYPE, str(value)[:256])
            except ValueError as exp:
                logger.warning("data.testtype: %s" % exp)
        else:
            self.metadata.set_attr(self.SDATA_TESTTYPE, str(value)[:256])

    testtype = property(fget=_get_testtype, fset=_set_testtype, doc="testtype of the testseries")

    def gen_test(self, **kwargs):
        """generate Test instance

        :param kwargs:
        :return: Test()
        """
        t = Test(**kwargs)
        t.name_testprogram = self.name_testprogram
        t.uuid_testprogram = self.uuid_testprogram
        t.name_testseries = self.name_testseries
        t.uuid_testseries = self.uuid_testseries
        t.project = self.project
        t.testtype = self.testtype
        t.metadata.add(self.SDATA_PARENT, self.uuid)

        return t

    @property
    def longname(self):
        return "_".join([self.name_testprogram, self.name])


class Test(TestSeries):
    """A sdata Test

    """

    SDATA_TESTSERIES_NAME = "!sdata_testseries_name"
    SDATA_TESTSERIES_UUID = "!sdata_testseries_uuid"

    def __init__(self, **kwargs):
        """Test

        :param kwargs:
        """
        TestSeries.__init__(self, **kwargs)
        self.metadata.add(name=self.SDATA_TESTSERIES_NAME, value="N.N.", dtype="str")
        self.metadata.add(name=self.SDATA_TESTSERIES_UUID, value="", dtype="str")

        if kwargs.get("name") is not None:
            self._set_name(kwargs.get("name"))
        else:
            self._set_name("N.N.")
        if kwargs.get("testtype") is not None:
            # print("testtype", kwargs.get("testtype"), self._set_testtype)
            self._set_testtype(kwargs.get("testtype"))
        if kwargs.get("name_testseries") is not None:
            self._set_name_testseries(kwargs.get("name_testseries"))
        if kwargs.get("uuid_testseries") is not None:
            self._set_uuid_testseries(kwargs.get("uuid_testseries"))
        if kwargs.get("name_testprogram") is not None:
            self._set_name_testprogram(kwargs.get("name_testprogram"))
        if kwargs.get("uuid_testprogram") is not None:
            # print("uuid_testprogram", kwargs.get("uuid_testprogram"), self._set_uuid_testprogram)
            self._set_uuid_testprogram(kwargs.get("uuid_testprogram"))

    def _get_uuid_testseries(self):
        return self.metadata.get(self.SDATA_TESTSERIES_UUID).value

    def _set_uuid_testseries(self, value):
        if isinstance(value, str):
            try:
                uuid.UUID(value)
                self.metadata.set_attr(self.SDATA_TESTSERIES_UUID, uuid.UUID(value).hex)
            except ValueError as exp:
                logger.warning("data.uuid: %s" % exp)
                raise Sdata_Uuid_Exeption("got invalid uuid str '{}'".format(str(value)))
        elif isinstance(value, uuid.UUID):
            self.metadata.set_attr(self.SDATA_TESTSERIES_UUID, value.hex)
        else:
            logger.error("Data.uuid: invalid uuid '{}'".format(value))
            raise Exception("Data.uuid: invalid uuid '{}'".format(value))

    uuid_testseries = property(fget=_get_uuid_testseries, fset=_set_uuid_testseries, doc="uuid of the testseries")

    def _get_name_testseries(self):
        return self.metadata.get(self.SDATA_TESTSERIES_NAME).value

    def _set_name_testseries(self, value):
        if isinstance(value, str):
            try:
                self.metadata.set_attr(self.SDATA_TESTSERIES_NAME, str(value)[:256])
            except ValueError as exp:
                logger.warning("data.name_testseries: %s" % exp)
        else:
            self.metadata.set_attr(self.SDATA_TESTSERIES_NAME, str(value)[:256])

    name_testseries = property(fget=_get_name_testseries, fset=_set_name_testseries, doc="name of the testseries")

    def _get_testtype(self):
        return self.metadata.get(self.SDATA_TESTTYPE).value

    def _set_testtype(self, value):
        if isinstance(value, str):
            try:
                self.metadata.set_attr(self.SDATA_TESTTYPE, str(value)[:256])
            except ValueError as exp:
                logger.warning("data.testtype: %s" % exp)
        else:
            self.metadata.set_attr(self.SDATA_TESTTYPE, str(value)[:256])

    testtype = property(fget=_get_testtype, fset=_set_testtype, doc="testtype of the testseries")

    @property
    def longname(self):
        return "_".join([self.name_testprogram, self.name_testseries, self.name])



__all__ = []
