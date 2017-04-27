Design goals
------------

* open data format for open science projects
* self describing data
* flexible data structure layout

    * hierarchical data structure (nesting groups, dictionaries)
    * (posix path syntax support?)

* extendable data structure
* platform independent
* simple object model
* support of standard metadata formats (key/value, ...)
* support of standard dataset formats (hdf5, netcdf, csv, ...)
* support of standard dataset types (datacubes, tables, series, ...)
* support of physical units (conversion of units)
* transparent, optional data compression (zlib, blosc, ...)
* support of (de-)serialization of every dataset type (group, data, metadata)
* easy defineable (project) standards, e.g. for a uniaxial tension test (UT)
* (optional data encryption (gpg, ...))
* change management support?
* Enable use of data structures from existing tensor libraries transparently
* (single writer/ multiple reader (swmr) support)
* (nested table support)