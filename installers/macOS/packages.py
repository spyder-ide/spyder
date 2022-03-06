#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOTES
-----
py2app includes all packages in Spyder.app/Contents/Resources/lib/
python<ver>.zip, but some packages have issues when placed there.
The following packages are included in py2app's PACKAGES option so that
they will be placed in Spyder.app/Contents/Resources/lib/python<ver>
instead.

blib2to3 :
    File "<frozen zipimport>", line 177, in get_data
    KeyError: 'blib2to3/Users/rclary/Library/Caches/black/20.8b1/
    Grammar3.8.6.final.0.pickle'
humanfriendly :
    spyder-terminal plugin
    ModuleNotFoundError: No module named 'humanfriendly.tables'
jinja2 :
    No module named 'jinja2.ext'
keyring :
    ModuleNotFoundError: No module named 'keyring.backends.<mod>'
PIL :
    Library not loaded: @loader_path/.dylibs/libjpeg.9.dylib
    Note: only applicable to not-Lite build
pkg_resources:
    ImportError: The 'more_itertools' package is required; normally this is
    bundled with this package so if you get this warning, consult the
    packager of your distribution.
pylint :
    <path>/Contents/MacOS/python: No module named pylint.__main__
pylsp_black :
    Mandatory: python-pyls-black >=1.0.0 : None (NOK)
pyls_spyder :
    Mandatory: pyls_spyder >=0.1.1 : None (NOK)
setuptools :
    Mandatory: setuptools >=49.6.0 : None (NOK)
spyder :
    NotADirectoryError: [Errno 20] Not a directory: '<path>/Resources/lib/
    python38.zip/spyder/app/mac_stylesheet.qss'
spyder_kernels :
    No module named spyder_kernels.console.__main__
spyder_terminal :
    No module named spyder_terminal.server
"""

# Packages that cannot be in the zip folder
PACKAGES = [
    'blib2to3',
    'humanfriendly',
    'jinja2',
    'keyring',
    'pkg_resources',
    'pylint',
    'pylsp_black',
    'pyls_spyder',
    'setuptools',
    'spyder',
    'spyder_kernels',
    'spyder_terminal',
]

# Packages to exclude
EXCLUDES = []

# modules that py2app misses
INCLUDES = [
    'jellyfish',
    'pylsp',
]

SCIENTIFIC = [
    'cython',
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'sympy',
]
