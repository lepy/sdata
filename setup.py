from setuptools import find_packages, setup

with open('sdata/__init__.py', 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.strip().split('=')[1].strip(' \'"')
            break
    else:
        version = '0.0.1'

with open('README.md', 'rb') as f:
    readme = f.read().decode('utf-8')

REQUIRES = ['numpy', 'pandas', 'tabulate', 'xlrd', 'openpyxl', 'xlsxwriter', 'pytz', 'Pillow', 'suuid>=0.2.0']

# Optionale Abhängigkeiten:
#   pip install "sdata[did]"   DID-/VC-Subpackage (sdata.did)
#   pip install "sdata[hdf]"   HDF5-I/O (PyTables-Backend)
#   pip install "sdata[sql]"   to_sqlite / pandas.to_sql (SQLAlchemy)
EXTRAS = {
    # sdata.did ist abhängigkeitsfrei (Ed25519 + base58btc als pure Python).
    # Extra bleibt als no-op erhalten, damit 'pip install sdata[did]' weiter funktioniert.
    'did': [],
    # Optionales HTTP-Backend: ohne 'requests' nutzt sdata einen urllib-Fallback
    # (Standardbibliothek). 'requests' bietet certifi-CA-Bundle/Connection-Pooling.
    'http': ['requests'],
    'hdf': ['tables'],
    'sql': ['sqlalchemy'],
    'parquet': ['pyarrow'],   # sdata.sclass.DataFrame (Parquet-Serialisierung)
    'blob': ['fsspec'],       # sdata.sclass.Blob (URI-Content: file/S3/Zip)
}

setup(
    name='sdata',
    version=version,
    description='a structured data format',
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Lepy",
    author_email="lepy@tuta.io",
    maintainer='Lepy',
    maintainer_email='lepy@tuta.io',
    url="https://github.com/lepy/sdata",
    license='MIT/Apache-2.0',

    keywords=[
        'open data',
    ],

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    python_requires='>=3.7',

    install_requires=REQUIRES,
    extras_require=EXTRAS,
    tests_require=['coverage', 'pytest', 'requests'],
    test_suite = 'tests',
    packages=find_packages(),
)
