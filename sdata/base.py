import os
import uuid
import logging
import unicodedata
import json
from typing import List, Dict, Any, Optional, Type, Literal

import pandas
from sdata import __version__
from sdata.sclass import register
from sdata.suuid import SUUID
from sdata.metadata import Metadata, Attribute, extract_name_unit

import sdata.sclass

# from sdata.timestamp import now_utc_str, now_local_str, today_str



logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class SdataUuidException(Exception):
    pass


class Base:
    """
    Base class for sdata objects with metadata management.
    Provides core functionality for handling metadata, unique identifiers,
    serialization, and hierarchical relationships.
    """

    SDATA_VERSION = "_sdata_version"
    SDATA_CLASS = "_sdata_class"
    SDATA_NAME = "_sdata_name"
    SDATA_SNAME = "_sdata_sname"
    SDATA_SUUID = "_sdata_suuid"
    SDATA_PARENT_SNAME = "_sdata_parent_sname"  # Changed to store sname for consistency
    SDATA_PROJECT_SNAME = "_sdata_project_sname"  # Changed to store sname for consistency
    SDATA_BFO_CLASS = "_sdata_bfo_class" # BFO (Basic Formal Ontology) top-level ontology class name

    SDATA_ATTRIBUTES: List[str] = [
        SDATA_VERSION, SDATA_NAME, SDATA_SUUID, SDATA_CLASS,
        SDATA_PARENT_SNAME, SDATA_PROJECT_SNAME, SDATA_BFO_CLASS
    ]

    @classmethod
    def get_sdata_spec(cls: type) -> str:
        """Canonischer, importierbarer String für eine Klasse."""
        return f"{cls.__module__}:{cls.__qualname__}"

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize Base with metadata.

        :param name: Required name of the object (str).
        :param parent: Optional parent object (Base) or suuid_str (str).
        :param project: Optional project object (Base) or suuid_str (str).
        :param ns_name: Optional namespace for reproducible SUUID (str).
        :param default_attributes: List of dicts for additional metadata attributes.
        :raises ValueError: If name is empty or None.
        """

        name = kwargs.get("name", "noname")
        if not name:
            raise ValueError("Name cannot be empty")
        self.metadata = Metadata(name=name)

        project = kwargs.get("project", None)
        if project is not None and issubclass(project.__class__, Base):
            self.metadata.add(
                self.SDATA_PROJECT_SNAME, project.sname, dtype="str",
                description="sname of the project"
            )
        elif project is not None:
            logger.warning(
                f"project must be of type Base, got {project.__class__.__bases__}"
            )
        else:
            self.metadata.add(
                self.SDATA_PROJECT_SNAME, str(kwargs.get("project_sname", "")),
                dtype="str", description="sname of the project"
            )

        if kwargs.get("ns_name", None) is not None:
            suuid = SUUID.from_name(
                class_name=self.__class__.__name__,
                name=SUUID.generate_safe_filename(name),
                ns_name=kwargs.get("ns_name").lower()
            )
        else:
            suuid = SUUID(self.__class__.__name__, name=SUUID.generate_safe_filename(name))
        self.default_attributes: List[Dict[str, Any]] = []

        self.metadata.add(
            self.SDATA_VERSION, __version__, dtype="str",
            description="sdata package version", required=True
        )
        self.metadata.add(
            self.SDATA_BFO_CLASS, "sdata.sclass:IndependentContinuant", dtype="str",
            description="sdata bfo class name", required=True
        )
        self.metadata.add(
            self.SDATA_NAME, name, dtype="str",
            description="name of the data object", required=True
        )
        self.metadata.add(
            self.SDATA_SNAME, suuid.sname, dtype="str",
            description="sname of the data object", required=True
        )
        self.metadata.add(
            self.SDATA_SUUID, suuid.suuid_str, dtype="str",
            description="Super Universally Unique Identifier", required=True
        )
        self.metadata.add(
            self.SDATA_CLASS, self.get_sdata_spec(), dtype="str",
            description="sdata class", required=True
        )

        parent = kwargs.get("parent", None)
        if parent is not None and issubclass(parent.__class__, Base):
            self.metadata.add(
                self.SDATA_PARENT_SNAME, parent.sname, dtype="str",
                description="sname of the parent"
            )
        elif parent is not None:
            logger.warning(
                f"parent must be of type Base, got {parent.__class__.__bases__}"
            )
        else:
            self.metadata.add(
                self.SDATA_PARENT_SNAME, str(kwargs.get("parent_sname", "")),
                dtype="str", description="sname of the parent"
            )

        if "default_attributes" in kwargs:
            self.default_attributes.extend(kwargs.get("default_attributes"))
        self.set_default_attributes()

        self._description = kwargs.get("description", "")
        self._data: Dict[str, Any] = kwargs.get("data", {})

        logger.debug(f"Created {self.__class__.__name__} '{suuid.sname}'")

    @property
    def md(self) -> Metadata:
        """Shortcut to access the metadata object."""
        return self.metadata

    @property
    def mdf(self) -> pandas.DataFrame:
        """Shortcut to access the metadata as a pandas DataFrame."""
        return self.metadata.df

    @property
    def osname(self) -> str:
        """Returns an OS-compatible ASCII name."""
        return SUUID.generate_safe_filename(self.name)

    @property
    def class_name(self) -> str:
        """Returns the class name of the object."""
        return self.__class__.__name__

    @property
    def uuid(self) -> uuid.UUID:
        """Returns the UUID component of the SUUID."""
        return self.suuid.uuid

    @property
    def huuid(self) -> str:
        """Returns the hex representation of the UUID."""
        return self.suuid.uuid.hex

    def _get_suuid(self) -> str:
        return self.metadata.get(self.SDATA_SUUID).value

    def _set_suuid(self, value: str) -> None:
        if not SUUID.is_valid_suuid_str(value):
            raise SdataUuidException("Invalid SUUID string")
        self.metadata.set_attr(self.SDATA_SUUID, value)

    suuid_str = property(
        fget=_get_suuid, fset=_set_suuid,
        doc="The SUUID of the object as a string."
    )

    @property
    def suuid(self) -> SUUID:
        """Returns the SUUID object."""
        return SUUID.from_suuid_str(self.metadata.get(self.SDATA_SUUID).value)

    @property
    def suuid_bytes(self) -> bytes:
        """Returns the SUUID string encoded as UTF-8 bytes."""
        return self.suuid_str.encode("utf-8")

    def _get_sname(self) -> str:
        return self.metadata.get(self.SDATA_SNAME).value

    def _set_sname(self, value: str) -> None:
        self.metadata.set_attr(self.SDATA_SNAME, value)

    sname = property(
        fget=_get_sname, fset=_set_sname,
        doc="The sname of the object."
    )

    def _get_name(self) -> str:
        return self.metadata.get(self.SDATA_NAME).value

    def _set_name(self, value: str) -> None:
        if not value:
            raise ValueError("Name cannot be empty")
        self.metadata.set_attr(self.SDATA_NAME, value)

    name = property(
        fget=_get_name, fset=_set_name,
        doc="The name of the object."
    )

    def _get_data(self) -> Dict[str, Any]:
        return self._data

    def _set_data(self, value: Dict[str, Any]) -> None:
        if not isinstance(value, dict):
            raise ValueError("data must be a dict")
        self._data = value

    data = property(
        fget=_get_data, fset=_set_data,
        doc="The data dictionary of the object."
    )

    def _get_description(self) -> str:
        return self._description

    def _set_description(self, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError("description must be a string")
        if len(value) > 1000:
            self._description = value[:1000] + "..."
        else:
            self._description = value

    description = property(
        fget=_get_description, fset=_set_description,
        doc="The description string of the object (max 1000 characters)."
    )

    def update_data(self, data_dict: Dict[str, Any]) -> None:
        """
        Update the data dictionary with recursive merge for nested dicts.

        :param data_dict: Dictionary to merge into self._data.
        :raises ValueError: If data_dict is not a dict.
        """
        if not isinstance(data_dict, dict):
            raise ValueError("data must be a dict")
        self._data = self._deep_update(self._data, data_dict)

    def _deep_update(self, d: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = self._deep_update(d.get(k, {}), v)
            else:
                d[k] = v
        return d

    @property
    def parent(self) -> SUUID:
        """Returns the parent as a SUUID object."""
        return self.get_parent()

    def get_parent(self) -> SUUID:
        """Returns the parent SUUID."""
        sname = self.metadata.get(self.SDATA_PARENT_SNAME).value
        if sname:
            return SUUID.from_suuid_sname(sname)
        else:
            return None

    @property
    def project(self) -> SUUID:
        """Returns the project as a SUUID object."""
        return self.get_project()

    def get_project(self) -> SUUID:
        """Returns the project SUUID."""
        sname = self.metadata.get(self.SDATA_PROJECT_SNAME).value
        if sname:
            return SUUID.from_suuid_sname(sname)
        else:
            return None

    def __str__(self) -> str:
        return f"<{self.sname}>"

    __repr__ = __str__

    @property
    def udf(self) -> pandas.DataFrame:
        """Returns the user-defined metadata as a DataFrame."""
        return self.metadata.udf

    @property
    def sdf(self) -> pandas.DataFrame:
        """Returns the system-defined metadata as a DataFrame."""
        return self.metadata.sdf

    def set_default_attributes(self) -> None:
        """
        Set default attributes from self.default_attributes list.
        """
        for attr_dict in self.default_attributes:
            self.metadata.add(**attr_dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the object to a dictionary representation.

        :return: Dictionary with metadata, data, and description.
        """
        return {
            "metadata": self.metadata.to_dict(),
            "data": self._data,
            "description": self._description,
        }

    @staticmethod
    def classname_from_classspec(spec: str) -> str:
        if ":" in spec:
            return spec.split(":")[-1]
        else:
            return spec

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Base':
        """
        Create an instance from a dictionary.

        :param d: Dictionary with metadata, data, and description.
        :return: Instance of Base or subclass.
        """
        metadata = Metadata.from_dict(d.get("metadata", {}))
        class_spec = metadata.get(cls.SDATA_CLASS).value or "sdata.base:Base"
        class_name = cls.classname_from_classspec(class_spec)
        b = sdata_factory(class_name)
        b.metadata = metadata
        b.data = d.get("data", {})
        b.description = d.get("description", "")
        return b

    def to_json(self, filepath: Optional[str] = None) -> Optional[str]:
        """
        Export the object to JSON format, either as a string or to a file.

        :param filepath: Optional file path to write JSON (default: None).
        :return: JSON string if filepath is None, else None.
        """
        data_dict = self.to_dict()
        if filepath:
            with open(filepath, "w") as fh:
                json.dump(data_dict, fh, indent=4)
            return None
        else:
            return json.dumps(data_dict, indent=4)

    @classmethod
    def from_json(cls, s: str) -> 'Base':
        """
        Create an instance from a JSON string or file path.

        :param s: JSON string or path to JSON file.
        :return: Instance of Base or subclass.
        :raises json.JSONDecodeError: If invalid JSON.
        :raises FileNotFoundError: If file not found.
        """
        if os.path.isfile(s):
            with open(s, "r") as fh:
                d = json.load(fh)
        else:
            d = json.loads(s)
        return cls.from_dict(d)

def cls_from_spec(
#        class_name: str,
        sdata_spec: Optional[str] = "sdata.base:Base",
        on_error: Literal["ignore", "strict"] = "strict",
        sdata_attrs: Optional[Dict[str, Any]] = None,
        **kwargs: Any
) -> Any:
    """
    Factory function to create an instance of a dynamically generated subclass.

    :param sdata_class: The base class to inherit from (default: sdata.base:Base).
    :param sdata_attrs: Optional dict of custom attributes/methods to add to the class.
    :param kwargs: Keyword arguments to pass to the instance initialization.
    :return: generated class.
    """
    sdata_attrs = sdata_attrs or {}

    if ":" in sdata_spec:
        mod_name, class_name = sdata_spec.split(":", 1)
    else:
        mod_name, class_name = "", sdata_spec
    try:
        sdata_class = sdata.sclass.spec_to_class(sdata_spec)
    except ModuleNotFoundError as e:
        if on_error == "ignore":
            sdata_class = Base
        else:
            raise ModuleNotFoundError(f"sdata.base.class_factory Error {e}")

    cls = type(class_name, (sdata_class,), sdata_attrs)

    def __init__(self, **init_kwargs: Any) -> None:
        super(cls, self).__init__(**init_kwargs)  # type: ignore

    setattr(cls, '__init__', __init__)
    return cls

def sclass_factory(
#        class_name: str,
        sdata_spec: Optional[str] = "sdata.base:Base",
        on_error: Literal["ignore", "strict"] = "strict",
        sdata_attrs: Optional[Dict[str, Any]] = None,
        **kwargs: Any
) -> Any:
    """
    Factory function to create an instance of a dynamically generated subclass.

    :param sdata_class: The base class to inherit from (default: sdata.base:Base).
    :param sdata_attrs: Optional dict of custom attributes/methods to add to the class.
    :param kwargs: Keyword arguments to pass to the instance initialization.
    :return: An instance of the generated class.
    """
    sdata_attrs = sdata_attrs or {}

    if ":" in sdata_spec:
        mod_name, class_name = sdata_spec.split(":", 1)
    else:
        mod_name, class_name = "", sdata_spec
    try:
        sdata_class = sdata.sclass.spec_to_class(sdata_spec)
    except ModuleNotFoundError as e:
        if on_error == "ignore":
            sdata_class = Base
        else:
            raise ModuleNotFoundError(f"sdata.base.class_factory Error {e}")

    cls = type(class_name, (sdata_class,), sdata_attrs)

    def __init__(self, **init_kwargs: Any) -> None:
        super(cls, self).__init__(**init_kwargs)  # type: ignore


    setattr(cls, '__init__', __init__)

    # print(sdata_spec, sdata_class, type(sdata_class), cls)
    instance = cls(**kwargs)
    if sdata_class.__name__ == "Base":
        instance.metadata["_sdata_class"].value = sdata_spec
    # print(sdata_class, sdata_class.__name__ == "Base")
    return instance

def sdata_factory(
        class_name: str,
        sdata_class: Type = Base,  # Neu: Optionale Basisklasse, default ist Base
        sdata_attrs: Optional[Dict[str, Any]] = None,
        **kwargs: Any
) -> Any:
    """
    Factory function to create an instance of a dynamically generated subclass.

    :param class_name: The name of the class to generate (e.g., "Material").
    :param sdata_class: The base class to inherit from (default: Base).
    :param sdata_attrs: Optional dict of custom attributes/methods to add to the class.
    :param kwargs: Keyword arguments to pass to the instance initialization.
    :return: An instance of the generated class.
    """
    sdata_attrs = sdata_attrs or {}

    cls = type(class_name, (sdata_class,), sdata_attrs)

    def __init__(self, **init_kwargs: Any) -> None:
        super(cls, self).__init__(**init_kwargs)  # type: ignore

    setattr(cls, '__init__', __init__)
    return cls(**kwargs)



if __name__ == '__main__':
    class MyFancyClass(Base):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)


    c = MyFancyClass(name="Häl[l]o@Sp{ö}ncer;-:.")

    print(c)
    print(c.osname)
    material = sdata_factory(
        "Material", name="DP800", project=None, parent=c,
        default_attributes=[{"name": "a", "value": 1.2, "dtype": float, "label": "an a"}]
    )
    m2 = Base.from_json(material.to_json())
