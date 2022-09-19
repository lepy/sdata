#!/bin/bash
cd ~/projects/sdata
rm dist/*.tar.gz
rm dist/*.egg
python setup.py sdist
#export TWINE_USERNAME=''
#export TWINE_PASSWORD=''
twine upload dist/*
