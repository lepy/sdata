# -*-coding: utf-8-*-
import logging
logger = logging.getLogger("sdata")
import pandas as pd
import numpy as np
from sdata.timestamp import TimeStamp
from sdata import __version__
import json
import os
import hashlib
import re
import copy
from sdata.contrib.sortedcontainers.sorteddict import SortedDict

def extract_name_unit(value):
    """extract name and unit from a combined string

    .. code-block:: python

        value: 'Target Strain Rate (1/s) '
        name : 'Target Strain Rate'
        unit : '1/s'

        value: 'Gauge Length [mm] monkey '
        name : 'Gauge Length'
        unit : 'mm'

        value: 'Gauge Length <mm> whatever '
        name : 'Gauge Length'
        unit : 'mm'

    :param value: string, e.g. 'Length <mm> whatever'
    :return: name, unit
    """
    pattern1 = r'([\w\s\.]+) \(([\w.-\/]+)\)'
    match1 = re.search(pattern1, value)
    pattern2 = r'([\w\s\.]+) \[([\w.-\/]+)\]'
    match2 = re.search(pattern2, value)
    pattern3 = r'([\w\s\.]+) \<([\w.-\/]+)\>'
    match3 = re.search(pattern3, value)
    if match1:
        name = match1.group(1)
        unit = match1.group(2)
    elif match2:
        name = match2.group(1)
        unit = match2.group(2)
    elif match3:
        name = match3.group(1)
        unit = match3.group(2)
    else:
        name = value
        unit = ""
    return name, unit

class Attribute(object):
    """Attribute class"""

    DTYPES = {'float': float, 'int': int, 'str': str, 'timestamp': TimeStamp, "bool": bool}
    DTYPES_INV = {v: k for k, v in DTYPES.items()}

    def __init__(self, name, value, **kwargs):
        """Attribute(name, value, dtype=str, unit="-", description="", label="", required=False)
        :param name
        :param value
        :param dtype ['float', 'int', 'str', 'timestamp', 'uuid?', 'unicode?']
        :param description
        :param dimension e.g. force, length, strain, count, energy
        :param unit
        :param label
        :param required
        """
        self._name = None
        self._value = None
        self._unit = "-"
        self._description = ""
        self._label = ""
        self._dtype = None
        self.name = name
        self._set_dtype(kwargs.get("dtype", None))
        self._set_description(kwargs.get("description", ""))
        self._set_label(kwargs.get("label", ""))
        self._set_unit(kwargs.get("unit", "-"))
        self._set_required(kwargs.get("required", False))
        # set dtype first!
        self._set_value(value)

    def _get_name(self):
        return self._name

    def _set_name(self, value):
        if isinstance(value, str):
            try:
                value = value.strip()[:256]
                if len(value) > 0:
                    self._name = value
                else:
                    raise ValueError("empty Attribute.name")
            except ValueError as exp:
                logger.warning("error Attribute.name: %s" % exp)
        else:
            self._name = str(value).strip()[:256]

    name = property(fget=_get_name, fset=_set_name, doc="Attribute name")

    def _get_value(self):
        return self._value

    def _set_value(self, value):
        try:
            dtype = self.DTYPES.get(self.dtype, self.guess_dtype(value))

            if self.dtype != dtype.__name__:
                # logger.debug("guess dtype for ``: ``".format(value, dtype.__name__))
                self.dtype = dtype.__name__

            if value == "" and self.dtype in ["str"]:
                self._value = ""
            elif not value and self.dtype not in ["int", "float", "bool"]:
                self._value = None
            elif not value and self.dtype in ["int", "float"]:
                self._value = np.nan
            elif pd.isna(value) and self.dtype in ["int", "float"]:
                self._value = np.nan
            elif dtype.__name__ == "bool" and value not in [1, "1", "true", "True"]:
                self._value = False
            elif dtype.__name__ == "bool" and value in [1, "1", "true", "True"]:
                self._value = True
            else:
                self._value = dtype(value)
        except ValueError as exp:
            logger.error("error Attribute.value: {}".format(exp))

    value = property(fget=_get_value, fset=_set_value, doc="Attribute value")

    @staticmethod
    def guess_dtype(value):
        """returns dtype class

        :param value:
        :return: __class__
        """
        if isinstance(value, (int)):
            return value.__class__
        elif isinstance(value, (float)):
            return value.__class__
        elif isinstance(value, (str)):
            return value.__class__
        else:
            return str

    def _get_dtype(self):
        return self._dtype

    def _set_dtype(self, value):
        """set dtype str
s
        :param value:
        :return:
        """
        if value is None:
            return None
        if value in self.DTYPES_INV.keys():
            value = self.DTYPES_INV.get(value, "str")
        elif "float" in value:
            value = "float"
        elif "int" in value:
            value = "int"
        if value in self.DTYPES.keys():
            self._dtype = value
        # todo: cast self.value to new dtype
        # if self._value is not None:
        #     try:
        #         self._value = self.DTYPES[self.dtype](self.value)
        #     except Exception as exp:
        #         logger.error("_set_dtype:{}:{}-{}".format(self.dtype, exp, exp.__class__.__name__))

    dtype = property(fget=_get_dtype, fset=_set_dtype, doc="Attribute type str")

    def _get_description(self):
        return self._description

    def _set_description(self, value):
        if value is None:
            value = ""
        self._description = str(value)

    description = property(fget=_get_description, fset=_set_description, doc="Attribute description")

    def _get_label(self):
        return self._label

    def _set_label(self, value):
        if value is None:
            value = ""
        self._label = str(value)

    label = property(fget=_get_label, fset=_set_label, doc="Attribute label")

    def _get_unit(self):
        return self._unit

    def _set_unit(self, value):
        self._unit = value

    unit = property(fget=_get_unit, fset=_set_unit, doc="Attribute unit")

    def _get_required(self):
        return self._required

    def _set_required(self, value):
        if value in [True, 1, "true", "True"]:
            self._required = True
        else:
            self._required = False

    required = property(fget=_get_required, fset=_set_required, doc="Attribute required")

    def to_dict(self):
        """:returns dict of attribute items"""
        return {'name': self.name,
                'value': self.value,
                'unit': self.unit,
                'dtype': self.dtype,
                'description': self.description,
                'label': self.label,
                'required': self.required,
                }

    def to_list(self):
        return [self.name, self.value, self.unit, self.dtype, self.description, self.label, self.required]

    def to_csv(self, prefix="", sep=",", quote=None):
        """export Attribute to csv

        :param prefix:
        :param sep:
        :param quote:
        :return:
        """
        xs = []
        for x in self.to_list():
            if x is None:
                xs.append("")
            else:
                xs.append(str(x))
        return "{}{}".format(prefix, sep.join(xs))

    def __str__(self):
        return "(Attr'%s':%s(%s))" % (self.name, self.value, self.dtype)

    __repr__ = __str__


class Metadata(object):
    """Metadata container class
    
    each Metadata entry has has a 
        * name (256)
        * value
        * unit
        * description
        * type (int, str, float, bool, timestamp)
        """

    ATTRIBUTEKEYS = ["name", "value", "unit", "dtype", "description", "label", "required"]

    def __init__(self, **kwargs):
        """Metadata class

        :param kwargs:
        """
        self._attributes = SortedDict()
        self._name = kwargs.get("name") or "N.N."

    def _get_name(self):
        return self._name

    def _set_name(self, value):
        self._name = str(value)

    name = property(fget=_get_name, fset=_set_name, doc="Name of the Metadata")

    def _get_attributes(self):
        return self._attributes

    def _set_attributes(self, value):
        self._attributes = value

    attributes = property(fget=_get_attributes, fset=_set_attributes, doc="returns Attributes")

    @property
    def user_attributes(self):
        attrs = [(a.name, a) for a in self.attributes.values() if not a.name.startswith("!sdata")]
        return SortedDict(attrs)

    @property
    def sdata_attributes(self):
        attrs = [(a.name, a) for a in self.attributes.values() if a.name.startswith("!sdata")]
        return SortedDict(attrs)

    @property
    def required_attributes(self):
        required_attributes = [(attr.name, attr) for attr in self.attributes.values() if attr.required is True]
        return SortedDict(required_attributes)

    def add_attribute(self, attr, **kwargs):
        """set Attribute"""
        prefix = kwargs.get("prefix", "")
        self._attributes[prefix + attr.name] = attr

    def set_attr(self, name="N.N.", value=None, **kwargs):
        """set Attribute"""
        prefix = kwargs.get("prefix", "")
        if isinstance(name, Attribute) or "Attribute" in name.__class__.__name__:
            attr = name # name is the Attribute!
        else:
            attr = self.get_attr(prefix + name) or Attribute(name, value, **kwargs)
        for key in ["unit", "dtype", "description", "label", "required"]:
            if key in kwargs:
                if key in kwargs:
                    # print("!!!", attr, key, kwargs.get(key))
                    setattr(attr, key, kwargs.get(key))
        if value is not None:
            attr.value = value
        self._attributes[prefix + attr.name] = attr

    def get_attr(self, name):
        """get Attribute by name"""
        return self._attributes.get(name, None)

    def to_dict(self):
        """serialize attributes to dict"""
        d = {}
        for attr in self.attributes.values():
            d[attr.name] = attr.to_dict()
        return d

    @staticmethod
    def guess_dtype_from_value(value):
        """guess dtype from value,
        e.g.
        '1.23' -> 'float'
        'otto1.23' -> 'str'
        1 -> 'int'
        False -> 'bool'

        :param value:
        :return: dtype(value), dtype ['int', 'float', 'bool', 'str']
        """
        if value.__class__.__name__ in ["int", "float", "bool"]:
            return value, value.__class__.__name__
        elif value in ["False", "True", "true", "false"]:
            return value, 'bool'
        try:
            value = int(value)
            return value, value.__class__.__name__
        except:
            pass
        try:
            value = float(value)
            return value, value.__class__.__name__
        except:
            pass
        return str(value), "str"

    def update_from_dict(self, d, guess_dtype=True):
        """set attributes from dict

        :param d: dict
        :return:
        """
        for k, v in d.items():
            if guess_dtype is False:
                value = v
                dtype = None
            else:
                value, dtype = self.guess_dtype_from_value(v)
            if dtype in ["float", "int", "bool"]:
                v = {"name":k, "value":value}
                # v = {"name":k, "value":value, "dtype":dtype, "unit":"", "description":"", "label":"", "required":False}
            elif isinstance(v, (str,)):
                v = {"name":k, "value":v, "dtype":"str", "unit":"", "description":"", "label":"", "required":False}
            elif hasattr(v, "keys"):
                dtype = v.get("dtype", self.guess_dtype_from_value(v.get("value"))[1])
                value = v.get("value")
                v = {"name":k, "value":value, "dtype":dtype,
                     "unit":v.get("unit", ""), "description":v.get("description", ""),
                     "label":v.get("label", ""), "required":v.get("required", False)}
            else:
                v, dtype = self.guess_dtype_from_value(v)
                # v = {"name":k, "value":v, "dtype":dtype, "unit":"", "description":"", "label":"", "required":False}
                v = {"name":k, "value":v, "dtype":dtype}
            self.set_attr(**v)

    @classmethod
    def from_dict(cls, d):
        """setup metadata from dict"""
        metadata = cls()
        metadata.update_from_dict(d)
        return metadata

    def _to_dict(self, attributes):
        """

        :param attributes:
        :return:
        """
        d = {}
        for attr in attributes.values():
            d[attr.name] = attr.to_dict()
        return d

    def get_sdict(self):
        """get sdata attribute as dict"""
        d = {}
        for attr in self.sdata_attributes.values():
            d[attr.name] = attr.value
        return d

    def get_udict(self):
        """get user attribute as dict"""
        d = {}
        for attr in self.user_attributes.values():
            d[attr.name] = attr.value
        return d

    def get_dict(self):
        """get user attribute as dict"""
        d = {}
        for attr in self.attributes.values():
            d[attr.name] = attr.value
        return d

    def _to_dataframe(self, attributes):
        """create dataframe from attributes"""
        d = self._to_dict(attributes)
        if len(d) == 0:
            df = pd.DataFrame(columns=self.ATTRIBUTEKEYS)
        else:
            df = pd.DataFrame.from_dict(d, orient="index")
        df.index.name = "key"
        return df[self.ATTRIBUTEKEYS]

    def to_dataframe(self):
        """create dataframe"""
        return self._to_dataframe(self.attributes)

    @property
    def df(self):
        """create dataframe"""
        return self._to_dataframe(self.attributes)

    @property
    def udf(self):
        """create dataframe for user attributes"""
        return self._to_dataframe(self.user_attributes)

    @property
    def dft(self):
        """create transposed dataframe for sdata attributes"""
        mt = self.df[["value"]].transpose(copy=True)
        mt.index = [self.get("!sdata_sname").value]
        return mt

    def get_dft(self, index_name=None):
        """create transposed dataframe for sdata attributes"""
        if index_name is None:
            index_name = "!sdata_sname"
        mt = self.df[["value"]].transpose(copy=True)
        mt.index = [self.get(index_name).value]
        return mt


    @property
    def sdf(self):
        """create dataframe for sdata attributes"""
        return self._to_dataframe(self.sdata_attributes)

    @property
    def sdft(self):
        """create transposed dataframe for sdata attributes"""
        mt = self.sdf[["value"]].transpose(copy=True)
        mt.index = [self.get("!sdata_uuid").value]
        return mt

    @classmethod
    def from_dataframe(cls, df):
        """create metadata from dataframe"""
        df["unit"] = df.unit.fillna("")
        df["label"] =df.label.fillna("")
        df["description"] =df.description.fillna("")
        d = df.to_dict(orient='index')
        metadata = cls.from_dict(d)
        return metadata

    def update_from_usermetadata(self, metadata):
        """update user metadata from metadata"""
        for attribute in metadata.user_attributes.values():
            self.add(attribute)

    def to_csv(self, filepath=None, sep=",", header=False):
        """serialize to csv"""
        try:
            df = self.to_dataframe()
            # df.to_csv(filepath, index=None, sep=sep)
            return df.to_csv(filepath, index=None, sep=sep, header=header)
        except OSError as exp:
            logger.error("metadata.to_csv error: %s" % (exp))

    def to_csv_header(self, prefix="#", sep=",", filepath=None):
        """serialize to csv"""
        try:
            lines = []
            for attr in self.attributes.values():
                lines.append(attr.to_csv(prefix=prefix, sep=sep)+"\n")

            alines = "".join(lines)
            if filepath:
                logger.info("export '{}'".format(filepath))
                with open(filepath, "w") as fh:
                    fh.write(alines)
            return alines
        except OSError as exp:
            logger.error("metadata.to_csv error: %s" % (exp))

    @classmethod
    def from_csv(cls, filepath):
        """create metadata from dataframe"""
        df = pd.read_csv(filepath, header=None)
        df.columns = cls.ATTRIBUTEKEYS
        df.set_index(df.name.values, inplace=True)
        metadata = cls.from_dataframe(df)
        return metadata

    def to_json(self, filepath=None):
        """create a json

        :param filepath: default None
        :return: json str
        """
        d = self.to_dict()
        if filepath:
            with open(filepath, "w") as fh:
                json.dump(d, fh)
        return json.dumps(d)

    @classmethod
    def from_json(cls, jsonstr=None, filepath=None):
        """create metadata from json file

        :param jsonstr: json str
        :param filepath: filepath to json file
        :return: Metadata
        """

        if filepath is not None and os.path.exists(filepath):
            with open(filepath, "r") as fh:
                j = json.load(fh)
            metadata = cls.from_dict(j)
        elif jsonstr is not None:
            j = json.loads(jsonstr)
            metadata = cls.from_dict(j)
        return metadata

    def to_list(self):
        """create a nested list of Attribute values

        :return: list
        """
        return self.df.values.tolist()

    @classmethod
    def from_list(cls, mlist):
        """create metadata from a list of Attribute values

        [['force_x', 1.2, 'kN', 'float', 'force in x-direction'],
         ['force_y', 3.1, 'N', 'float', 'force in y-direction', 'label', True]]
         """
        metadata = cls()
        for alist in mlist:
            if len(alist) < 2:
                logger.error("Metadata.from_list skip {}".format(alist))
            else:
                alist.extend(["", "", "", "", ""])
                #["name", "value", "unit", "dtype", "description", "label", "required"]
                metadata.add(alist[0], alist[1], unit=alist[2], dtype=alist[3], description=alist[4],
                             label=alist[5], required=alist[6])
        return metadata

    def __repr__(self):
        return "(Metadata'%s':%d)" % (self.name, len(self.attributes))

    def __str__(self):
        return "(Metadata'%s':%d %s)" % (self.name, len(self.attributes), [x for x in self.attributes])

    def add(self, name, value=None, **kwargs):
        """add Attribute

        :param name:
        :param value:
        :param kwargs:
        :return:
        """
        self.set_attr(name, value, **kwargs)

    def relabel(self, name, newname):
        """relabel Attribute

        :param name: old attribute name
        :param newname: new attribute name
        :return: None
        """
        attr = self.get(name)
        if not attr:
            logger.warning("{0}: no Attribute {1} to relabel.".format(self.__class__, name))
        else:
            attr.name = newname
            self.attributes.pop(name)
            self.add(attr)

    def get(self, name, default=None):
        if self._attributes.get(name) is not None:
            return self._attributes.get(name)
        else:
            return default

    def keys(self):
        """

        :return: list of Attribute names
        """
        return list(self._attributes.keys())

    def values(self):
        """

        :return: list of Attribute values
        """
        return list(self._attributes.values())

    def items(self):
        """

        :return: list of Attribute items (keys, values)
        """
        return list(self._attributes.items())


    def copy(self):
        """returns a deep copy"""
        return copy.deepcopy(self)

    @property
    def size(self):
        """return number uf Attribute"""
        return len(self.attributes)

    def __getitem__(self, name):
        return self.get(name)

    def __setitem__(self, name, value):
        """update value in Attribute or create new Attribute"""
        attr = self.get(name)

        if attr is None:
            attr = Attribute(name=name, value=value, dtype=type(value).__name__)
            self._attributes[attr.name] = attr
        else:
            dtype = attr.guess_dtype(value)
            attr.dtype = dtype
            attr.value = dtype(value)

    def __contains__(self, item):
        return item in self.attributes.keys()

    def pop(self, item):
        try:
            return self._attributes.pop(item)
        except KeyError as exp:
            return None

    def __iter__(self):
        for x in self.attributes.items():
            yield x

    @property
    def sha3_256(self):
        """Return a new SHA3 hash object with a hashbit length of 32 bytes.

        :return: hashlib.sha3_256.hexdigest()
        """
        s = hashlib.sha3_256()
        metadatastr = self.to_json().encode(errors="replace")
        s.update(metadatastr)
        return s.hexdigest()

    def update_hash(self, hashobject):
        """A hash represents the object used to calculate a checksum of a
        string of information.

        .. code-block:: python

            hashobject = hashlib.sha3_256()
            metadata = Metadata()
            metadata.update_hash(hashobject)
            hash.hexdigest()

        :param hash: hash object
        :return: hash_function().hexdigest()
        """
        if not (hasattr(hashobject, "update") and hasattr(hashobject, "hexdigest")):
            logger.error("Metadata.hash: given hashfunction is invalid")
            raise Exception("Metadata.hash: given hashfunction is invalid")

        metadatastr = self.to_json().encode(errors="replace")
        hashobject.update(metadatastr)
        return hash

    def set_unit_from_name(self, add_description=True, fix_name=True):
        """try to extract unit from attribute name

        :return:
        """
        for attr in self.user_attributes.values():
            new_name, unit = extract_name_unit(attr.name)
            attr.unit = unit
            if add_description is True and len(attr.description)==0 and len(unit)>0:
                attr.description = attr.name
            if fix_name is True:
                self.relabel(attr.name, new_name)

    def guess_value_dtype(self):
        """try to cast the Attribute values, e.g. str -> float

        :return:
        """
        for attr in list(self.user_attributes.values()):
            for dtype in [float, str]:
                try:
                    # attr.value = dtype(attr.value)
                    # attr.dtype = dtype.__name__
                    self.add(name=attr.name, value=dtype(attr.value), dtype=dtype.__name__)
                    # print(["ok", attr.name, attr.value, self.get(attr.name).value])
                    break
                except (ValueError, TypeError) as exp:
                    pass
                    # print([attr.name, attr.value, dtype, exp])

    def is_complete(self):
        """check all required attributes"""
        required_attributes = self.required_attributes.values()
        for attr in required_attributes:
            if attr.value is None or attr.value=="":
                return False

        return True