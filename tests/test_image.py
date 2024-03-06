import sys
import os
import pandas as pd

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

import sdata
import uuid

def test_image():
    imagepath = os.path.join(modulepath, "images/a.png")
    png = sdata.Image.from_file(imagepath, project="ImageProject", description="a png image")

    assert png.name == "a.png"

    imagepath = os.path.join(modulepath, "images/sdata.png")
    png = sdata.Image.from_file(imagepath, project="ImageProject", description="a png image")

    assert png.name == "sdata.png"
    assert png.suuid == "Y2VmZTFhNDlhYmM0NDIxNzhmNjdkZjlkNDYzZjlhYTNJbWFnZXxzZGF0YS5wbmc="

    imagepath = os.path.join(modulepath, "images/sdata.jpg")
    jpg = sdata.Image.from_file(imagepath, project="ImageProject", description="a jpg image")

    assert jpg.name == "sdata.jpg"
    assert jpg.suuid == 'YmViNTJkYTFiOTc4NGUxMzk0MWQyNmI5YjQ2YTNlNWJJbWFnZXxzZGF0YS5qcGc='
