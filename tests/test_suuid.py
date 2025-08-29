# -*-coding: utf-8-*-
import logging
logger = logging.getLogger("sdata")

import sys
import os
import pandas as pd

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

import sdata
import uuid

def test_suuid():
    suuid = sdata.SUUID("Data", "Otto")
    suuid, suuid.to_list()
    assert suuid.name == "otto"

def test_suuid_from_name():
    suuid = sdata.SUUID.from_name(class_name="MyClass", name="Otto")
    suuid, suuid.to_list()
    #((MyClass|Otto|9120846d11185cbd9c06742056d757ad),
 # ['OTEyMDg0NmQxMTE4NWNiZDljMDY3NDIwNTZkNzU3YWRNeUNsYXNzfE90dG8=',
 #  'MyClass',
 #  'Otto',
 #  '9120846d11185cbd9c06742056d757ad'])
    print(suuid.huuid)
    print(suuid.suuid_str)
    print(suuid.sname)


    assert suuid.huuid=='d090bdae83315b8b935ea4c71ef86b2f'
    assert suuid.name == 'otto'
    assert suuid.suuid_str == 'ZDA5MGJkYWU4MzMxNWI4YjkzNWVhNGM3MWVmODZiMmZNeUNsYXNzQG90dG8='
    assert suuid.class_name == 'MyClass'

    s = sdata.SUUID.from_suuid_str(suuid.suuid_str)
    assert s.huuid=='d090bdae83315b8b935ea4c71ef86b2f'
    assert s.name == 'otto'
    assert s.suuid_str == 'ZDA5MGJkYWU4MzMxNWI4YjkzNWVhNGM3MWVmODZiMmZNeUNsYXNzQG90dG8='
    assert s.class_name == 'MyClass'

