import sdata
from sdata import __version__
from sdata.suuid import SUUID
from sdata.metadata import Metadata, Attribute, extract_name_unit
from sdata.timestamp import now_utc_str, now_local_str, today_str
import uuid
import logging
import unicodedata
import json
from typing import List, Dict, Any, Optional
import pandas

logger = logging.getLogger(__name__)


class SdataUuidException(Exception):
    pass


class Base:
    """
    Base class for sdata objects with metadata management.
    """

    SDATA_VERSION = "_sdata_version"
    SDATA_CLASS = "_sdata_class"
    SDATA_NAME = "_sdata_name"
    SDATA_SNAME = "_sdata_sname"
    SDATA_SUUID = "_sdata_suuid"
    SDATA_PARENT_SNAME = "_sdata_parent_sname"
    SDATA_PROJECT_SNAME = "_sdata_project_sname"

    SDATA_ATTRIBUTES: List[str] = [
        SDATA_VERSION, SDATA_NAME, SDATA_SUUID, SDATA_CLASS,
        SDATA_PARENT_SNAME, SDATA_PROJECT_SNAME
    ]

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize Base with metadata.

        :param name: Required name of the object (str).
        :param parent: Optional parent SUUID (str).
        :param project: Optional project SUUID (str).
        :param ns_name: Optional name space for reproduceable a suuid (str).
        :param default_attributes: List of dicts for additional metadata.
        :raises ValueError: If name is empty or None.
        """

        name = kwargs.get("name", "noname")
        if not name:
            raise ValueError("Name cannot be empty")
        self.metadata = Metadata(name=name)

        project = kwargs.get("project", None)
        project_sname = None
        if project is not None and issubclass(project.__class__, Base):
            self.metadata.add(self.SDATA_PROJECT_SNAME, project.sname, dtype="str",
                              description="sname of the project")
            project_sname = project.sname
        elif project is not None:
            logger.warning(f"project must be of type sdata.Base {project.__class__.__bases__}")
        else:
            self.metadata.add(self.SDATA_PROJECT_SNAME, str(kwargs.get("project_sname", "")), dtype="str",
                              description="sname of the project")

        if kwargs.get("ns_name", None) is not None:
            suuid = SUUID.from_name(class_name=self.__class__.__name__, name=self.asciiname(name),
                                    ns_name=kwargs.get("ns_name").lower())
        else:
            suuid = SUUID(self.__class__.__name__, name=self.asciiname(name))
        self.default_attributes: List[Dict[str, Any]] = []

        self.metadata.add(self.SDATA_VERSION, __version__, dtype="str", description="sdata package version",
                          required=True)
        self.metadata.add(self.SDATA_NAME, name, dtype="str", description="name of the data object", required=True)
        self.metadata.add(self.SDATA_SNAME, suuid.sname, dtype="str", description="sname of the data object",
                          required=True)
        self.metadata.add(self.SDATA_SUUID, suuid.suuid_str, dtype="str",
                          description="Super Universally Unique Identifier", required=True)
        self.metadata.add(self.SDATA_CLASS, self.__class__.__name__, dtype="str", description="sdata class",
                          required=True)

        parent = kwargs.get("parent", None)
        if parent is not None and issubclass(parent.__class__, Base):
            self.metadata.add(self.SDATA_PARENT_SNAME, parent.sname, dtype="str",
                              description="sname of the parent")
        elif parent is not None:
            logger.warning(f"parent must be of type sdata.Base {parent.__class__.__bases__}")
        else:
            self.metadata.add(self.SDATA_PARENT_SNAME, str(kwargs.get("parent_sname", "")), dtype="str",
                              description="sname of the parent")

        if "default_attributes" in kwargs:
            self.default_attributes.extend(kwargs.get("default_attributes"))
        self.set_default_attributes()

        self._description = kwargs.get("description", "")
        self._data: Dict[str, Any] = kwargs.get("data", {})

        logger.debug(f"Created {self.__class__.__name__} '{suuid.sname}'")

    @property
    def md(self) -> Metadata:
        """Shortcut for metadata."""
        return self.metadata

    @property
    def mdf(self) -> pandas.DataFrame:  # Assuming Metadata.df returns a DataFrame
        """Shortcut for metadata DataFrame."""
        return self.metadata.df

    @property
    def osname(self) -> str:
        """:returns: os compatible name (ascii)"""
        return self.asciiname(self.name)

    @property
    def class_name(self) -> str:
        """:returns: class_name"""
        return self.__class__.__name__

    @staticmethod
    def asciiname(name: str) -> str:
        """
        Convert name to ASCII-compatible string for OS use.

        :param name: Original name.
        :return: Sanitized name.
        """
        mapper = {
            "ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
            "ß": "ss", " ": "_", "/": "_", "\\": "_", "!": "_", "@": "_", "#": "_",
            "$": "_", "%": "_", "^": "_", "&": "_", "*": "_", "(": "_", ")": "_", ";": "_"
        }
        for k, v in mapper.items():
            name = name.replace(k, v)
        name = unicodedata.normalize('NFKD', name).encode('ascii', 'replace').decode('ascii')
        return name.lower()

    @property
    def uuid(self) -> uuid.UUID:
        return self.suuid.uuid

    @property
    def huuid(self) -> str:
        return self.suuid.uuid.hex

    def _get_suuid(self) -> str:
        return self.metadata.get(self.SDATA_SUUID).value

    def _set_suuid(self, value: str) -> None:
        if not SUUID.is_valid_suuid_str(value):  # Assuming SUUID has a validation method; add if not
            raise SdataUuidException("Invalid SUUID string")
        self.metadata.set_attr(self.SDATA_SUUID, value)

    @property
    def suuid(self) -> SUUID:
        return SUUID.from_suuid_str(self.metadata.get(self.SDATA_SUUID).value)

    suuid_str = property(fget=_get_suuid, fset=_set_suuid, doc="suuid of the object (str)")

    @property
    def suuid_bytes(self) -> bytes:
        return self.suuid_str.encode("utf-8")

    def _get_sname(self) -> str:
        return self.metadata.get(self.SDATA_SNAME).value

    def _set_sname(self, value: str) -> None:
        self.metadata.set_attr(self.SDATA_SNAME, value)

    sname = property(fget=_get_sname, fset=_set_sname, doc="sname of the object")

    def _get_name(self) -> str:
        return self.metadata.get(self.SDATA_NAME).value

    def _set_name(self, value: str) -> None:
        if not value:
            raise ValueError("Name cannot be empty")
        self.metadata.set_attr(self.SDATA_NAME, value)

    name = property(fget=_get_name, fset=_set_name, doc="name of the object")

    def _get_data(self) -> dict:
        return self._data

    def _set_data(self, value: dict) -> None:
        if not isinstance(value, dict):
            raise ValueError("data must be a dict")
        self._data = value

    data = property(fget=_get_data, fset=_set_data, doc="data dictionary of the object")

    def _get_description(self) -> str:
        return self._description

    def _set_description(self, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError("description must be a string")
        if len(value) > 10000:
            self._description = value[1000:] + "..." + value[9000:]
        else:
            self._description = value
    description = property(fget=_get_description, fset=_set_description, doc="description string of the object")

    def update_data(self, data_dict: dict) -> None:
        if not isinstance(data_dict, dict):
            raise ValueError("data must be a dict")
        self._data.update(data_dict)

    @property
    def parent(self) -> str:
        return self.metadata.get(self.SDATA_PARENT_SUUID).value

    def get_parent(self) -> SUUID:
        return SUUID.from_suuid_str(self.metadata.get(self.SDATA_PARENT_SUUID).value)

    @property
    def project(self) -> str:
        return self.metadata.get(self.SDATA_PROJECT_SNAME).value

    def get_project(self) -> str:  # Assuming project is str; change to SUUID if it's a SUUID
        return self.metadata.get(self.SDATA_PROJECT_SNAME).value

    def __str__(self) -> str:
        return f"<{self.sname}>"
        # return f"<{self.__class__.__name__}:'{self.name}':({self.sname})>"

    __repr__ = __str__

    @property
    def udf(self) -> 'pandas.DataFrame':  # Assuming types
        return self.metadata.udf

    @property
    def sdf(self) -> 'pandas.DataFrame':
        return self.metadata.sdf

    def set_default_attributes(self) -> None:
        for attr_dict in self.default_attributes:
            self.metadata.add(**attr_dict)
        # Optional: Validate against SDATA_ATTRIBUTES if needed

    def to_dict(self) -> Dict[str, Any]:
        return {"metadata": self.metadata.to_dict(),
                "data": self._data,
                "description": self._description, }

    @classmethod
    def from_dict(cls, d: dict) -> 'Base':
        metadata = Metadata.from_dict(d.get("metadata", {}))
        class_name = metadata.get(cls.SDATA_CLASS).value or "Base"
        b = base_factory(class_name)
        b.metadata = metadata
        b.data = d.get("data", {})
        b.description = d.get("description", "")
        return b

    def to_json(self, filepath=None):
        """export Data in json format

        :param filepath: export file path (default:None)
        :return: json str
        """

        data_dict = self.to_dict()
        if filepath:
            with open(filepath, "w") as fh:
                json.dump(data_dict, fh)
        else:
            return json.dumps(data_dict)

    @classmethod
    def from_json(cls, s):
        """create Data from json str or file

        :param s: json str
        :return: sdata.Base
        """
        data = cls(name="N.N.")

        try:
            d = json.loads(s)
            return cls.from_dict(d)

        except json.decoder.JSONDecodeError:
            logger.error("data.from_json: unexpected error")
            d = None
            raise


def base_factory(class_name: str, custom_attrs: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
    """
    Factory function to create an instance of a dynamically generated subclass of Base.

    :param class_name: The name of the class to generate (e.g., "Material").
    :param custom_attrs: Optional dict of custom attributes/methods to add to the class.
    :param kwargs: Keyword arguments to pass to the instance initialization.
    :return: An instance of the generated class.
    """
    custom_attrs = custom_attrs or {}

    # Define the __init__ method to mimic the provided example
    def __init__(self, **init_kwargs: Any) -> None:
        super(self.__class__, self).__init__(**init_kwargs)  # type: ignore

    custom_attrs['__init__'] = __init__
    cls = type(class_name, (sdata.base.Base,), custom_attrs)
    return cls(**kwargs)


if __name__ == '__main__':
    class MyFancyClass(Base):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)


    c = MyFancyClass(name="Häl[l]o@Sp{ö}ncer;-:.")

    print(c)
    print(c.osname)
    material = base_factory("Material", name="DP800", project=project, parent=b,
                            default_attributes=[{"name": "a", "value": 1.2, "dtype": float, "label": "an a"}])
    m2 = Base.from_json(material.to_json())
