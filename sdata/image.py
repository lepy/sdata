import copy
import logging
import collections
import pandas as pd
import numpy as np
from sdata.timestamp import TimeStamp
from sdata.data import Data
from sdata.suuid import SUUID
from sdata.metadata import Metadata, Attribute
import sdata.contrib
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


    def __init__(self, url, **kwargs):
        """Image Object"""

        # url = kwargs.get("url", "")
        load = kwargs.get("load", False)
        try:
            name = os.path.basename(url)
        except Exception as exp:
            name = None
        if "name" not in kwargs:
            kwargs["name"] = name
        Data.__init__(self, **kwargs)
        self.url = url
        self.img = None
        if load is True:
            self.load()

    @classmethod
    def _from_filepath(cls, filepath, **kwargs):
        """read image from file

        """
        project = kwargs.get("project")
        suuid = SUUID.from_file(cls.__class__.__name__, filepath, ns_name=project)
        kwargs["uuid"] = suuid.huuid
        kwargs["url"] = filepath

        data = cls(name=os.path.basename(filepath), **kwargs)
        return data

    @classmethod
    def from_file(cls, filepath, **kwargs):
        """read image from file

        """
        project = kwargs.get("project")
        class_name = "Image" #cls.__class__.__name__
        suuid = SUUID.from_file(class_name, filepath, ns_name=project)
        kwargs["sname"] = suuid.sname
        kwargs["uuid"] = suuid.huuid
        kwargs["suuid"] = suuid.idstr
        kwargs["url"] = filepath
        name = os.path.basename(filepath)


        if filepath.lower().endswith(".png"):
            data = cls.from_png(filepath, **kwargs)
        elif filepath.lower().endswith(".jpg"):
            data = cls.from_jpg(filepath, **kwargs)
        else:
            data = cls(name=name, **kwargs)
        return data

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

    def to_numpy(self):
        """returns a NumPy array created from the color channels of the given Image object

            array([[[192, 190, 187],
                    [193, 190, 187],
                    [193, 190, 185],
        """
        return np.array(self.img)

    @classmethod
    def from_png(cls, filepath, **kwargs):
        """load png image and metadata

        """
        if PIL is None:
            logging.warning("PIL is not available -> no image import")
            return
        data = cls._from_filepath(filepath, **kwargs)
        data.load()
        if "sdata" in data.img.info:
            d = json.loads(data.img.info.get("sdata"))
            data.metadata = data.metadata.from_json(d)
        return data

    @staticmethod
    def _get_metadata(filepath, **kwargs):
        """

        """
        if filepath.lower().endswith(".png"):
            d = Image._get_png_metadata(filepath, **kwargs)
        elif filepath.lower().endswith(".jpg"):
            d = Image._get_png_metadata(filepath, **kwargs)
        else:
            d = {}
        return d

    @staticmethod
    def _get_png_metadata(filepath, **kwargs):
        """load metadata json dict from img.info
        """
        img = PIL.Image.open(filepath)
        try:
            d = json.loads(img.info.get("sdata"))
        except Exception as exp:
            d = {}
        return d

    @classmethod
    def from_jpg(cls, filepath, **kwargs):
        """load jpg image and metadata

        """
        if PIL is None:
            logging.warning("PIL is not available -> no image import")
            return
        data = cls._from_filepath(filepath, **kwargs)
        # data.load()
        try:
            d = cls._get_jpg_metadata(filepath)
            if d is not None:
                data.metadata = data.metadata.from_json(d)
        except Exception as exp:
            logging.debug(exp)
        return data

    @staticmethod
    def _get_jpg_metadata(filepath):
        """load metadata json dict from exif usercomment

        """
        exif_dict = sdata.contrib.piexif.load(filepath)
        exif = exif_dict.get("Exif")
        user_comment = exif.get(sdata.contrib.piexif.ExifIFD.UserComment)
        d = None
        if user_comment is not None:
            json_string = sdata.contrib.piexif.helper.UserComment.load(user_comment)
            d = json.loads(json_string)
        return d

    def saveas(self, filepath, rename=True, random=True, **kwargs):
        """save image

        """
        other = copy.deepcopy(self) # keep parent ...
        if rename is True:
            basename = os.path.basename(filepath)
            other.rename(basename, random=random)
        other.update_mtime()
        other.save(filepath)
        return other

    def save(self, filepath, **kwargs):

        if self.img is None:
            self.load()

        if filepath.endswith(".png"):
            self._save_png(filepath)
        elif filepath.lower().endswith(".jpg"):
            self._save_jpg(filepath)
        else:
            logging.warning(f"metadata not supported for {filepath}")
            self.img.save(filepath)

    def _save_png(self, filepath):
        """save png with metadata

        """
        if self.img is None:
            self.load()

        json_string = json.dumps(self.metadata.to_json())
        metadaten = PIL.PngImagePlugin.PngInfo()
        metadaten.add_text("sdata", json_string)

        self.img.save(filepath, "PNG", pnginfo=metadaten)

    def _save_jpg(self, filepath):
        """save jpg with metadata

        """
        if self.img is None:
            self.load()
        json_string = json.dumps(self.metadata.to_json())
        exif_dict = {"Exif": {sdata.contrib.piexif.ExifIFD.UserComment: sdata.contrib.piexif.helper.UserComment.dump(json_string)}}
        exif_bytes = sdata.contrib.piexif.dump(exif_dict)
        self.img.save(filepath, "jpeg", exif=exif_bytes)