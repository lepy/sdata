import sdata.tools


def test_col_to_idx():
    print(sdata.tools.col_to_idx("aB"))
    assert sdata.tools.col_to_idx("aB") == 27
