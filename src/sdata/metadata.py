import logging
import collections
import pandas as pd
from sdata.timestamp import TimeStamp


class Attribute(object):
    """Attribute class"""

    DTYPES = {'float':float, 'int':int, 'str':str, 'timestamp':TimeStamp, 'bool':bool}

    def __init__(self, name, value, **kwargs):
        """Attribute
        :param name
        :param value
        :param dtype ['float', 'int', 'str', 'bool', 'timestamp', 'uuid?', 'unicode?']
        :param description
        :param dimension e.g. force, length, strain, count, energy
        :param unit

        """
        self._name = None
        self._value = None
        self._unit = "-"
        self._dimension = kwargs.get("dimension", "?")
        self._description = ""
        self._dtype = "str"
        self.name = name
        self.dtype = kwargs.get("dtype", "str")
        self.description = kwargs.get("description", "")
        self.unit = kwargs.get("unit", "-")
        #set dtype first!
        self.value = value

    def _get_name(self):
        return self._name
    def _set_name(self, value):
        if isinstance(value, str):
            try:
                value = value.strip()[:256]
                if len(value)>0:
                    self._name = value
                else:
                    raise ValueError("empty Attribute.name")
            except ValueError as exp:
                logging.warning("error Attribute.name: %s" % exp)
        else:
            self._name = str(value).strip()[:256]
    name = property(fget=_get_name, fset=_set_name, doc="Attribute name")

    def _get_value(self):
        return self._value
    def _set_value(self, value):
        try:
            dtype = self.DTYPES.get(self.dtype, str)
            if value is None:
                self._value = None
            elif dtype.__name__=="bool" and value in [0, "0", "False", "false"]:
                self._value = False
            elif dtype.__name__=="bool" and value in [1, "1", "true", "True"]:
                self._value = True
            else:
                self._value = dtype(value)
        except ValueError as exp:
            print("error Attribute.value: %s" % exp)
            logging.warning("error Attribute.value: %s" % exp)
    value = property(fget=_get_value, fset=_set_value, doc="Attribute value")

    def _get_dtype(self):
        return self._dtype
    def _set_dtype(self, value):
        if value in self.DTYPES.keys():
            self._dtype = value
    dtype = property(fget=_get_dtype, fset=_set_dtype, doc="Attribute type")

    def _get_description(self):
        return self._description
    def _set_description(self, value):
        self._description = value
    description = property(fget=_get_description, fset=_set_description, doc="Attribute description")

    def _get_unit(self):
        return self._unit
    def _set_unit(self, value):
        self._unit = value
    unit = property(fget=_get_unit, fset=_set_unit, doc="Attribute unit")

    def to_dict(self):
        """:returns dict of attribute items"""
        return {'name':self.name,
                'value':self.value,
                'unit':self.unit,
                'dtype':self.dtype,
                'description':self.description,
                }

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
        * type (int, str, float)
        """

    ATTRIBUTEKEYS = ["name", "value", "dtype", "unit", "description"]

    def __init__(self, **kwargs):
        """"""
        self._attributes = collections.OrderedDict()

    def _get_attributes(self):
        return self._attributes
    def _set_attributes(self, value):
        self._attributes = value
    attributes = property(fget=_get_attributes, fset=_set_attributes, doc="returns Attributes")

    def set_attr(self, name, value, **kwargs):
        """set Attribute"""
        attr = self.get_attr(name) or Attribute(name, value, **kwargs)
        for key in  ["dtype", "unit", "description"]:
            if key in kwargs:
                setattr(attr, key, kwargs.get(key))
        attr.value = value
        self._attributes[attr.name] = attr

    def get_attr(self, name):
        """get Attribute by name"""
        return self._attributes.get(name, None)

    def to_dict(self):
        """serialize attributes to dict"""
        d = {}
        for attr in self.attributes.values():
            d[attr.name]=attr.to_dict()
        return d

    def update_from_dict(self,d):
        """set attributes from dict"""
        for k,v in d.items():
            self.set_attr(**v)

    @classmethod
    def from_dict(cls,d):
        """setup metadata from dict"""
        metadata = cls()
        for k,v in d.items():
            metadata.set_attr(**v)
        return metadata

    def to_dataframe(self):
        """create dataframe"""
        d = self.to_dict()
        df = pd.DataFrame.from_dict(d, orient="index")
        return df[self.ATTRIBUTEKEYS]

    @classmethod
    def from_dataframe(cls, df):
        """create metadata from dataframe"""
        d = df.to_dict(orient='index')
        metadata = cls.from_dict(d)
        return metadata

    def to_csv(self, filepath):
        """serialize to csv"""
        try:
            df = self.to_dataframe()
            df.to_csv(filepath, index=None)
        except OSError as exp:
            logging.error("metadata.to_csv error: %s" % (exp))

    @classmethod
    def from_csv(cls, filepath):
        """create metadata from dataframe"""
        df = pd.read_csv(filepath)
        metadata = cls.from_dataframe(df)
        return metadata

    def __repr__(self):
        return "(Metadata:%d)" % (len(self.attributes))

    def __str__(self):
        return "(Metadata:%d %s)" % (len(self.attributes), [x for x in self.attributes])
