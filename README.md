# Structured data format (sdata)

## Design goals

* open data format for open data and open science projects
* self describing data
* hierarchical data structure
* support of standard metadata formats
* support of standard data formats (hdf5, netcdf, csv, ...)
* support of datacubes, tables, series
* support of physical units
* flexible data structure layout
* extendable data structure
* easy defineable (project) standards, e.g. for a uniaxial tension test (UT)
* support of (de-)serialization of every data type (group, data, metadata)
* transparent, optional data compression (zlib, blosc, ...)
* (optional data encryption (gpg, ...))
* change management support?

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
