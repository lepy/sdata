Usage examples
==============

Dump and load a pandas dataframe
--------------------------------

.. uml::

    frame "pd.DataFrame()" as dataframe {
    }

    frame sdata [
    sdata.Data()
    ====
    Metadata
    ----
    Dataframe
    ----
    Description
    ]

    cloud {

    file hdf5

    file json

    file xlsx

    file csv

    file html
    }

    frame sdata2 [
    sdata.Data()
    ====
    Metadata
    ----
    Dataframe
    ----
    Description
    ]

    frame sdata_wo_description [
    sdata.Data()
    ====
    Metadata
    ----
    Dataframe
    ----

    ]

    dataframe -right-> sdata

    sdata --> xlsx

    sdata --> hdf5

    sdata --> json

    sdata ..> csv

    sdata --> html

    json --> sdata2
    hdf5 --> sdata2
    csv --> sdata_wo_description
    xlsx --> sdata2

.. code-block:: python

    import logging
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.WARNING, datefmt='%I:%M:%S')

    import os
    import sys
    import numpy as np
    import pandas as pd
    import sdata
    print("sdata v{}".format(sdata.__version__))

    # ## create a dataframe
    df = pd.DataFrame({"a":[1.,2.,3.], "b":[4.,6.,1.]})

    # ## create a Data object
    data = sdata.Data(name="df",
                      uuid=sdata.uuid_from_str("df"),
                      table=df,
                      description="a pandas dataframe",)
    # ## dump the data
    # ### Excel IO
    data.to_xlsx(filepath="/tmp/data1.xlsx")
    data_xlsx = sdata.Data.from_xlsx(filepath="/tmp/data1.xlsx")
    assert data.name==data_xlsx.name
    assert data.uuid==data_xlsx.uuid
    assert data.description==data_xlsx.description
    print(data_xlsx)
    data_xlsx.df

    # ### Hdf5 IO
    data.to_hdf5(filepath="/tmp/data1.hdf")
    data_hdf5 = sdata.Data.from_hdf5(filepath="/tmp/data1.hdf")
    assert data.name==data_xlsx.name
    assert data.uuid==data_xlsx.uuid
    assert data.description==data_hdf5.description
    print(data_hdf5)
    data_hdf5.df

    # ### Json IO
    data.to_json(filepath="/tmp/data1.json")
    data_json = sdata.Data.from_json(filepath="/tmp/data1.json")
    assert data.name==data_json.name
    assert data.uuid==data_json.uuid
    assert data.description==data_json.description
    print(data_json)
    data_json.df

    # ### csv IO
    data.to_csv(filepath="/tmp/data1.csv")
    data_csv = sdata.Data.from_csv(filepath="/tmp/data1.csv")
    assert data.name==data_csv.name
    assert data.uuid==data_csv.uuid
    # assert data.description==data_csv.description
    assert data.df.shape == data_csv.df.shape
    print(data_csv)
    data_csv.df

    # ### html export
    data.to_html(filepath="/tmp/data1.html")


Components of sdata.Data
------------------------

.. uml::

    package "sdata.Data" as sdata {

        frame "Description" as description0 {
        }

        frame "Dataframe" as data0 {
        }

        frame "Metadata" as metadata0 {
        }

    }

.. code-block:: python

    # ## create a Data object
    data = sdata.Data(name="df",
                      table=pd.DataFrame({"a":[1.,2.,3.], "b":[4.,6.,1.]}),
                      description="a pandas dataframe",)

    # Metadata
    data.metadata

    # Dataframe
    data.df

    # Description
    data.description