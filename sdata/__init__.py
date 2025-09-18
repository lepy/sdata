# -*-coding: utf-8-*-
from __future__ import division

__version__ = '1.0.0'
__revision__ = None
__version_info__ = tuple([int(num) for num in __version__.split('.')])

'''
basic sdata types 
'''

import sys
import uuid
import logging
import re
import unicodedata

# fix "ValueError: unsupported pickle protocol: 5"
#import pickle
#pickle.HIGHEST_PROTOCOL = 4
import pandas

from sdata.metadata import Metadata, Attribute
from sdata.data import Data
from sdata.base import Base, sdata_factory
from sdata.sclass.blob import Blob
from sdata.suuid import SUUID
from sdata.sclass.image import Image

# import sdata.timestamp as timestamp
from sdata.timestamp import today_str, now_utc_str, now_local_str
import inspect

try:
    import openpyxl
except:
    logging.warning("openpyxl is not available -> no xlsx import")
    openpyxl = None


def uuid_from_str(name):
    return uuid.uuid3(uuid.NAMESPACE_DNS, name)


def osname(name, lower=True):
    mapper = [("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"),
              ("ß", "sz"), (" ", "_"), ("/", "_"), ("\\", "_")]
    for k, v in mapper:
        name = name.replace(k, v)
    if lower is True:
        name = name.lower()
    return name.encode('ascii', 'replace').decode("ascii")

def generate_safe_name(original_name: str) -> str:
    r"""
    Generiert einen sicheren Dateinamen, der kompatibel mit Linux, Windows, AWS S3 und als Datenbank-Spaltenname oder Index-Name ist.

    - Konvertiert zu Lowercase.
    - Ersetzt Umlaute und Sonderzeichen durch ASCII-Äquivalente oder Unterstriche.
    - Erlaubt nur alphanumerische Zeichen (a-z, 0-9), Unterstriche (_) und Punkte (.).
    - Entfernt verbotene Zeichen für Windows (z.B. < > : " / \ | ? *).
    - Reduziert multiple Unterstriche zu einem.
    - Entfernt leading/trailing Unterstriche oder Punkte.
    - Stellt sicher, dass der Name mit einem Buchstaben oder Unterstrich beginnt (für DB-Kompatibilität).
    - Begrenzt die Länge auf 255 Zeichen (sichere Grenze für die meisten Dateisysteme).

    :param original_name: Der ursprüngliche Name (str).
    :return: Der sichere Dateiname (str).
    """
    if not isinstance(original_name, str):
        original_name = str(original_name)

    # Ersetze verbotene Zeichen für Windows und allgemeine Sicherheit
    forbidden = r'[<>:"/\\|?*]'
    original_name = re.sub(forbidden, '_', original_name)

    # Konvertiere Umlaute und andere diakritische Zeichen zu ASCII
    mapper = {
        "ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
        "ß": "ss", " ": "_", "!": "_", "@": "_", "#": "_", "$": "_",
        "%": "_", "^": "_", "&": "_", "*": "_", "(": "_", ")": "_",
        ";": "_", ",": "_", "+": "_", "=": "_", "[": "_", "]": "_",
        "{": "_", "}": "_", "`": "_", "~": "_"
    }
    for k, v in mapper.items():
        original_name = original_name.replace(k, v)

    # Normalisiere zu ASCII und entferne nicht-ASCII-Zeichen
    original_name = unicodedata.normalize('NFKD', original_name).encode('ascii', 'ignore').decode('ascii')

    # # Zu Lowercase
    # name = original_name.lower()

    # Ersetze ungültige Zeichen mit _
    # Erlaube nur a-z, 0-9, _, .
    #name = re.sub(r'[^a-z0-9_.]', '_', original_name)

    # Reduziere multiple _ oder . zu _
    name = re.sub(r'[_.-]+', '_', original_name)

    # Entferne leading/trailing _ oder .
    name = name.strip('_.')

    # Stelle sicher, dass es mit einem Buchstaben oder _ beginnt (für DB)
    if name and (name[0].isdigit() or name[0] == '.'):
        name = '_' + name

    # Begrenze auf 255 Zeichen
    if len(name) > 255:
        name = name[:255]

    # Falls der Name leer wird, fallback zu einem Standard
    if not name:
        name = 'noname'

    return name

SDATACLS = {"Data": Data,
            "Image": Image,
            "Blob": Blob,
            "SUUID": SUUID,
            }

__all__ = ["Data", "Image", "Blob", "SUUID"]


def print_classes():
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj):
            print(obj)
