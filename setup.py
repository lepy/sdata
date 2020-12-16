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

REQUIRES = ['numpy', 'pandas', 'tabulate', 'xlrd', 'openpyxl', 'xlsxwriter', 'pytz', 'requests']

setup(
    name='sdata',
    version=version,
    description='a structured data format',
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Lepy",
    author_email="lepy@mailbox.org",
    maintainer='Lepy',
    maintainer_email='lepy@mailbox.org',
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
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],

    install_requires=REQUIRES,
    tests_require=['coverage', 'pytest'],
    test_suite = 'tests',
    packages=find_packages(),
)
