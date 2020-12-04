import sys
import os

modulepath = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(modulepath, "..", "..", "src"))

#["name", "value", "dtype", "unit", "description", "required"]
ks2specimen_default_attributes = [
    ["rd", None, "float", "deg", "rolling direction", True],
    ["t", None, "float", "mm", "thickness sheet", True],
    ["r", None, "float", "mm", "bending radius sheet", True],
    ["bi", None, "float", "mm", "inner width", True],
    ["hi", None, "float", "mm", "inner height", True],
    ["l", None, "float", "mm", "length", True],
    ]

#["name", "value", "dtype", "unit", "description", "required"]
ks2test_default_attributes = [
    ["angle", None, "float", "deg", "loading angle", True],
    ]

#["name", "value", "dtype", "unit", "description"]
material_default_attributes = [
    ["material_type", None, "str", "-", "Material type, e.g. alu|steel|plastic|wood|glas|foam|soil|...", True],
    ["material_grade", "-", "str", "-", "Material grade, e.g. T4", False],
    ]

material_default_attributes = [
    ["rd", None, "float", "deg", "rolling direction", True],
    ["t", None, "float", "mm", "thickness sheet", True],
    ["l", None, "float", "mm", "length", True],
    ["w", None, "float", "mm", "width", True],
]

import sdata
# import sdata.test
# import sdata.experiments.ks2
import pandas as pd
import numpy as np

def _fixed_uuid():
    fixed_uuids=['60a90898f0c94b23984b174a74a2a47a', '6322a66775604c32af74039575221fe0', '9bec8c67e09b456f96a9e23b04d9441a', 'ea4fa966bedb4104b9754a4f5f5d8a80', 'd061d7a58b2341128dd95412ff6ab36f', 'e4130bc9719e42dd9149e24ab7169398', '8b534e9795624650828be6f39828c153', '82212590f1c2420e8066d9d4e84dbd48', '37f5a429a2a1471d99b342fb95a8d16e', '96a550261de64848b128f982803f2daf', 'e3172927f41c4cfa96f71d76cd59b1e9', 'ba6ea9a119e84e95b304219e009c61a8', 'c161746eef1c4caf9e34f611e9dc4d5d', 'b7dc0d91def94a74ade3767e6a7fc27b', '4253242656e84463807f454b59fcb210', 'de60b7b98bb943ae801f43ccb102d47c', '923e2ef4319e4788a7ed06df7d1940c0', 'cc67e24c09a14d96aace36770d7c7253', 'f81f468b80c2428cae375d4dde321749', 'ea1ba03b578f47839f65a6804e8df1aa', 'f1a62a91b6384c6aa8163f4f2731dc90', '38b1eb86216048238fce60d262eb433c', '9fb394da4a274c7191d549980a3fc5e4', 'f5376c16774e4e8cb3701b54b275663a', '24b4b16be47f4a53ad07c9c3065e4721', '2403e75fb44a45cdae716d807d10a23f', 'a89c49ea00924d19a959d3246d1555b0', '8a17ac6db7f248b8ab48f33e9c68e642', 'ba1e75fac4c54244bdf894c90c5c9433', '7c090410e84747a39230bbfb677feb4b', '71827185aa2b48eea00eca4b29ea360b', 'eaf70185ef52492eb166368dedf8c293', 'e296ecaa56f14b199597dc110e3295df', 'eb885e0e50d047e2b176df6f9537338c', 'd94c000fe9dd4e7cb7b92c2eb88fab58', '4f6a7eb6ec184f828e61cb58bde3ae38', '31bc7501c9554b42b1d537f7b1c3b7c2', '07a670df750649a58c4f3550a4fff568', '85ab8c8694ef40e49d626e768a234323', '5425056193aa4eceae3284e1025be685', '2092edfc1ef442b1b8ccdfa8e3d80942', '60e0a331aae94bc5be69d9554972a2eb', '143bae95ef054e309660f8ac7b821e61', 'e8949cc7d39b4241aa5ddae63392747a', 'efba81a764304b379522a0b04b5c8e51', '70717fcec2fd46169ce645f0ef1e2838', '5a92c55dc9e84eb686dc2c962d21260e', '6730db061a05419e9b2860a215a3d511', 'd8f85fb0b4cd4a858b68621c2a0c2544', '126fffa1dbd54ea58076f152f7b3aa4a', '1b9daeff4ac04bdba483231cfe2f2928', 'a3fd969dd9ca4a4098b83c8a9a1322f0', 'daac5f2b7a1248fc8f3e0aad95eb7a8b', 'ca257d83bb3442d59c9c641ca54ce437', '447f48c0e24848e3bdc58eb4e90eef94', '8d0d4544dc264fbcb18d3954a9707a59', '0dc66d06054d4e65aebd1a7cd7b61f02', '8946db8393be4b7ebb982f1fc6b66b58', '222b02610b564b339cefba9229a6dc69', '9c46d6ff4ce44ae49f169c1b6b4cd136', '87aed4b0d3004593a8f7abd9b5011375', '5836150560d449fa9fb1e6ece43914c1', 'b926c2c318a042c58070d94f3074f9fa', '3cb3cebb0ba242b69c862e4d64c6e594', 'b12d51a756254606b299559b6e115d46', '5c73c9ed582c4aacab8c55ed82af1d5e', '464933693a8f45bdba4460e418044afe', '31f59ead75414a58b235d1fc5c1d8054', '1945ead3bf844c1fb4dc726e4f665ef5', 'cf82de1361b34d90aee21d190cd8fb28', 'e58513ab1516481e91114c4481c9c62a', 'f9b67376adb0469aa5a06723617c64a2', '05b8ca9b26f44a0cb2eaeee860caeabf', 'e649b9a64cbc48859537d2c3449f7095', '0dd448f82cdc427c96c2c940b044a46c', '65e0629b1a7040c4a8443d58ffc1aa3a', '62a4142dd2744a698cda373e7af4ad92', '120eff225b394c88bac9153638ddeda0', '4a48f820e60c432488be68174248cb24', '9dcf98ed8f04481aa4793e6e7303f615', '8beae3f5adb041a4a903d4fe01745345', '42acc26c1afc44669543f9b9b0626366', 'e98c2f050a75438cbe7c520493a00ffe', '2c4da182e2c54ead977e55c8e0e58686', '07ef87f1889c450ab3ed7a29519f0a84', 'dbd8a04eb6794a1b9a66a1e0f53c08b0', '1f6c577dc78e41bd819a69a3e67d0267', '3213a345ec15440b8812b47f94987b38', '024725091cd64a86be390ba649a473ae', '61e34f60c7f848f7aa83b84964fddb4e', '5ea58d41726448df9ab1f09967873b8a', 'e4b8485737574c82b0c0e86aef01f377', '62f7f9738e0141cfb3bf2e8ae10a28a9', 'ad04dc26ea784809aae39d6adc9817f7', '58724a5ba7a64c61a9e9c7c4306f0bf2', '8af74b40b501461296f9412b6904168f', '15c659ba99ae44ea9dfcf65fed76fa0c', 'bd80ad679d954ae18a1bb1cc60097b9a', '0e4f0d796d574173b26a07dcc961c5ea', 'ffa78242021d4951993f2f027bfb2921']
    for uid in fixed_uuids:
        yield uid

fixed_uuid =_fixed_uuid()

def atest_ks2_full():
    tp = sdata.Data("what")
    tp.to_folder("/tmp/tp_ks2")
    # sdata.testprogram.TestProgram.clear_folder("/tmp/tp_ks2")
    tp = sdata.Data.from_folder("/tmp/tp_ks2")
    tp.clear_group()
    tp.add_data(sdata.Data(name="materials"))
    tp.add_data(sdata.Data(name="parts"))
    print(tp.group)
    materials = tp.get_data_by_name("materials")
    parts = tp.get_data_by_name("parts")
    print(parts)
    # Material 1
    mat1 = sdata.Data(name="HX340LAD", default_attributes=material_default_attributes)
    mat1.metadata.set_attr("material_type", "steel")
    # print(mat1.metadata)
    invalid_attrs = mat1.verify_attributes()
    print(invalid_attrs)
    assert len(invalid_attrs)==0
    # print(mat1.metadata.to_dataframe())
    materials.add_data(mat1)

    # Material 2
    mat2 = sdata.Data(name="AW6016", default_attributes=material_default_attributes)
    mat2.metadata.set_attr("material_type", "alu")
    mat2.metadata.set_attr("material_grade", "T4")
    materials.add_data(mat2)

    # Part 1
    part1 = sdata.Data(name="upper sheet", default_attributes=ks2specimen_default_attributes)
    part1.metadata.set_attr("material_uuid", mat1.uuid)
    invalid_attrs = part1.verify_attributes()
    print(invalid_attrs)
    # assert len(invalid_attrs)>0
    part1.metadata.set_attr("rd", 0)
    part1.metadata.set_attr("t", 1.1)
    part1.metadata.set_attr("r", 2)
    part1.metadata.set_attr("bi", 34.)
    part1.metadata.set_attr("hi", 29.)
    part1.metadata.set_attr("l", 50.)
    invalid_attrs = part1.verify_attributes()
    print(invalid_attrs)
    assert len(invalid_attrs)==0
    parts.add_data(part1)

    # Part 2
    part2 = sdata.Data(name="bottom sheet", default_attributes=ks2specimen_default_attributes)
    print("!!!", part2.osname)
    part2.metadata.set_attr("material_uuid", mat1.uuid)
    print(part2.metadata.get_attr("t"))
    part2.metadata.set_attr("material_uuid", mat2.uuid)
    part2.metadata.set_attr("rd", 0)
    # part2.metadata.get_attr("t").value=2.0
    part2.metadata.set_attr("r", 4)
    part2.metadata.set_attr("bi", 34.)
    part2.metadata.set_attr("hi", 29.)
    part2.metadata.set_attr("l", 50.)

    invalid_attrs = part2.verify_attributes()
    print(invalid_attrs)
    assert len(invalid_attrs)==0
    parts.add_data(part2)

    # KS2 Test Series 1
    ts1 = sdata.Data(name="KS2 Series A1")
    tp.add_data(ts1)

    # KS2 Test 1
    ks2 = sdata.Data(name="KS2 test A1", parts=[part1, part2], default_attributes=ks2test_default_attributes)
    ks2.name = "KS2 Test A1"
    print("ks2test", ks2)
    assert ks2.name=="KS2 Test A1"
    print("ks2test", ks2.metadata)
    ks2.metadata.set_attr("angle", 30.)
    print(ks2.metadata.get_attr("t3"))
    ts1.add_data(ks2)

    # Test Result Table for KS2 Test 1
    df = pd.DataFrame(np.random.random((10,3)), columns=["a", "b", "c"])
    table = sdata.Data(name="Fs", desciption="Force Displacement Relation")
    table.table = df
    table.metadata.set_attr(name="a", value="Column a", description="bar")
    table.metadata.set_attr(name="b", value="Column a", description="bar", unit="kN")
    table.metadata.set_attr(name="c", value="Column a", description="bar", unit="mm")
    ks2.add_data(table)



    tp.to_folder("/tmp/tp_ks2")
    tp2 = sdata.Data.from_folder("/tmp/tp_ks2")
    tp2.to_folder("/tmp/tp_ks2a")
    tp2.tree_folder("/tmp/tp_ks2a")
    print(tp.dir())

# def test_ks2():
    tp = sdata.Data.from_folder("/tmp/tp_ks2")
    tp.name = "KS2-testprogram"
    tp.to_folder("/tmp/tp_ks2")

    tp2 = sdata.Data.from_folder("/tmp/tp_ks2")
    tp2.to_folder("/tmp/tp_ks2a")
    tp2.tree_folder("/tmp/tp_ks2a")



if __name__ == '__main__':
    test_ks2_full()
