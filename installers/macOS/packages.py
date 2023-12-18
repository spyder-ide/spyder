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

keyring:
    ModuleNotFoundError: No module named 'keyring.backends.kwallet'
    ModuleNotFoundError: No module named 'keyring.backends.SecretService'
    ModuleNotFoundError: No module named 'keyring.backends.Windows'
    ModuleNotFoundError: No module named 'keyring.backends.chainer'
    ModuleNotFoundError: No module named 'keyring.backends.libsecret'
    ModuleNotFoundError: No module named 'keyring.backends.macOS'
pkg_resources:
    ImportError: The 'more_itertools' package is required; normally this is
    bundled with this package so if you get this warning, consult the
    packager of your distribution.
pygments:
    ModuleNotFoundError: No module named 'pygments.formatters.latex'
pylint_venv:
    Mandatory: pylint_venv >=2.1.1 : None (NOK)
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
"""

# Packages that cannot be in the zip folder
PACKAGES = [
    'blackd',
    'keyring',
    'pkg_resources',
    'pygments',
    'pylint_venv',
    'pyls_spyder',
    'pylsp_black',
    'setuptools',
    'spyder',
    'spyder_kernels',
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
    'openpyxl',
    'pandas',
    'scipy',
    'sympy',
]
