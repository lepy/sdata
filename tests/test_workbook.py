# -*- coding: utf-8 -*-

import sdata
from sdata.workbook import Workbook
import pandas as pd
import numpy as np

def test_blob():
    wb = Workbook(name="workbook",
                  description="A excel like workbook",
                  )
    print(wb)
    assert wb.name == "workbook"


    s0 = wb.create_sheet(1)
    assert s0 is None

    df1 = pd.DataFrame([1, 2, 3])
    s1 = wb.create_sheet("df1")
    s1.df = df1
    assert s1.name == "df1"
    s1.describe()

    data2 = sdata.Data(name="data2", df=pd.DataFrame({"a": [1, 2, 3]}))
    wb.add_sheet(data2)
    assert data2 in wb
    assert "data2" in wb.sheetnames

    s3 = wb.add_sheet(1)
    assert s3 is None

    print(wb.sheetnames)
    assert wb.sheetnames == ['df1', 'data2']

    assert len(wb.sheets)==2