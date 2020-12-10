
[![PyPI version](https://badge.fury.io/py/sdata.svg)](https://badge.fury.io/py/sdata)
[![PyPI](https://img.shields.io/pypi/v/sdata.svg?style=flat-square)](https://pypi.python.org/pypi/sdata/)
[![readthedocs](https://readthedocs.org/projects/sdata/badge/?version=latest)](http://sdata.readthedocs.io/en/latest/) 
[![Build Status](https://travis-ci.org/lepy/sdata.svg?branch=master)](https://travis-ci.org/lepy/sdata)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/107e46dc4eee4b58a6ef82fce3043a3e)](https://www.codacy.com/app/lepy/sdata?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=lepy/sdata&amp;utm_campaign=Badge_Grade)
[![Coverage Status](https://coveralls.io/repos/github/lepy/sdata/badge.svg?branch=master)](https://coveralls.io/github/lepy/sdata?branch=master)
[![Das sdata-Format v0.8.4](https://zenodo.org/badge/DOI/10.5281/zenodo.4311323.svg)](https://doi.org/10.5281/zenodo.4311323)

https://lepy.github.io/sdata/

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
## Howto

  
* [Das sdata-Format - slides](https://lepy.github.io/sdata/ipynb/Das_sdata_Format.slides.html#)


## Demo App

* [test the demo app with editor](https://share.streamlit.io/lepy/sdata_streamlit/main/sdata_editor.py)

Try to paste some Excel-Data in the forms ...


## Metadata

### Attributes

* name
* value
* dtype
* unit
* description
* label

### dtypes for attributes

* int
* float
* str
* bool
* timestamp (datetime.isoformat with timezone)

## paper

* [Das sdata-Format](https://zenodo.org/record/4311323#.X89yo9-YXys)
    * Ingolf Lepenies. (2020). Das sdata-Format (Version 0.8.4). http://doi.org/10.5281/zenodo.4311323 
    * [slides](https://lepy.github.io/sdata/ipynb/Das_sdata_Format.slides.html#),
    [html](https://lepy.github.io/sdata/paper/2020/Das_sdata-Format.html), 
    [pdf](https://lepy.github.io/sdata/paper/2020/Das_sdata-Format.pdf)
    [temperaturmessung-001.json](https://lepy.github.io/sdata/paper/2020/temperaturmessung-001.json)
    [temperaturmessung-001.xlsx](https://lepy.github.io/sdata/paper/2020/temperaturmessung-001.xlsx)
    
* [sdata](https://doi.org/10.5281/zenodo.4311396)
    * Ingolf Lepenies. (2020, December 8). sdata - a structured data format (Version 0.8.4). Zenodo. http://doi.org/10.5281/zenodo.4311397

