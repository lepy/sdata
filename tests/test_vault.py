from sdata.iolib.vault import Vault, VaultIndex
from sdata.iolib.vault import FileSystemVault, VaultIndex, VaultSqliteIndex, Hdf5Vault
from sdata import Data
import pandas as pd
import numpy as np
import sdata
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

    data = sdata.Data(name="otto",
                      uuid=sdata.uuid_from_str("otto"),
                      table=pd.DataFrame({"a": [1, 2, 3]}),
                      description="Hallo\nSpencer")
    datac = data.copy(uuid='18b26864e7794f5182d38459bab85842', name="copy")
    print(datac)

    ret = vault.dump_blob(data)
    print(ret)
    ret = vault.dump_blob(datac)
    print(ret)
    ldata = vault.load_blob(data.uuid)
    assert data == ldata

    ldatac = vault.load_blob(datac.uuid)
    assert datac == ldatac

    keys = vault.keys()
    print(keys)
    assert sorted(keys) == sorted(['18b26864e7794f5182d38459bab85842', '21b83703d98e38a7be2e50e38326d0ce'])

    items = vault.items()
    print("items", items)
    assert len(items) == 2
    for k, v in items:
        print(f"{k}:{v}")

    item_dict = dict(items)
    assert item_dict['18b26864e7794f5182d38459bab85842'].uuid == datac.uuid
    assert item_dict['18b26864e7794f5182d38459bab85842'].name == datac.name

    values = vault.values()
    print("values", values)
    assert len(values) == 2
    for v in values:
        print(f"{v.name}:{v}")

    # o = values.find_blobs("otto")
    # print("!!", o)
    # assert isinstance(o, list)

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
    datac = data.copy(uuid='18b26864e7794f5182d38459bab85842', name="copy")
    print(datac)


    ret = vault.dump_blob(data)
    print(ret)
    ret = vault.dump_blob(datac)
    print(ret)

    ldata = vault.load_blob(data.uuid)
    assert data == ldata

    ldatac = vault.load_blob(datac.uuid)
    assert datac == ldatac

    keys = vault.keys()
    print(keys)
    assert sorted(keys) == sorted(['18b26864e7794f5182d38459bab85842', '21b83703d98e38a7be2e50e38326d0ce'])

    items = vault.items()
    print("items", items)
    assert len(items) == 2
    for k, v in items:
        print(f"{k}:{v}")

    item_dict = dict(items)
    assert item_dict['18b26864e7794f5182d38459bab85842'].uuid == datac.uuid
    assert item_dict['18b26864e7794f5182d38459bab85842'].name == datac.name

    values = vault.values()
    print("values", values)
    assert len(values) == 2
    for v in values:
        print(f"{v.name}:{v}")


    # vault.reindex()

    # assert 1==2
