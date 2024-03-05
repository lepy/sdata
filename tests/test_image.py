import sys
import os
import pandas as pd

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

import sdata
import uuid

def test_image():
    imagepath = os.path.join(modulepath, "images/a.png")
    png = sdata.Image.from_filepath(imagepath, project="ImageProject", description="a png image")

    assert png.name == "a.png"

    imagepath = os.path.join(modulepath, "images/sdata.png")
    png = sdata.Image.from_filepath(imagepath, project="ImageProject", description="a png image")

    assert png.name == "sdata.png"
    assert png.suuid == "ODk3YmE1N2M3MDNlNTFjYWEzZGI4MTQ0M2YzNDg3MTFJbWFnZXxzZGF0YS5wbmc="

    imagepath = os.path.join(modulepath, "images/sdata.jpg")
    jpg = sdata.Image.from_filepath(imagepath, project="ImageProject", description="a jpg image")

    assert jpg.name == "sdata.jpg"
    assert jpg.suuid == 'OWY0NGQ5ZGEyMDBlNTYyOThjNmYzYTE4ODk2YmU1MmNJbWFnZXxzZGF0YS5qcGc='
