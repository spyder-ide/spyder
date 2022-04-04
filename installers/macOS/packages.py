# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
NOTES
-----
py2app includes all packages in Spyder.app/Contents/Resources/lib/
python<ver>.zip, but some packages have issues when placed there.
The following packages are included in py2app's PACKAGES option so that
they will be placed in Spyder.app/Contents/Resources/lib/python<ver>
instead.

610faff656c4cfcbb4a3__mypyc :
    WARNING - pylsp.config.config - Failed to load pylsp entry point
    'pylsp_black': No module named '610faff656c4cfcbb4a3__mypyc'
blib2to3 :
    WARNING - pylsp.config.config - Failed to load pylsp entry point
    'pylsp_black': cannot import name 'pgen' from 'blib2to3.pgen2'
    WARNING - pylsp.config.config - Failed to load pylsp entry point
    'pylsp_black': [Errno 2] No such file or directory:
        '.../Grammar3.9.9.final.0.pickle'
humanfriendly :
    spyder-terminal plugin
    ModuleNotFoundError: No module named 'humanfriendly.tables'
pathspec :
    WARNING - pylsp.config.config - Failed to load pylsp entry point 'pylsp_black': The 'pathspec>=0.9.0' distribution was not found and is required by black
pkg_resources:
    ImportError: The 'more_itertools' package is required; normally this is
    bundled with this package so if you get this warning, consult the
    packager of your distribution.
pyls_spyder :
    Mandatory: pyls_spyder >=0.1.1 : None (NOK)
pylsp_black :
    Mandatory: python-pyls-black >=1.0.0 : None (NOK)
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
    'pkg_resources',
    'pyls_spyder',
    'pylsp_black',
    'setuptools',
    'spyder',
    'spyder_kernels',
    'spyder_terminal',
]

# Packages to exclude
EXCLUDES = []

# modules that py2app misses
INCLUDES = [
    '610faff656c4cfcbb4a3__mypyc',
    'blackd',
    'pathspec',
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
