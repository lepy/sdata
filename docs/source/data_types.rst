Data types
==========

Metadata
--------

Metadata describing EVERY object within the the datastructure.

Attributes
..........

* ``name`` .. Name of an attribute (``str``)
* ``value`` .. Value of an attribute
* ``dtype`` .. data type of the attribute (default: ``str``)
* ``unit`` .. physical unit of an attribute (optional)
* ``description`` .. a description of an attribute (optional)
* ``label`` .. an fancy label of an attribute , e.g. for plotting (optional)

.. code-block:: python
    :linenos:

    import sdata
    attribute1 = sdata.Attribute("color", "blue")
    attribute1

.. code-block:: none

    (Attr'color':blue(str))

.. code-block:: python
    :linenos:

    attribute2 = sdata.Attribute(name="answer",
                                 value=42,
                                 dtype="int",
                                 unit="-",
                                 description="""The Answer to the Ultimate Question of Life, The Universe, and Everything""",
                                 label="Die Antwort")
    attribute2.to_dict()

.. code-block:: none

    {'name': 'answer',
     'value': 42,
     'unit': '-',
     'dtype': 'int',
     'description': 'The Answer to the Ultimate Question of Life, The Universe, and Everything',
     'label': 'Die Antwort'}

dtypes for attributes
.....................

* ``int``, (int64)
* ``float``, (float32, float64, float128)
* ``str``, (unicode)
* ``bool``
* ``timestamp`` (datetime.isoformat with timezone)
* (``uuid`` planed)

sdata.metadata
..............

.. code-block:: python
    :linenos:

    metadata = sdata.Metadata()
    metadata.add(attribute1)
    metadata.add(attribute2)
    print(metadata)
    metadata.df

.. code-block:: none

                            name  value dtype unit                                        description        label
    key                                                                                                            
    sdata_version  sdata_version  0.8.4   str    -                                                                 
    Augenfarbe             color   blue   str    -                                                                 
    answer                answer     42   int    -  The Answer to the Ultimate Question of Life, T...  Die Antwort 

.. code-block:: python
    :linenos:

    data = sdata.Data(name="basic example", uuid="38b26864e7794f5182d38459bab85842", table=df)
    data.metadata.add("Temperatur",
                      value=25.4,
                      dtype="float",
                      unit="degC",
                      description="Temperatur",
                      label="Temperatur T [°C]")
    data.metadata.df

.. code-block:: none

                            name                             value  dtype  unit  description              label
    key                                                                                                        
    sdata_version  sdata_version                             0.8.4    str     -                                
    name                    name                     basic example    str     -                                
    uuid                    uuid  38b26864e7794f5182d38459bab85842    str     -                                
    Temperatur        Temperatur                              25.4  float  degC   Temperatur  Temperatur T [°C]


Core data types
---------------

Data
....

The ``Data`` class is the Base class for all classes within the sdata family. It provides a uuid, a name and the metadata functionality.
It can group other Data objects. A Data object can store one pandas.DataFrame.


.. code-block:: python
    :linenos:

    import sdata
    data = sdata.Data(name="my data name", table=df, description="my data description")


.. code-block:: python
    :linenos:

    df = pd.DataFrame({"time": [1.1, 2.1, 3.5],
                       "temperature": [2.4, 5.2, 2.2]},

    data_name = "Temperaturmessung-001"
    data = sdata.Data(name=data_name,
                      uuid=sdata.uuid_from_str(data_name),
                      table=df,
                      description="Messergebnis Temperatur")
    data.metadata.add("time",
                      value=None,
                      dtype="float",
                      unit="s",
                      description="Zeitachse",
                      label="time $t$")
    data.metadata.add("temperature",
                      value=None,
                      dtype="float",
                      unit="°C",
                      description="Zeitachse",
                      label="temperature $T$")
    data.describe()


.. code-block:: python
    :linenos:

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()

    x_var = "time"
    y_var = "temperature"

    x_attr = data.metadata.get(x_var)
    y_attr = data.metadata.get(y_var)

    ax.plot(data.df[x_var], data.df[y_var], label=data.name)
    ax.legend(loc="best")
    ax.set_xlabel("{0.label} [{0.unit}]".format(x_attr))
    ax.set_ylabel("{0.label} [{0.unit}]".format(y_attr))
    print("plot")
