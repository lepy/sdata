# -*- coding: utf-8 -*-

import logging
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG, datefmt='%I:%M:%S')

import sdata
from sdata.io.vault import FileSystemVault, VaultIndex, VaultSqliteIndex, Hdf5Vault
from sdata import Data
import pandas as pd
import numpy as np
import shutil
import os


def test_sqlitevault():

    d1 = Data(name="d1", uuid=sdata.uuid_from_str("d1"))
    d2 = Data(name="d2", uuid=sdata.uuid_from_str("d2"))

    db_file = "/tmp/test_sqlitevault.sqlite"

    vi = VaultSqliteIndex(db_file=db_file)
    vi.drop_db()

    all_m = vi.get_all_metadata()
    print(all_m)
    assert len(all_m) == 0

    vi.update_from_metadata(d1.metadata)
    vi.update_from_metadata(d2.metadata)
    all_m = vi.get_all_metadata()
    print(all_m)
    assert len(all_m) == 2

    print(vi.df)
    d1i = vi.df.loc[d1.uuid]
    print(d1i)
    assert vi.df.loc[d1.uuid, "!sdata_uuid"] == d1.uuid
    assert vi.df.loc[d1.uuid, "!sdata_name"] == d1.name

    assert len(vi.df) == 2

    vi.drop_db()
    all_m = vi.get_all_metadata()
    print(all_m)
    assert len(all_m) == 0

def test_filesystemvault():
    rootpath = "/tmp/test_filesystemvault/"

    shutil.rmtree(rootpath, ignore_errors=True)

    vault = FileSystemVault(rootpath=rootpath)
    print(vault)
    assert os.path.exists(rootpath)

def test_hdf5vault():

    rootpath = "/tmp/test_hdf5vault.h5"

    if os.path.exists(rootpath):
        os.remove(rootpath)
    vault = Hdf5Vault(rootpath=rootpath)
    print(vault)
    assert os.path.exists(rootpath)

    data = sdata.Data(name="otto",
                      uuid=sdata.uuid_from_str("otto"),
                      table=pd.DataFrame({"a": [1, 2, 3]}),
                      description="Hallo\nSpencer")
    datac = data.copy()

    ret = vault.dump_blob(data)
    print(ret)

    ldata = vault.load_blob(data.uuid)
    assert data == ldata

    ldata = vault.load_blob(datac.uuid)

    # assert 1==2
