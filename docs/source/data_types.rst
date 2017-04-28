Data types
==========

Metadata
--------

Metadata describing EVERY object within the the datastructure.

Attributes
..........

* name
* value
* dtype
* unit
* description

dtypes for attributes
.....................

* int, (int64)
* float, (float32, float64, float128)
* str, (unicode)
* timestamp (datetime.isoformat with timezone)

Core data types
---------------

Data
....

The ``Data`` class is the Base class for all classes within the sdata family. It provides a uuid, a name and the metadata functionality.

Table
.....

The ```Table``` is able to store column based data.

Group
.....

A ``Group`` is a container class to collect different data objects.

Derives data types
------------------

TestProgram
...........

A ``TestProgram`` is a container object for ``TestSeries``.

TestSeries
..........

A ``TestSeries`` is a container object for ``Test`` s.

Test
....

A ``Test`` is a container object for the particular data to a test.
