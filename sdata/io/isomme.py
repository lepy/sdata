# -*- coding: utf-8 -*-
import os
import sys
import re
import logging
import copy
import numpy as np
import pandas as pd

class ISOMMEError(Exception): pass

class Isomme:
    """isomme object"""

    CHANNEL = "CHANNEL"
    DIAGRAM = "DIAGRAM"
    DOCUMENT = "DOCUMENT"
    MOVIE = "MOVIE"
    PHOTO = "PHOTO"
    REPORT = "REPORT"
    STATIC = "STATIC"

    def __init__(self, name=None):
        """isomme"""
        self.ISOSTANDARD = "ISO/TS 13499 (2005)"
        self._channels = []
        self.mmeinfo = {}
        # self.mme = MME()
        self.path = None
        if name is None:
            self.name = "Sxxxx_xx"
        else:
            self.name = str(name)

    @classmethod
    def from_sdata(cls, data):
        """

        :param data: sdata.Data
        :return:
        """
        iso = cls(name=data.name)
        for col in data.df.columns:
            channel = Channel(cid=col, data=data.df[col])
            iso.add_channel(channel)
        return iso

    @property
    def channels(self):
        return self._channels

    def add_channel(self, channel):
        """add channel to channel list"""
        channelcode = channel.get_code()
        logging.debug("add channel '%s'" % channelcode)
        self._channels.append(channel)

    def export(self, exportpath, mmeinfo=None, createall=False):
        """

        :param exportpath:
        :param mmeinfo:
        :param createall:
        :return:
        """
        try:
            # exportpath = os.path.join(path, versuch)
            self._genMMEFolder(exportpath, createall=createall)
            self._exportChannels(exportpath)
            self._exportChnFile(exportpath)
            # self.mme.export(exportpath, self.name)
            # if zip is True:
            #     # files = self.get_files(exportpath, versuch)
            #     ret = self.export_zip(exportpath, versuch)
        except (IOError, OSError) as exp:
            logging.warning("could not export isomme structure (%s)" % str(exp))
            return False
        return True

    def _exportChannels(self, exportpath):
        logging.info("start channel export (%d channels)" % len(self._channels))
        channelpath = os.path.join(exportpath, self.CHANNEL)
        for cid, channel in enumerate(self._channels):
            path = os.path.join(exportpath, self.CHANNEL, self.name + ".%03d" % (cid + 1))
            logging.debug("generate %s for %s" % (path, channel.cid))
            para = {}
            channel.update_para(para)
            channel.export(path)
        logging.debug("finish channel export")

    def _genMMEFolder(self, exportpath, createall=False):
        """generate isomme-subfolder"""
        if createall is True:
            folders = [self.CHANNEL, self.DIAGRAM, self.DOCUMENT, self.MOVIE, self.PHOTO, self.REPORT, self.STATIC]
        else:
            folders = [self.CHANNEL]
        for folder in folders:
            path = os.path.join(exportpath, folder)
            if not os.path.exists(path):
                os.makedirs(path)

    def _exportChnFile(self, exportpath):
        """This file contains general information concerning the test channels. Each item shall be separated by a
“carriage return” and a “line feed” (CR/LF). Each line may comprise up to 80 characters."""
        filepath = os.path.join(exportpath, self.CHANNEL, "%s.chn" % self.name)
        try:
            fil = open(filepath, "w")
            fil.write("Instrumentation standard    :%s\n" % self.ISOSTANDARD)
            fil.write("Number of channels          :%d\n" % len(self._channels))
            for cid, channel in enumerate(self._channels):
                channelname = channel.para["CHANNEL_CODE"]
                # in chn file nur channel codes auflisten!
                # if channel.para["CUSTOMER_CHANNEL_CODE"] is not None and len(channel.para["CUSTOMER_CHANNEL_CODE"])>0:
                #     channelname = channel.para["CUSTOMER_CHANNEL_CODE"]
                fil.write(("Name of channel %03d         :%s\n" % (cid + 1, channelname)))
            fil.close()
        except IOError as exp:
            print("Chn-Error: %s-%s" % (exp.__class__.__name__, exp))
        except OSError as exp:
            print("Chn-Error: %s-%s" % (exp.__class__.__name__, exp))

class Channel:
    """channel object"""

    NOVALUE = "NOVALUE"
    NOCOMMENTS = "NO COMMENTS"

    TEST_OBJECT_NUMBER = "TEST_OBJECT_NUMBER"
    NAME_OF_THE_CHANNEL = "NAME_OF_THE_CHANNEL"
    LABORATORY_CHANNEL_CODE = "LABORATORY_CHANNEL_CODE"
    CUSTOMER_CHANNEL_CODE = "CUSTOMER_CHANNEL_CODE"
    CHANNEL_CODE = "CHANNEL_CODE"
    COMMENTS = "COMMENTS"
    LOCATION = "LOCATION"
    DIRECTION = "DIRECTION"
    DIMENSION = "DIMENSION"
    CHANNEL_FREQUENCY_CLASS = "CHANNEL_FREQUENCY_CLASS"
    UNIT = "UNIT"
    REFERENCE_SYSTEM = "REFERENCE_SYSTEM"
    TRANSDUCER_TYPE = "TRANSDUCER_TYPE"
    PRE_FILTER_TYPE = "PRE_FILTER_TYPE"
    CUT_OFF_FREQUENCY = "CUT_OFF_FREQUENCY"
    CHANNEL_AMPLITUDE_CLASS = "CHANNEL_AMPLITUDE_CLASS"
    SAMPLING_INTERVAL = "SAMPLING_INTERVAL"
    BIT_RESOLUTION = "BIT_RESOLUTION"
    TIME_OF_FIRST_SAMPLE = "TIME_OF_FIRST_SAMPLE"
    NUMBER_OF_SAMPLES = "NUMBER_OF_SAMPLES"
    REFERENCE_CHANNEL = "REFERENCE_CHANNEL"
    REFERENCE_CHANNEL_NAME = "REFERENCE_CHANNEL_NAME"
    DATA_SOURCE = "DATA_SOURCE"
    DATA_STATUS = "DATA_STATUS"
    FIRST_GLOBAL_MAXIMUM_VALUE = "FIRST_GLOBAL_MAXIMUM_VALUE"
    TIME_OF_MAXIMUM_VALUE = "TIME_OF_MAXIMUM_VALUE"
    FIRST_GLOBAL_MINIMUM_VALUE = "FIRST_GLOBAL_MINIMUM_VALUE"
    TIME_OF_MINIMUM_VALUE = "TIME_OF_MINIMUM_VALUE"
    START_OFFSET_INTERVAL = "START_OFFSET_INTERVAL"
    END_OFFSET_INTERVAL = "END_OFFSET_INTERVAL"

    DATA_SOURCES = {"transducer": "Channel data has been generated by transducer",
                    "calculation": "Channel data has been calculated from other channels",
                    "camera": "Channel data has been generated by film analysis",
                    "simulation": "Channel data has been generated by simulation",
                    "parameter": "Channel data can be constant or limit curve",
                    }

    DATA_STATUSE = ["ok",
                    "channel failed",
                    "meaningless data",
                    "no data",
                    "questionable data",
                    "scaling factor applied",
                    "system failed",
                    "linearised data",
                    "NOVALUE",
                    ]

    PARAMETER_FLOAT = [SAMPLING_INTERVAL,
                       CUT_OFF_FREQUENCY,
                       BIT_RESOLUTION,
                       TIME_OF_FIRST_SAMPLE,
                       ]

    PARAMETER_INT = [TEST_OBJECT_NUMBER,
                     NUMBER_OF_SAMPLES,
                     FIRST_GLOBAL_MAXIMUM_VALUE,
                     TIME_OF_MAXIMUM_VALUE,
                     FIRST_GLOBAL_MINIMUM_VALUE,
                     TIME_OF_MINIMUM_VALUE,
                     START_OFFSET_INTERVAL,
                     END_OFFSET_INTERVAL,
                     ]

    ##TODO: Test para
    REFERENCE_CHANNELS = {
        "implicit": "Time reference is given with the descriptor values 'Time of first sample' and 'Sampling interval'",
        "explicit": "Explicit time channel exists in test data. Channel name is given with the descriptor 'Reference channel name'",
        "NOVALUE": "No time reference is available. For example in case of constant channels (filter class 'X')."
        }

    channeltemplate = """Test object number          :%(TEST_OBJECT_NUMBER)s
Name of the channel         :%(NAME_OF_THE_CHANNEL)s
Laboratory channel code     :%(LABORATORY_CHANNEL_CODE)s
Customer channel code       :%(CUSTOMER_CHANNEL_CODE)s
Channel code                :%(CHANNEL_CODE)s
Comments                    :%(COMMENTS)s
Location                    :%(LOCATION)s
Direction                   :%(DIRECTION)s
Dimension                   :%(DIMENSION)s
Channel frequency class     :%(CHANNEL_FREQUENCY_CLASS)s
Unit                        :%(UNIT)s
Reference system            :%(REFERENCE_SYSTEM)s
Transducer type             :%(TRANSDUCER_TYPE)s
Pre-filter type             :%(PRE_FILTER_TYPE)s
Cut off frequency           :%(CUT_OFF_FREQUENCY)s
Channel amplitude class     :%(CHANNEL_AMPLITUDE_CLASS)s
Sampling interval           :%(SAMPLING_INTERVAL)s
Bit resolution              :%(BIT_RESOLUTION)s
Time of first sample        :%(TIME_OF_FIRST_SAMPLE)s
Number of samples           :%(NUMBER_OF_SAMPLES)s
Reference channel           :%(REFERENCE_CHANNEL)s
Reference channel name      :%(REFERENCE_CHANNEL_NAME)s
Data source                 :%(DATA_SOURCE)s
Data status                 :%(DATA_STATUS)s
First global maximum value  :%(FIRST_GLOBAL_MAXIMUM_VALUE)s
Time of maximum value       :%(TIME_OF_MAXIMUM_VALUE)s
First global minimum value  :%(FIRST_GLOBAL_MINIMUM_VALUE)s
Time of minimum value       :%(TIME_OF_MINIMUM_VALUE)s
Start offset interval       :%(START_OFFSET_INTERVAL)s
End offset interval         :%(END_OFFSET_INTERVAL)s
"""
    defaultpara = {
        TEST_OBJECT_NUMBER: NOVALUE,
        NAME_OF_THE_CHANNEL: NOVALUE,
        LABORATORY_CHANNEL_CODE: NOVALUE,
        CUSTOMER_CHANNEL_CODE: NOVALUE,
        CHANNEL_CODE: NOVALUE,
        COMMENTS: NOCOMMENTS,
        LOCATION: NOVALUE,
        DIRECTION: NOVALUE,
        DIMENSION: NOVALUE,
        CHANNEL_FREQUENCY_CLASS: NOVALUE,
        UNIT: 1,
        REFERENCE_SYSTEM: NOVALUE,
        TRANSDUCER_TYPE: NOVALUE,
        PRE_FILTER_TYPE: NOVALUE,
        CUT_OFF_FREQUENCY: NOVALUE,
        CHANNEL_AMPLITUDE_CLASS: NOVALUE,
        SAMPLING_INTERVAL: NOVALUE,
        BIT_RESOLUTION: NOVALUE,
        TIME_OF_FIRST_SAMPLE: NOVALUE,
        NUMBER_OF_SAMPLES: NOVALUE,
        REFERENCE_CHANNEL: NOVALUE,
        REFERENCE_CHANNEL_NAME: NOVALUE,
        DATA_SOURCE: NOVALUE,
        DATA_STATUS: NOVALUE,
        FIRST_GLOBAL_MAXIMUM_VALUE: NOVALUE,
        TIME_OF_MAXIMUM_VALUE: NOVALUE,
        FIRST_GLOBAL_MINIMUM_VALUE: NOVALUE,
        TIME_OF_MINIMUM_VALUE: NOVALUE,
        START_OFFSET_INTERVAL: NOVALUE,
        END_OFFSET_INTERVAL: NOVALUE,
    }

    def __init__(self, cid, data=None, para=None):
        """Channel id"""

        self.cid = cid
        self.para = copy.deepcopy(Channel.defaultpara)
        self.para["DATA_SOURCE"] = "sdata"
        self.para["CHANNEL_FREQUENCY_CLASS"] = "0"

        self.para["NAME_OF_THE_CHANNEL"] = str(cid)

        if data is not None:
            self.data = data
            self.data.name = cid
            self.para["TIME_OF_FIRST_SAMPLE"] = self.data.index[0]
            try:
                dt = np.diff(c.data.index.values).mean()
                self.para["SAMPLING_INTERVAL"] = dt
            except:
                self.para["SAMPLING_INTERVAL"] = 1.
        else:
            self.data = pd.Series(name=cid)
        self.update_para(para)
        self.comments = []

        self.para["FIRST_GLOBAL_MAXIMUM_VALUE"] = self.data.max()
        self.para["FIRST_GLOBAL_MINIMUM_VALUE"] = self.data.min()
        self.para["TIME_OF_MAXIMUM_VALUE"] = self.data.idxmax()
        self.para["TIME_OF_MINIMUM_VALUE"] = self.data.idxmin()

    def __repr__(self):
        return "(%s(%s)|%d)" % (self.cid, self.para["NAME_OF_THE_CHANNEL"], len(self.data))

    __str__ = __repr__

    def add_comment(self, comment):
        self.comments += [comment]

    def update_para(self, para):
        if not para:
            return
        if "DATA_STATUS" in para and not any(para["DATA_STATUS"] == x for x in self.DATA_STATUSE):
            self.logger.warn("invalid DATA_STATUS '%s'" % (para["DATA_STATUS"]))
        if "DATA_SOURCE" in para and not any(para["DATA_SOURCE"] == x for x in self.DATA_SOURCES):
            self.logger.warn("invalid DATA_SOURCE '%s'" % (para["DATA_SOURCE"]))
        if para:
            self.para.update(para)

        if self.para.get("CUSTOMER_CHANNEL_CODE") is None or len(self.para.get("CUSTOMER_CHANNEL_CODE")) == 0:
            self.para["CUSTOMER_CHANNEL_CODE"] = self.para.get("CHANNEL_CODE")
        if self.para.get("LABORATORY_CHANNEL_CODE") is None or len(self.para.get("LABORATORY_CHANNEL_CODE")) == 0:
            self.para["LABORATORY_CHANNEL_CODE"] = self.para.get("CHANNEL_CODE")

    def get_code(self):
        for i in ["CHANNEL_CODE", "CUSTOMER_CHANNEL_CODE", "LABORATORY_CHANNEL_CODE", "NAME_OF_THE_CHANNEL"]:
            if self.para[i] != self.NOVALUE:
                return self.para[i]

    def export(self, filepath=None):
        code = self.get_code()
        logging.info("export channel %s" % (self.cid))
        self.para.update({
            "NUMBER_OF_SAMPLES": "%d" % len(self.data),
        })

        # # fix para
        # for k, v in self.para.items():
        #     if isinstance(v, str):
        #         self.para[k] = v#.decode("utf-8", "ignore")

        output = self.channeltemplate % self.para
        for comment in self.comments:
            output += "Comments                    :%s\n" % comment
        for x in self.data:
            # output += "%20.6E\n" % x
            output += "{:+.6e}\n".format(x)

        if filepath:
            try:
                fil = open(filepath, "w")
                fil.write(output)
                fil.close()
            except IOError as exp:
                logging.warning("Channel-Error: %s-%s" % (exp.__class__.__name__, exp))
            except OSError as exp:
                logging.warning("Channel-Error: %s-%s" % (exp.__class__.__name__, exp))
        return output

    def _import_channel(self, filepath):
        """path"""
        self.logger.debug("try to import Channel '%s'" % filepath)
        with open(filepath) as fh:
            self.parse(fh)
        self.logger.info("Channel '%s' imported" % self.get_code())

    def parse(self, fh):
        for line in fh:
            try:
                self.data.append(float(line))
            except ValueError:
                self._tryToReadParameter(line)

    def _raw_import_channel(self, filepath):
        """read str"""
        self.logger.debug("try to raw import Channel '%s'" % filepath)
        self.is_raw = True
        with open(filepath) as fh:
            self.raw_data = fh.read()
        self._import_channel(filepath)

    def _tryToReadParameter(self, line):
        line = line.rstrip("\n")
        seppos = line.find(":")
        key = line[:seppos]
        value = line[seppos + 1:].strip()
        ikey = key.strip().upper().replace(" ", "_")
        #        print key, value, ikey
        if ikey in self.defaultpara:
            if ikey in self.PARAMETER_FLOAT:
                try:
                    value = float(value)
                except:
                    pass
            elif ikey in self.PARAMETER_INT:
                try:
                    value = int(value)
                except:
                    pass
            if ikey.upper() == "COMMENTS" and self.para[ikey] != self.NOCOMMENTS:
                self.add_comment(value)
            else:
                self.para[ikey] = value


if __name__ == '__main__':
    s = pd.Series(data=[1., 2., 3.], name="otto")

    c = Channel(cid="otto", data=s)
    print(c)
    print(c.cid)
    print(c.data)
    print(c.data.describe())
    print(c.get_code())
    print(c.para)
    print(np.diff(c.data.index.values).mean())
    print(c.export())
    print(c.export(filepath="/tmp/c.001"))

