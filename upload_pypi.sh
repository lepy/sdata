#!/bin/bash
cd ~/projects/sdata/src
rm dist/*.tar.gz
python setup.py sdist upload
twine upload dist/*

