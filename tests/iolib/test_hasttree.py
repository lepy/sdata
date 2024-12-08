import sys
import os
import numpy as np

modulepath = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))
import sdata.iolib.hashtree


def test_uuid_from_list():
    data = [3.14159265, 42, "hello", 2.7182818]
    uid = sdata.iolib.hashtree.stable_uuid_from_list(data)
    print(uid)
    assert uid == "f09e3370d8f953398366753ca7e16eb9"


def test_hash_from_list():
    data = [3.14159265, 42, "hello", 2.7182818]
    hashstr = sdata.iolib.hashtree.stable_hash_from_list(data)
    print(hashstr)
    assert hashstr == "f54068f9b31cb94d56b454d36c1458877e5e45589684038b5c60097ad45b9052"


def test_stable_hash_from_nested_list():
    nested_list = [[3.14159265, 42, "hello", 2.7182818],
                   [1, 1.2, "ssd"],
                   ["a"],
                   ]
    hashlist = sdata.iolib.hashtree.stable_hash_from_nested_list(nested_list)
    assert np.array_equal(hashlist,
                          ['f54068f9b31cb94d56b454d36c1458877e5e45589684038b5c60097ad45b9052',
                           'ce6bc57403f6d39b1dd30fe7aca428d5de956758551facfbca290500ad9100b3',
                           'a326618a43c0b61aff497f4d8a82f4857fe952c5fae156ab94facf4adbf7dcb4'])


def test_stable_uuids_from_nested_list():
    nested_list = [[3.14159265, 42, "hello", 2.7182818],
                   [1, 1.2, "ssd"],
                   ["a"],
                   ]
    hashlist = sdata.iolib.hashtree.stable_uuids_from_nested_list(nested_list)
    assert np.array_equal(hashlist,
                          ['f09e3370d8f953398366753ca7e16eb9',
                           'b0465a6b35ce5fd28338e04233c422d7',
                           '68bb365dbf5c556faf848a6c8c72b205'])


def test_stable_cum_uuids_from_nested_list():
    nested_list = [[3.14159265, 42, "hello", 2.7182818],
                   [1, 1.2, "ssd"],
                   ["a"],
                   ]
    uuids = sdata.iolib.hashtree.stable_cum_uuids_from_nested_list(nested_list)
    print(uuids)
    assert np.array_equal(uuids,
                          ['f09e3370d8f953398366753ca7e16eb9',
                           'b8f6eb73756c5d3d8f7456003bf0dc6d',
                           'f6dd12b913135291b58bcd2f5f63f157'])

def test_stable_cum_uuid_from_nested_list():
    nested_list = [[3.14159265, 42, "hello", 2.7182818],
                   [1, 1.2, "ssd"],
                   ["a"],
                   ]
    uuidstr = sdata.iolib.hashtree.stable_cum_uuid_from_nested_list(nested_list)
    print(uuidstr)
    assert uuidstr == 'f6dd12b913135291b58bcd2f5f63f157'
