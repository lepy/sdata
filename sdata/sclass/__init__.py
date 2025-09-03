import logging
from .lazy_namespace import LazyRegistry
from typing import List, Dict, Any, Optional, Type, Literal
import sdata.base
import sys

# 1) Registry für dieses Package anlegen
_registry = LazyRegistry(__name__)

# 2) Anfangs-Exports (kann leer sein)
_registry.register_many({
    "SUUID": "sdata.suuid:SUUID",
    "Base": "sdata.base:Base",
    "Blob":"sdata.sclass.blob:Blob",
    "DataFrame":"sdata.sclass.dataframe:DataFrame",
    "Image":"sdata.sclass.image:Image",
    "ProcessData":"sdata.sclass.process:ProcessData",
    "ProcessNode":"sdata.sclass.process:ProcessNode",
    # "Class2": "_mypkg.othermodule:Class2",
})
# 3) An Package binden (aktiviert __getattr__/__dir__)
_registry.attach()

# 4) Öffentliche API zum Erweitern zur Laufzeit
def register(name: str, spec: str) -> None:
    """Erweitert den mypkg-Namespace zur Laufzeit."""
    logging.debug(f"registering '{name}' with '{spec}'")
    _registry.register(name, spec)

def register_many(mapping: dict[str, str]) -> None:
    _registry.register_many(mapping)

def get_specs() -> dict[str, str]:
    return _registry.exports()

# Optional: für (De-)Serialisierung wiederverwenden
from .lazy_namespace import to_json, from_json  # re-export

from importlib import import_module
from typing import Any

def class_to_spec(cls: type) -> str:
    """Canonischer, importierbarer String für eine Klasse."""
    return f"{cls.__module__}:{cls.__qualname__}"

def obj_to_spec(obj: Any) -> str:
    return class_to_spec(obj.__class__)

def spec_to_class(spec: str,
                  on_error: Literal["ignore", "strict"] = "strict",
                  ) -> type:
    """Auflösung 'pkg.mod:Qual.Name' → Klasse (lazy import)."""
    try:
        mod_name, class_name = spec.split(":", 1)
        register(class_name, spec)
        mod = import_module(mod_name)
        obj = mod
        for part in class_name.split("."):
            obj = getattr(obj, part)
        return obj
    except (Exception, ModuleNotFoundError, AttributeError, NameError) as e:
        if on_error == "ignore":
            obj = sdata.base.Base
            return obj
        else:
            raise ModuleNotFoundError(f"sdata.sclass.spec_to_class Error {e}")

def is_importable_by_spec(cls: type) -> bool:
    try:
        return spec_to_class(class_to_spec(cls)) is cls
    except Exception:
        return False

def make_module_alias(cls: type, alias: str | None = None) -> str:
    """
    Falls importierbarkeits-Check scheitert, Klassenalias im Modul erzeugen:
    mod:Alias  → importierbar, auch wenn Klasse ursprünglich lokal/nested war.
    """
    mod = sys.modules[cls.__module__]
    name = alias or cls.__name__
    setattr(mod, name, cls)
    return f"{cls.__module__}:{name}"




# def to_json(obj: Any, *, short_name: str | None = None) -> dict:
#     cls = obj.__class__
#     payload = getattr(obj, "to_dict", lambda: obj.__dict__)()
#     return {
#         "__type__": short_name or cls.__name__,                      # kurz
#         "__spec__": f"{cls.__module__}:{cls.__qualname__}",          # kanonisch
#         **payload,
#     }
#
# def from_json(d: dict) -> Any:
#     cls = spec_to_class(d["__spec__"])
#     data = {k: v for k, v in d.items() if k not in {"__type__", "__spec__"}}
#     if hasattr(cls, "from_dict"):
#         return cls.from_dict(data)
#     return cls(**data)

if __name__ == '__main__':
    pass
    # Process_1_Generic = create_process_class(
    #     'Process_1',
    #     input_classes={'DataClass_1': DataClass_1, 'DataClass_2': DataClass_2},
    #     output_classes={'DataClass_3': DataClass_3},
    # )
    # print(Process_1_Generic)