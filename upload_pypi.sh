#!/bin/bash
cd ~/projects/sdata
rm dist/*.tar.gz
python setup.py sdist upload
twine upload dist/*

