import sdata
from sdata import __version__
from sdata.suuid import SUUID
from sdata.metadata import Metadata, Attribute, extract_name_unit
from sdata.timestamp import now_utc_str, now_local_str, today_str
import uuid
import copy


class Base:

    SDATA_VERSION = "!sdata_version"
    SDATA_NAME = "!sdata_name"
    SDATA_SNAME = "!sdata_sname"
    SDATA_UUID = "!sdata_uuid"
    SDATA_SUUID = "!sdata_suuid"
    SDATA_CTIME = "!sdata_ctime"
    SDATA_MTIME = "!sdata_mtime"
    SDATA_PARENT = "!sdata_parent"
    SDATA_CLASS = "!sdata_class"
    SDATA_PROJECT = "!sdata_project"
    SDATA_URL = "!sdata_url"
    SDATA_COLUMN = "!sdata_column"

    SDATA_ATTRIBUTES = [SDATA_VERSION, SDATA_NAME, SDATA_UUID, SDATA_SUUID, SDATA_CLASS, SDATA_PARENT, SDATA_PROJECT,
                        SDATA_CTIME, SDATA_MTIME, SDATA_URL]

    def __init__(self, **kwargs):
        name = kwargs.get("name", "N.N.")
        suuid = SUUID.from_name(class_name=self.__class__.__name__, name=name)
        self.metadata = Metadata(name=suuid.sname)
        self.metadata.add(self.SDATA_VERSION, __version__, dtype="str", description="sdata package version")
        self.metadata.add(self.SDATA_NAME, name, dtype="str", description="name of the data object")
        self.metadata.add(self.SDATA_SNAME, suuid.sname, dtype="str", description="sname of the data object")
        self.metadata.add(self.SDATA_UUID, suuid.huuid, dtype="str", description="Universally Unique Identifier")
        self.metadata.add(self.SDATA_SUUID, suuid.suuid, dtype="str", description="Super Universally Unique Identifier")
        self.metadata.add(self.SDATA_PARENT, str(kwargs.get("parent", "")), dtype="str", description="suuid of the parent sdata object")
        self.metadata.add(self.SDATA_CLASS, self.__class__.__name__, dtype="str", description="sdata class")
        self.metadata.add(self.SDATA_CTIME, now_utc_str(), dtype="str", description="creation date")
        self.metadata.add(self.SDATA_MTIME, now_utc_str(), dtype="str", description="modification date")
        self.metadata.add(self.SDATA_URL, str(kwargs.get("url", "")), dtype="str", description="url of the data object")
        self.metadata.add(self.SDATA_PROJECT, str(kwargs.get("project", "")), dtype="str", description="project name")

    @property
    def md(self):
        return self.metadata

    @property
    def mdf(self):
        return self.metadata.df

    @property
    def osname(self):
        """:returns: os compatible name (ascii?)"""
        return self.asciiname(self.name)

    @staticmethod
    def asciiname(name):
        name = copy.copy(name)
        mapper = [("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"),
                  ("ß", "sz"), (" ", "_"), ("/", "_"), ("\\", "_")]
        for k, v in mapper:
            name = name.replace(k, v)
        name = name.lower()
        return name.encode('ascii', 'replace').decode("ascii")

    def __str__(self):
        return f"({self.__class__.__name__} '{self.name}':{self.uuid})"

    def _get_uuid(self):
        return self.metadata.get(self.SDATA_UUID).value
        # return self._uuid

    def _set_uuid(self, value):
        if isinstance(value, str):
            try:
                uuid.UUID(value)
                self.metadata.set_attr(self.SDATA_UUID, uuid.UUID(value).hex)
            except ValueError as exp:
                logger.warning("data.uuid: %s" % exp)
                raise Sdata_Uuid_Exeption("got invalid uuid str '{}'".format(str(value)))
        elif isinstance(value, uuid.UUID):
            self.metadata.set_attr(self.SDATA_UUID, value.hex)
        else:
            logger.error("Data.uuid: invalid uuid '{}'".format(value))
            raise Exception("Data.uuid: invalid uuid '{}'".format(value))

    uuid = property(fget=_get_uuid, fset=_set_uuid, doc="uuid of the object")

    def get_uuid(self):
        return uuid.UUID(self.uuid)

    def _get_suuid(self):
        return self.metadata.get(self.SDATA_SUUID).value

    def _set_suuid(self, value):
        self.metadata.set_attr(self.SDATA_SUUID, value)

    suuid = property(fget=_get_suuid, fset=_set_suuid, doc="suuid of the object")

    def get_suuid(self):
        return sdata.SUUID.from_suuid_sname(self.sname)

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

    def __str__(self):
        return f"<{self.__class__.__name__}:{self.name}:{self.uuid}>"

    __repr__ = __str__

    @property
    def udf(self):
        return self.metadata.udf

    @property
    def sdf(self):
        return self.metadata.sdf

    @property
    def md(self):
        return self.metadata

if __name__ == '__main__':
    class MyFancyClass(Base):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            pass


    c = MyFancyClass(name="Hello Spencer")
    print(c)
    print(c.osname)
    print(c.mdf)

