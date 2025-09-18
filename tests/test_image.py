import sys
import os
import pandas as pd
from sdata.sclass.image import Image
modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

import sdata
import uuid

def test_image():
    imagepath = os.path.join(modulepath, "images/a.png")
    png = Image.from_file(imagepath, project="ImageProject", description="a png image")

    assert png.name == "a.png"

    imagepath = os.path.join(modulepath, "images/sdata.png")
    png = Image.from_file(imagepath, ns_name="ImageProject", description="a png image")
    print(png.name)
    assert png.name == "sdata.png"
    assert png.suuid.suuid_bytes == b"ODZiNTVmM2MwZGNhNWQ2NmJhOTdkZDVmZGNlOWExNjRJbWFnZV9fc2RhdGFfcG5n"

    imagepath = os.path.join(modulepath, "images/sdata.jpg")
    jpg = Image.from_file(imagepath, ns_name="ImageProject", description="a jpg image")

    assert jpg.name == "sdata.jpg"
    assert jpg.sname == 'Image__sdata_jpg__d05005986f875e749604e3a61da836e3'
