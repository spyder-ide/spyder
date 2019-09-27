#!/usr/bin/env python
from setuptools import setup

VERSION = '3.0.0'
DESCRIPTION = "Bloom filter: A Probabilistic data structure"
LONG_DESCRIPTION = """
This bloom filter is forked from pybloom, and its tightening ratio is changed to 0.9, and this ration is consistently used. Choosing r around 0.8 - 0.9 will result in better average space usage for wide range of growth, therefore the default value of model is set to LARGE_SET_GROWTH.
This is a Python implementation of the bloom filter probabilistic data
structure. The module also provides a Scalable Bloom Filter that allows a
bloom filter to grow without knowing the original set size.
"""

CLASSIFIERS = filter(None, map(str.strip,
"""
Intended Audience :: Developers
License :: OSI Approved :: MIT License
Programming Language :: Python
Programming Language :: Python :: 3
Operating System :: OS Independent
Topic :: Utilities
Topic :: Database :: Database Engines/Servers
Topic :: Software Development :: Libraries :: Python Modules
""".splitlines()))

setup(
    name="pybloom_pyqt",
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    classifiers=CLASSIFIERS,
    keywords=('data structures', 'bloom filter', 'bloom', 'filter', 'big data',
              'probabilistic', 'set'),
    author="Jay Baird",
    author_email="jay.baird@me.com",
    url="https://github.com/joseph-fox/python-bloomfilter",
    license="MIT License",
    platforms=['any'],
    test_suite="pybloom_pyqt.tests",
    zip_safe=True,
    install_requires=['PyQt5 ==5.9.2'],
    packages=['pybloom_pyqt']
)
