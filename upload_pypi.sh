#!/bin/bash
cd ~/projects/sdata
rm dist/*.tar.gz
python setup.py sdist
#export TWINE_USERNAME=''
#export TWINE_PASSWORD=''
twine upload dist/*
