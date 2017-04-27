---

# sdata
## an open structured data format


---

## Design goals I/III

* open data format for open science projects
* self describing data
* flexible data structure layout
    * hierarchical data structure (nesting groups, dictionaries)
    * (posix path syntax support?)
* extendable data structure
* platform independent

+++

## Design goals II/III

* simple object model
* support of standard metadata formats (key/value, ...)
* support of standard dataset formats (hdf5, netcdf, csv, ...)
* support of standard dataset types (datacubes, tables, series, ...)
* support of physical units (conversion of units)
* transparent, optional data compression (zlib, blosc, ...)

+++

## Design goals III/III

* support of (de-)serialization of every dataset type (group, data, metadata)
* easy defineable (project) standards, e.g. for a uniaxial tension test (UT)
* (optional data encryption (gpg, ...))
* change management support?
* Enable use of data structures from existing tensor libraries transparently
* (single writer/ multiple reader (swmr) support)

---

## Example data structure

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

---

## Metadata

### Attributes

* name
* value
* dtype
* unit
* description

---

### dtypes for attributes

* int, (int32, int64)
* float, (float32, float64, float128)
* str, (unicode)
* timestamp (= datetime.isoformat with timezone)

---

# The End
