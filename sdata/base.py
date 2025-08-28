import sdata
from sdata import __version__
from sdata.suuid import SUUID
from sdata.metadata import Metadata, Attribute, extract_name_unit
from sdata.timestamp import now_utc_str, now_local_str, today_str
import uuid
import logging

logger = logging.getLogger(__name__)

class SdataUuidException(Exception):
    pass

class Base:

    SDATA_VERSION = "_sdata_version"
    SDATA_CLASS = "_sdata_class"
    SDATA_NAME = "_sdata_name"
    SDATA_SNAME = "_sdata_sname"
    SDATA_SUUID = "_sdata_suuid"
    SDATA_PARENT_SUUID = "_sdata_parent_suuid"
    SDATA_PROJECT_SUUID = "_sdata_project_suuid"
    SDATA_URL = "_sdata_url"

    SDATA_ATTRIBUTES = [SDATA_VERSION, SDATA_NAME, SDATA_SUUID, SDATA_CLASS,
                        SDATA_PARENT_SUUID, SDATA_PROJECT_SUUID, SDATA_URL]

    def __init__(self, **kwargs):
        name = kwargs.get("name", "N.N.")
        if not name:
            raise ValueError("Name cannot be empty")
        suuid = SUUID.from_name(class_name=self.__class__.__name__, name=name)
        self.default_attributes = []
        self.metadata = Metadata(name=suuid.sname)
        self.metadata.add(self.SDATA_VERSION, __version__, dtype="str", description="sdata package version")
        self.metadata.add(self.SDATA_NAME, name, dtype="str", description="name of the data object")
        self.metadata.add(self.SDATA_SNAME, suuid.sname, dtype="str", description="sname of the data object")
        self.metadata.add(self.SDATA_SUUID, suuid.suuid_str, dtype="str", description="Super Universally Unique Identifier")
        self.metadata.add(self.SDATA_PARENT_SUUID, str(kwargs.get("parent", "")), dtype="str", description="suuid of the parent sdata")
        self.metadata.add(self.SDATA_CLASS, self.__class__.__name__, dtype="str", description="sdata class")
        self.metadata.add(self.SDATA_URL, str(kwargs.get("url", "")), dtype="str", description="url of the data object")
        self.metadata.add(self.SDATA_PROJECT_SUUID, str(kwargs.get("project", "")), dtype="str", description="project suuid")

        if "default_attributes" in kwargs:
            self.default_attributes.extend(kwargs.get("default_attributes"))
        self.set_default_attributes()


    @property
    def md(self):
        """Shortcut for metadata."""
        return self.metadata

    @property
    def mdf(self):
        """Shortcut for metadata DataFrame."""
        return self.metadata.df

    @property
    def osname(self):
        """:returns: os compatible name (ascii?)"""
        return self.asciiname(self.name)

    @staticmethod
    def asciiname(name):
        mapper = {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
                  "ß": "sz", " ": "_", "/": "_", "\\": "_"}
        for k, v in mapper.items():
            name = name.replace(k, v)
        name = name.lower()
        return name.encode('ascii', 'replace').decode("ascii")

    def _get_uuid(self):
        uid = SUUID.from_suuid_str(self.metadata.get(self.SDATA_SUUID).value).uuid.hex
        return uid

    def get_uuid(self):
        return uuid.UUID(self.uuid)

    uuid = property(fget=_get_uuid, doc="uuid of the object")

    def _get_suuid(self):
        return self.metadata.get(self.SDATA_SUUID).value

    def _set_suuid(self, value):
        self.metadata.set_attr(self.SDATA_SUUID, value)

    def get_suuid(self):
        return SUUID.from_suuid_str(self.metadata.get(self.SDATA_SUUID).value)

    # def get_suuid(self):
    #     return SUUID.from_suuid_sname(self.sname)

    suuid = property(fget=_get_suuid, fset=_set_suuid, doc="suuid of the object")

    def _get_sname(self):
        return self.metadata.get(self.SDATA_SNAME).value

    def _set_sname(self, value):
        self.metadata.set_attr(self.SDATA_SNAME, value)

    sname = property(fget=_get_sname, fset=_set_sname, doc="sname of the object")

    def _get_name(self):
        return self.metadata.get(self.SDATA_NAME).value

    def _set_name(self, value):
        self.metadata.set_attr(self.SDATA_NAME, value)

    name = property(fget=_get_name, fset=_set_name, doc="name of the object")

    @property
    def parent(self):
        return self.metadata.get(self.SDATA_PARENT).value

    def get_parent(self):
        return SUUID.from_suuid_sname(self.metadata.get(self.SDATA_PARENT).value)

    @property
    def project(self):
        return self.metadata.get(self.SDATA_PROJECT).value

    def get_project(self):
        return self.metadata.get(self.SDATA_PROJECT).value

    def __str__(self):
        return f"<{self.__class__.__name__} '{self.name}':({self.sname})>"

    __repr__ = __str__

    @property
    def udf(self):
        return self.metadata.udf

    @property
    def sdf(self):
        return self.metadata.sdf

    def set_default_attributes(self):
        for attr_dict in self.default_attributes:
            self.metadata.add(**attr_dict)


def base_factory(class_name: str, **kwargs):
    """
    Factory function to create an instance of a dynamically generated subclass of Base.

    :param class_name: The name of the class to generate (e.g., "Material").
    :param kwargs: Keyword arguments to pass to the instance initialization.
    :return: An instance of the generated class.
    """

    # Define the __init__ method to mimic the provided example
    def __init__(self, **init_kwargs):
        super(self.__class__, self).__init__(**init_kwargs)

    # Create the class dynamically
    cls = type(class_name, (Base,), {'__init__': __init__})

    # Instantiate and return with provided kwargs
    return cls(**kwargs)

if __name__ == '__main__':
    class MyFancyClass(Base):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            pass

    c = MyFancyClass(name="Hello Spencer")
    print(c)
    print(c.osname)
    print(c.mdf)
