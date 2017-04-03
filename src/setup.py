# coding: utf-8

import os
import setuptools

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
# def read(fname):
#     return open(os.path.join(os.path.dirname(__file__), fname)).read()



def extract_version():
    init_py = os.path.join(os.path.dirname(__file__), "sdata", "__init__.py")
    with open(init_py) as init:
        for line in init:
            if line.startswith("__version__"):
                d = {}
                exec(line, d)
                return d["__version__"]
        else:
            raise RuntimeError("Missing line starting with '__version__ =' in %s" % (init_py,))


setup_params = dict(
    name="sdata",
    description = ("structured data"),
    version=extract_version(),
    author="Lepy",
    author_email="lepy@mailbox.org",
    url="https://github.com/lepy/sdata",
    license = "LGPL",
    keywords = "data, CDM, Common Data Model, open data, open science",

    # long_description=read('README'),

    packages=setuptools.find_packages(exclude=["tests"]),
    zip_safe=False,

    install_requires=['numpy']
#     # classifiers=[
#         # "Development Status :: 3 - Alpha",
#         # "Topic :: Utilities",
#         # "License :: OSI Approved :: BSD License",
#     # ],

)

if __name__ == "__main__":
    setuptools.setup(**setup_params)
