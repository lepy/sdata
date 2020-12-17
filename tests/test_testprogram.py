import sys
import os
import uuid
import six

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

import sdata
from sdata.experiments import TestProgram
import pandas as pd
import numpy as np


def _gen_uuids(n=100):
    us = [uuid.uuid4().hex for i in xrange(n)]
    print(us)


def _fixed_uuid():
    fixed_uuids = ['60a90898f0c94b23984b174a74a2a47a', '6322a66775604c32af74039575221fe0',
                   '9bec8c67e09b456f96a9e23b04d9441a', 'ea4fa966bedb4104b9754a4f5f5d8a80',
                   'd061d7a58b2341128dd95412ff6ab36f', 'e4130bc9719e42dd9149e24ab7169398',
                   '8b534e9795624650828be6f39828c153', '82212590f1c2420e8066d9d4e84dbd48',
                   '37f5a429a2a1471d99b342fb95a8d16e', '96a550261de64848b128f982803f2daf',
                   'e3172927f41c4cfa96f71d76cd59b1e9', 'ba6ea9a119e84e95b304219e009c61a8',
                   'c161746eef1c4caf9e34f611e9dc4d5d', 'b7dc0d91def94a74ade3767e6a7fc27b',
                   '4253242656e84463807f454b59fcb210', 'de60b7b98bb943ae801f43ccb102d47c',
                   '923e2ef4319e4788a7ed06df7d1940c0', 'cc67e24c09a14d96aace36770d7c7253',
                   'f81f468b80c2428cae375d4dde321749', 'ea1ba03b578f47839f65a6804e8df1aa',
                   'f1a62a91b6384c6aa8163f4f2731dc90', '38b1eb86216048238fce60d262eb433c',
                   '9fb394da4a274c7191d549980a3fc5e4', 'f5376c16774e4e8cb3701b54b275663a',
                   '24b4b16be47f4a53ad07c9c3065e4721', '2403e75fb44a45cdae716d807d10a23f',
                   'a89c49ea00924d19a959d3246d1555b0', '8a17ac6db7f248b8ab48f33e9c68e642',
                   'ba1e75fac4c54244bdf894c90c5c9433', '7c090410e84747a39230bbfb677feb4b',
                   '71827185aa2b48eea00eca4b29ea360b', 'eaf70185ef52492eb166368dedf8c293',
                   'e296ecaa56f14b199597dc110e3295df', 'eb885e0e50d047e2b176df6f9537338c',
                   'd94c000fe9dd4e7cb7b92c2eb88fab58', '4f6a7eb6ec184f828e61cb58bde3ae38',
                   '31bc7501c9554b42b1d537f7b1c3b7c2', '07a670df750649a58c4f3550a4fff568',
                   '85ab8c8694ef40e49d626e768a234323', '5425056193aa4eceae3284e1025be685',
                   '2092edfc1ef442b1b8ccdfa8e3d80942', '60e0a331aae94bc5be69d9554972a2eb',
                   '143bae95ef054e309660f8ac7b821e61', 'e8949cc7d39b4241aa5ddae63392747a',
                   'efba81a764304b379522a0b04b5c8e51', '70717fcec2fd46169ce645f0ef1e2838',
                   '5a92c55dc9e84eb686dc2c962d21260e', '6730db061a05419e9b2860a215a3d511',
                   'd8f85fb0b4cd4a858b68621c2a0c2544', '126fffa1dbd54ea58076f152f7b3aa4a',
                   '1b9daeff4ac04bdba483231cfe2f2928', 'a3fd969dd9ca4a4098b83c8a9a1322f0',
                   'daac5f2b7a1248fc8f3e0aad95eb7a8b', 'ca257d83bb3442d59c9c641ca54ce437',
                   '447f48c0e24848e3bdc58eb4e90eef94', '8d0d4544dc264fbcb18d3954a9707a59',
                   '0dc66d06054d4e65aebd1a7cd7b61f02', '8946db8393be4b7ebb982f1fc6b66b58',
                   '222b02610b564b339cefba9229a6dc69', '9c46d6ff4ce44ae49f169c1b6b4cd136',
                   '87aed4b0d3004593a8f7abd9b5011375', '5836150560d449fa9fb1e6ece43914c1',
                   'b926c2c318a042c58070d94f3074f9fa', '3cb3cebb0ba242b69c862e4d64c6e594',
                   'b12d51a756254606b299559b6e115d46', '5c73c9ed582c4aacab8c55ed82af1d5e',
                   '464933693a8f45bdba4460e418044afe', '31f59ead75414a58b235d1fc5c1d8054',
                   '1945ead3bf844c1fb4dc726e4f665ef5', 'cf82de1361b34d90aee21d190cd8fb28',
                   'e58513ab1516481e91114c4481c9c62a', 'f9b67376adb0469aa5a06723617c64a2',
                   '05b8ca9b26f44a0cb2eaeee860caeabf', 'e649b9a64cbc48859537d2c3449f7095',
                   '0dd448f82cdc427c96c2c940b044a46c', '65e0629b1a7040c4a8443d58ffc1aa3a',
                   '62a4142dd2744a698cda373e7af4ad92', '120eff225b394c88bac9153638ddeda0',
                   '4a48f820e60c432488be68174248cb24', '9dcf98ed8f04481aa4793e6e7303f615',
                   '8beae3f5adb041a4a903d4fe01745345', '42acc26c1afc44669543f9b9b0626366',
                   'e98c2f050a75438cbe7c520493a00ffe', '2c4da182e2c54ead977e55c8e0e58686',
                   '07ef87f1889c450ab3ed7a29519f0a84', 'dbd8a04eb6794a1b9a66a1e0f53c08b0',
                   '1f6c577dc78e41bd819a69a3e67d0267', '3213a345ec15440b8812b47f94987b38',
                   '024725091cd64a86be390ba649a473ae', '61e34f60c7f848f7aa83b84964fddb4e',
                   '5ea58d41726448df9ab1f09967873b8a', 'e4b8485737574c82b0c0e86aef01f377',
                   '62f7f9738e0141cfb3bf2e8ae10a28a9', 'ad04dc26ea784809aae39d6adc9817f7',
                   '58724a5ba7a64c61a9e9c7c4306f0bf2', '8af74b40b501461296f9412b6904168f',
                   '15c659ba99ae44ea9dfcf65fed76fa0c', 'bd80ad679d954ae18a1bb1cc60097b9a',
                   '0e4f0d796d574173b26a07dcc961c5ea', 'ffa78242021d4951993f2f027bfb2921']
    for uid in fixed_uuids:
        yield uid


fixed_uuid = _fixed_uuid()


def get_dummy_table(dim=(10, 3)):
    df = pd.DataFrame(np.random.random((10, 3)), columns=["a", "b", "c"])
    table = sdata.Data(uuid=six.next(fixed_uuid))
    table.data = df
    table.metadata.set_attr(name="a", value="Column a", description="bar")
    table.metadata.set_attr(name="b", value="Column a", description="bar", unit="kN")
    table.metadata.set_attr(name="c", value="Column a", description="bar", unit="mm")
    return table


def gen_dummy_testprogram():
    ts1 = sdata.Data(name="testseries A1", uuid="a6fc7decdb1441518f762e3b5d798ba7")
    t1 = sdata.Data(name="test 001", uuid="8796c35b2e3a4f8a82af181698c15861")
    ts1.add_data(t1)
    t1.add_data(get_dummy_table())
    print(t1._get_table())

    t2 = sdata.Data(name="test 002", uuid="b62195ac49b64c9e8cedb7dba52bd539")
    t2.add_data(get_dummy_table())
    t2.add_data(get_dummy_table())
    ts1.add_data(t2)

    t3 = sdata.Data(name="test 003", uuid="ddc82782f5f0455895145682fe0a70f2")
    t3.add_data(get_dummy_table())
    ts1.add_data(t3)

    ts2 = sdata.Data(name="testseries A2", uuid="c3c63f8094464325bd57623cb5bbe58f")

    t1b = sdata.Data(name="test 001b", uuid="bb507e40663d49cca8264c0ed6751692")
    t1b.add_data(get_dummy_table())
    ts2.add_data(t1b)
    ts1.add_data(t3)

    t2b = sdata.Data(name="test 002b", uuid="e574e000f1404f5ebb9aaceb4183dc4c")
    # t2b.add_result(get_dummy_table())
    ts2.add_data(t2b)

    tp = TestProgram(name="testprogram FOO", uuid="43880975d9b745f1b853c31b691e67a9")
    tp.add_data(ts1)
    tp.add_data(ts2)

    return tp

def test_test():
    t = sdata.Data(name="test 001")
    print(t)
    assert t.name == "test 001"
    t.to_folder("/tmp/mytest")


def test_testseries():
    ts = sdata.Data(name="testseries A1")
    print(ts)
    assert ts.name == "testseries A1"

def test_testprogram():
    tpname = "ALU"
    tpname1 = "ALU1"
    tpuuid = "d4e97cedca6238bea16732ce88c1922f"
    tpuuid1 = "d4e97cedca6238bea16732ce88c19221"
    tp = TestProgram(name=tpname,
                     name_testprogram=tpname1,
                     uuid=tpuuid,
                     uuid_testprogram=tpuuid1)
    print(tp.metadata.df.value)
    assert tp.uuid == tpuuid
    assert tp.uuid_testprogram == tpuuid1
    assert tp.name == tpname
    assert tp.name_testprogram == tpname1

    tp = TestProgram(name=tpname,
                     uuid=tpuuid,)
    print(tp.metadata.df.value)
    assert tp.uuid == tpuuid
    assert tp.uuid_testprogram == ""
    assert tp.name == tpname
    assert tp.name_testprogram == "N.N."

def atest_testprogram():
    tp = gen_dummy_testprogram()
    print(tp)
    assert tp.name == "testprogram FOO"
    print(tp.dir())
    exportpath = "/tmp/mytestprogramx"
    tp.to_folder(exportpath, dtype="csv")
    tp.tree_folder(exportpath)
    tp2 = sdata.Data.from_folder(exportpath)
    print(tp)
    print(tp2)
    print(tp2.metadata.to_dataframe())
    exportpath2 = "/tmp/mytestprogramx2"
    tp2.to_folder(exportpath2)
    tp2.tree_folder(exportpath2)
    print()


if __name__ == '__main__':
    # test_test()
    # test_testseries()
    test_testprogram()
    sdata.print_classes()
