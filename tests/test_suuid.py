# -*-coding: utf-8-*-
import logging
logger = logging.getLogger("sdata")

import sdata


def test_suuid():
    sid = sdata.SUUID.from_name("Data", "Otto")
    assert sid.class_name == "Data"
    assert sid.name == "otto"                       # S3-sicher normalisiert
    assert sid.sname == f"Data__otto__{sid.huuid}"


def test_suuid_from_name():
    sid = sdata.SUUID.from_name(class_name="MyClass", name="Otto")
    assert sid.huuid == "d090bdae83315b8b935ea4c71ef86b2f"   # golden (unverändert)
    assert sid.name == "otto"
    assert sid.class_name == "MyClass"

    # Roundtrip über den kompakten Token (suuid_str)
    restored = sdata.SUUID.from_suuid_str(sid.suuid_str)
    assert restored == sid
    assert restored.huuid == sid.huuid
