import logging
import collections
import pandas as pd
import numpy as np
from sdata.timestamp import TimeStamp
from sdata.data import Data
from sdata.suuid import SUUID
from sdata.metadata import Metadata, Attribute
import sdata.contrib.piexif
import sdata.contrib.piexif.helper
import json
import os
import hashlib
try:
    import PIL
except:
    logging.warning("PIL is not available -> no image import")
    PIL = None
class Image(Data):
    """Image Object

    .. warning::

        highly experimental"""


    def __init__(self, **kwargs):
        """Image Object"""
        Data.__init__(self, **kwargs)
        self.url = kwargs.get("url", "")
        self.img = None

    @classmethod
    def from_filepath(cls, filepath, **kwargs):
        """

        """
        project = kwargs.get("project")
        suuid = SUUID.from_file(cls.__class__.__name__, filepath, ns_name=project)
        d = cls(name=os.path.basename(filepath), uuid=suuid.huuid, url=filepath, **kwargs)
        return d

    def get_sha3_256(self, filepath):
        sh = hashlib.sha3_256()
        with open(filepath, "rb") as fh:
            sh.update(fh.read())
        return sh.hexdigest()

    def get_image_metadata(self):
        """get metadata dict from pillow image"""
        if self.img is None:
            self.load()
        return self.img.info

    def load(self):
        """store image data in sdata.Image.img"""
        if PIL is None:
            logging.warning("PIL is not available -> no image import")
            return

        if os.path.exists(self.url):
            self.img = PIL.Image.open(self.url)
        return self.img

    @classmethod
    def from_png(cls, filepath, **kwargs):
        """load png image and metadata

        """
        if PIL is None:
            logging.warning("PIL is not available -> no image import")
            return
        data = cls.from_filepath(filepath, **filepath)
        data.load()
        if "sdata" in data.img.info:
            d = json.loads(data.img.info.get("sdata"))
            data.metadata = data.metadata.from_json(d)
        return data

    @classmethod
    def from_jpg(cls, filepath, **kwargs):
        """load jpg image and metadata

        """
        if PIL is None:
            logging.warning("PIL is not available -> no image import")
            return
        data = cls.from_filepath(filepath, **kwargs)
        # data.load()
        exif_dict = sdata.contrib.piexif.load(filepath)
        user_comment = exif_dict["Exif"][sdata.contrib.piexif.ExifIFD.UserComment]
        json_string = sdata.contrib.piexif.helper.UserComment.load(user_comment)
        d = json.loads(json_string)
        data.metadata = data.metadata.from_json(d)
        return data

    def save(self, filepath):
        if self.img is None:
            self.load()

        if filepath.lower().endswith(".png"):
            self.save_png(filepath)
        elif filepath.lower().endswith(".jpg"):
            self.save_png(filepath)
        else:
            logging.warning(f"metadata not supported for {filepath}")
            self.img.save(filepath)

    def save_png(self, filepath):
        if self.img is None:
            self.load()

        json_string = json.dumps(self.metadata.to_json())
        metadaten = PIL.PngImagePlugin.PngInfo()
        metadaten.add_text("sdata", json_string)

        self.img.save(filepath, "PNG", pnginfo=metadaten)

    def save_jpg(self, filepath):
        if self.img is None:
            self.load()
        json_string = json.dumps(self.metadata.to_json())
        exif_dict = {"Exif": {sdata.contrib.piexif.ExifIFD.UserComment: sdata.contrib.piexif.helper.UserComment.dump(json_string)}}
        exif_bytes = sdata.contrib.piexif.dump(exif_dict)
        self.img.save(filepath, "jpeg", exif=exif_bytes)