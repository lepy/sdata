# sdata

structured data format

## design goals

* open data format
* self describing data
    * support of standard metadata
* support of a hierarchical data structure
* support of standard data formats (hdf5, netcdf, csv, ...)
* support of datacubes, tables, series
* flexible data structure
* easy defineable standards, e.g. for a tension test
* transparent, optional data compression (zlib, blosc, ...)
* optional data encryption

## Example data structure (brain storming)

```
    testprogram_a
    ├── metadata.csv
    └── testseries_ut_a
        ├── test_ut_a_001
        │   ├── data
        │   │   ├── fs.csv
        │   │   ├── fs_metadata.csv
        │   │   ├── gom.csv
        │   │   ├── gom_metadata.csv
        │   │   └── metadata.csv
        │   ├── documents
        │   │   ├── report.pdf
        │   │   └── metadata.csv
        │   ├── pictures
        │   ├── movies
        │   └── metadata.csv
        └── test_ut_a_002
            └── metadata.csv

```

Each object has a metadata file.

## Data model

The data model is orientated to the common data model, cp. https://www.unidata.ucar.edu/software/thredds/current/netcdf-java/CDM/
