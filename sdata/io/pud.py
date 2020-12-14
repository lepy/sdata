# -*- coding: utf-8 -*-

import logging
logger = logging.getLogger("sdata")
import os
import uuid
import numpy as np
import pandas as pd
from sdata.io import PID
from sdata import Data

class Pud(Data):
    """run object, e.g. single tension test simulation"""

    ATTRIBUTES = ["material_norm_name",
                  "material_number_norm",
                  "material_name",
                  "test",
                  "sample_ident_number",
                  "sample_geometry",
                  "sample_direction",
                  "nominal_pre_deformation <%>",
                  "actual_pre_deformation <%>",
                  "direction_of_pre_deformation",
                  "heat_treatment",
                  "actual_sample_width_<mm>",
                  "actual_sample_thickness_<mm>",
                  "actual_gauge_length_<mm>",
                  "nominal_testing_temperature_<K>",
                  "nominal_testing_speed_<m/s>",
                  "order",
                  "date_of_test_<dd.mm.yyyy>",
                  "tester",
                  "place_of_test",
                  "remark",
                  "data",
                  ]

    def __init__(self, **kwargs):
        """"""
        Data.__init__(self, **kwargs)
        # for attr in self.ATTRIBUTES:
        #     self.set_attr(attr, None)


    @classmethod
    def from_file(cls, filepath):
        """read pud file

            .. code-block:: none

                WERKSTOFF_NORM_NAME                    = HC340LA
                WERKSTOFFNUMMER_NORM                   =
                MATERIALNAME                           = HC340LA
                PRUEFUNG                               = FLIESSKURVE
                PROBENIDENTNUMMER                      = id0815
                PROBENGEOMETRIE                        =
                ENTNAHMERICHTUNG                       = Quer (90deg)
                VORVERFORMUNG_SOLL <%>                 = 0
                VORVERFORMUNG_IST  <%>                 =
                VORVERFORMUNGSRICHTUNG                 = Unverformt
                WAERMEBEHANDLUNG                       = O
                PROBENBREITE_IST <mm>                  = 20.014
                PROBENDICKE_IST <mm>                   = 0.751
                MESSLAENGE_IST <mm>                    = 80.0
                MESSLAENGE_IST_FD <mm>                 = 80.0
                PRUEFTEMPERATUR_SOLL <K>               = 293
                PRUEFGESCHWINDIGKEIT_SOLL  <mm/s>      = 0.32
                PRUEFGESCHWINDIGKEIT_IST   <mm/s>      = 0.32
                DEHNRATE_SOLL <1/s>                    = 0.004
                DEHNRATE_IST  <1/s>                    = 0.004
                AUFTRAG                                =
                PRUEFDATUM  <tt.mm.jjjj>               = 19.03.2017
                PRUEFER                                = Otto
                PRUEFSTELLE                            = SALZGITTER AG
                BEMERKUNG                              = ASL 2009-056
                DATEN                                  =
                ZEIT <s>; KRAFT <N>; WEG <mm>; BREITENAENDERUNG <mm>; WEG_FD <mm>
                1.2372;192.181;-0.0235;0.0012;-0.0235
                1.2772;198.325;-0.0231;0.0012;-0.0231
                1.2972;201.397;-0.0227;0.0012;-0.0227
                1.3172;205.152;-0.0224;0.0013;-0.0224
                1.3572;211.638;-0.022;0.0013;-0.022
                1.3972;218.123;-0.0213;0.0013;-0.0213
        """

        if not os.path.exists(filepath):
            raise Exception("File not exists '{}'".format(filepath))

        filename = os.path.split(filepath)[-1]
        tt = cls(name=filename.upper().replace(".TXT", ""))

        df = None
        # https://docs.python.org/2/library/codecs.html#standard-encodings
        for encoding in ['ISO-8859-1', "ascii", "utf-8", "iso8859_1", "latin1", 'ISO-8859-1', 'cp1252', "iso8859_2", ]:

            try:
                logging.debug("try {}".format(encoding))
                df = pd.read_csv(filepath, encoding=encoding, sep="=", header=None)
                if df is not None:
                    break
            except:
                pass

        startindex = df[df[0].str.startswith("DATEN")].iloc[0].name + 1
        attributes = df.loc[:startindex - 2]
        attributes.columns = ["key", "value"]

        table = {
            0xe4     : u'ae',
            ord(u'ö'): u'oe',
            ord(u'ü'): u'ue',
            ord(u'ß'): u'ss',
            ord(u'Ä'): u'AE',
            ord(u'Ö'): u'OE',
            ord(u'Ü'): u'UE',
            ord(u'ß'): u'SS',
        }

        for row, attr in attributes.iterrows():
            s = attr.key  # .decode('utf8')
            attr.key = s.translate(table)
            try:
                tt.metadata.set_attr(attr.key.strip(), attr.value.strip())
            except AttributeError as exp:
                tt.metadata.set_attr(attr.key.strip(), attr.value)
            except UnicodeEncodeError as exp:
                print("UnicodeEncodeError {}".format(attr.key))
                raise

        table = df.loc[startindex:].copy()
        table = table[0].str.split(";", expand=True)
        table.columns = [x.strip() for x in table.iloc[0].values]
        table = table.drop(index=startindex)
        for col in table.columns:
            table[col] = table[col].astype(float)

        if 'KRAFT <kN>' in table.columns:
            table['KRAFT <N>'] = table['KRAFT <kN>'] * 1e3

        # print(table)
        # print(attributes)
        # mapper={"Kraft <N>":"force",
        #    'Weg <mm>':"displacement",
        #    "Zeit <s>":"time",
        #    "Breitenaenderung <mm>":"displacement_y",
        #     "KRAFT <N>":"force",
        #    'WEG <mm>':"displacement",
        #    "ZEIT <s>":"time",
        #    "BREITENAENDERUNG <mm>":"displacement_y"}
        #
        # table = table.rename(columns=mapper)

        attr = tt.metadata.get("PROBENIDENTNUMMER")
        tt.uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(attr.name.upper()))

        tt.table = table

        l0 = tt.metadata.get('MESSLAENGE_IST <mm>', np.nan)
        width = tt.metadata.get('PROBENBREITE_IST <mm>', np.nan)
        thickness = tt.metadata.get('PROBENDICKE_IST <mm>', np.nan)
        actual_testing_temperature = tt.metadata.get('PRUEFTEMPERATUR_SOLL <K>', np.nan)
        sample_direction = tt.metadata.get('ENTNAHMERICHTUNG', np.nan)
        nominal_pre_deformation = tt.metadata.get('VORVERFORMUNG_SOLL <%>', np.nan)
        actual_pre_deformation = tt.metadata.get('VORVERFORMUNG_IST  <%>', np.nan)
        nominal_strain_rate = tt.metadata.get('DEHNRATE_SOLL <1/s>', np.nan)
        actual_strain_rate = tt.metadata.get('DEHNRATE_IST  <1/s>', np.nan)
        place_of_test = tt.metadata.get('PRUEFSTELLE', np.nan)

        mapper = {"Kraft <N>"            : "force",
                  'Weg <mm>'             : "displacement",
                  "Zeit <s>"             : "time",
                  "Breitenaenderung <mm>": "displacement_y",
                  "KRAFT <N>"            : "force",
                  'WEG <mm>'             : "displacement",
                  "ZEIT <s>"             : "time",
                  "BREITENAENDERUNG <mm>": "displacement_y"}

        try:
            l0 = float(l0)
        except Exception as exp:
            l0 = np.nan

        try:
            width = float(width)
        except Exception as exp:
            width = np.nan

        try:
            thickness = float(thickness)
        except Exception as exp:
            thickness = np.nan

        try:
            actual_testing_temperature = float(actual_testing_temperature)
        except Exception as exp:
            actual_testing_temperature = np.nan

        try:
            sample_direction = tt.metadata.get_orientation(sample_direction)
        except Exception as exp:
            sample_direction = np.nan

        try:
            nominal_pre_deformation = float(nominal_pre_deformation) / 100.
        except Exception as exp:
            nominal_pre_deformation = np.nan

        try:
            actual_pre_deformation = float(actual_pre_deformation) / 100.
        except Exception as exp:
            actual_pre_deformation = np.nan

        try:
            nominal_strain_rate = float(nominal_strain_rate)
        except Exception as exp:
            nominal_strain_rate = np.nan

        try:
            actual_strain_rate = float(actual_strain_rate)
        except Exception as exp:
            actual_strain_rate = np.nan

        # try:
        #     place_of_test = str(place_of_test)
        # except Exception as exp:
        #     place_of_test = "?"hash

        area = width * thickness
        tt.metadata.set_attr("l0", l0)
        tt.metadata.set_attr("width", width)
        tt.metadata.set_attr("thickness", thickness)
        tt.metadata.set_attr("area", area)
        tt.metadata.set_attr("actual_testing_temperature", actual_testing_temperature)
        tt.metadata.set_attr("sample_direction", sample_direction)
        tt.metadata.set_attr("nominal_pre_deformation", nominal_pre_deformation)
        tt.metadata.set_attr("actual_pre_deformation", actual_pre_deformation)
        tt.metadata.set_attr("nominal_strain_rate", nominal_strain_rate)
        tt.metadata.set_attr("actual_strain_rate", actual_strain_rate)
        tt.metadata.set_attr("place_of_test", place_of_test)

        return tt
