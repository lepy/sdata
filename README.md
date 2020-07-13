
[![PyPI version](https://badge.fury.io/py/sdata.svg)](https://badge.fury.io/py/sdata)
[![PyPI](https://img.shields.io/pypi/v/sdata.svg?style=flat-square)](https://pypi.python.org/pypi/sdata/)
[![readthedocs](https://readthedocs.org/projects/sdata/badge/?version=latest)](http://sdata.readthedocs.io/en/latest/) 
[![saythanks.io/to/lepy](https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg)](https://saythanks.io/to/lepy) 
[![GitPitch](https://gitpitch.com/assets/badge.svg)](https://gitpitch.com/lepy/sdata/master?grs=github&t=beige)
[![Build Status](https://travis-ci.org/lepy/sdata.svg?branch=master)](https://travis-ci.org/lepy/sdata)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/107e46dc4eee4b58a6ef82fce3043a3e)](https://www.codacy.com/app/lepy/sdata?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=lepy/sdata&amp;utm_campaign=Badge_Grade)
[![Coverage Status](https://coveralls.io/repos/github/lepy/sdata/badge.svg?branch=master)](https://coveralls.io/github/lepy/sdata?branch=master)

# Structured data format (sdata)


## Design goals

* open data format for open science projects
* self describing data
* flexible data structure layout
    * hierarchical data structure (nesting groups, dictionaries)
    * (posix path syntax support?)
* extendable data structure
   * data format versions
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
* (nested data support)

## Example data structure (brain storming)

```
 └─mytestprogram
   |
   ├─metadata.csv
   |
   ├─testseries_c3c63f8094464325bd57623cb5bbe58f
   | |
   | ├─metadata.csv
   | |
   | ├─test_bb507e40663d49cca8264c0ed6751692
   | | |
   | | ├─metadata.csv
   | | |
   | | └─table_d061d7a58b2341128dd95412ff6ab36f
   | |   |
   | |   ├─metadata.csv
   | |   |
   | |   └─d061d7a58b2341128dd95412ff6ab36f.csv
   | |
   | └─test_e574e000f1404f5ebb9aaceb4183dc4c
   |   |
   |   └─metadata.csv
   |
   └─testseries_a6fc7decdb1441518f762e3b5d798ba7
     |
     ├─metadata.csv
     |
     ├─test_b62195ac49b64c9e8cedb7dba52bd539
     | |
     | ├─metadata.csv
     | |
     | ├─table_6322a66775604c32af74039575221fe0
     | | |
     | | ├─metadata.csv
     | | |
     | | └─6322a66775604c32af74039575221fe0.csv
     | |
     | └─table_9bec8c67e09b456f96a9e23b04d9441a
     |   |
     |   ├─metadata.csv
     |   |
     |   └─9bec8c67e09b456f96a9e23b04d9441a.csv
     |
     ├─test_ddc82782f5f0455895145682fe0a70f2
     | |
     | ├─metadata.csv
     | |
     | └─table_ea4fa966bedb4104b9754a4f5f5d8a80
     |   |
     |   ├─metadata.csv
     |   |
     |   └─ea4fa966bedb4104b9754a4f5f5d8a80.csv
     |
     └─test_8796c35b2e3a4f8a82af181698c15861
       |
       ├─metadata.csv
       |
       └─table_60a90898f0c94b23984b174a74a2a47a
         |
         ├─metadata.csv
         |
         └─60a90898f0c94b23984b174a74a2a47a.csv

```

## Metadata

### Attributes

* name
* value
* dtype
* unit
* description

### dtypes for attributes

* int
* float
* str
* timestamp (datetime.isoformat with timezone)




Each object has a metadata file.

## Data model

The data model is orientated to the common data model, cp. https://www.unidata.ucar.edu/software/thredds/current/netcdf-java/CDM/

* http://datashape.pydata.org/overview.html

## Links

* http://semver.org
* https://docs.python.org/2/library/mimetypes.html
* https://wiki.asam.net/display/STANDARDS/ASAM+ODS
* http://www.bioinformatics.org/bradstuff/bc/IntroPythonClient.pdf
* https://datahub.io/docs/data-packages/publish-faq#examples
