# -*- coding: utf-8 -*-

from sdata.io.vault import Vault, VaultIndex
from sdata import Data
import pandas as pd
import numpy as np

def test_vault_index():
    vi = VaultIndex()
    assert isinstance(vi.df, pd.DataFrame)
    print(vi.df.columns)
    print(sorted(vi.df.columns)==sorted(Data.SDATA_ATTRIBUTES))
    assert sorted(vi.df.columns)==sorted(Data.SDATA_ATTRIBUTES)
    assert 1
