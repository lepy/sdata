
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

```
df = pandas.DataFrame({"a":[1,2,3]})
import sdata
data = sdata.Data(name="my_data", table=df, comment="A remarkable comment")
data.metadata.add("my_key", 123, unit="m^3", description="a volume")
data.metadata.add("force", 1.234, unit="kN", description="x force")
data.to_xlsx(filepath="my_data.xlsx")
print(data.metadata.df)
```

```
          name                             value  dtype unit description
key                                                                     
name      name                           my_data    str    -            
uuid      uuid  08222ca66e5047808bdc3b35d8f17224    str    -            
my_key  my_key                               123    int  m^3    a volume
force    force                             1.234  float   kN     x force
```


[test the demo app](https://share.streamlit.io/lepy/sdata_streamlit/main/sdata_editor.py)

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
* bool
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
