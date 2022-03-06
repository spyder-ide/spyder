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

alabaster :
    Error message: [Errno 20] Not a directory: '<path>/Resources/lib/
    python38.zip/alabaster'
astroid :
    ImportError: cannot import name 'context' from 'astroid'
    (<path>/Resources/lib/python38.zip/astroid/__init__.pyc)
blib2to3 :
    File "<frozen zipimport>", line 177, in get_data
    KeyError: 'blib2to3/Users/rclary/Library/Caches/black/20.8b1/
    Grammar3.8.6.final.0.pickle'
debugpy :
    NotADirectoryError: [Errno 20] Not a directory:
    '<path>/Resources/lib/python39.zip/debugpy/_vendored'
docutils :
    [Errno 20] Not a directory: '<path>/Resources/lib/python39.zip/
    docutils/writers/latex2e/docutils.sty'
humanfriendly :
    spyder-terminal plugin
    ModuleNotFoundError: No module named 'humanfriendly.tables'
IPython :
    [IPKernelApp] WARNING | Could not copy README_STARTUP to startup dir.
    Source file
    <path>/Resources/lib/python38.zip/IPython/core/profile/README_STARTUP
    does not exist
jedi :
    jedi.api.environment.InvalidPythonEnvironment: Could not get version
    information for '<path>/Contents/MacOS/python': InternalError("The
    subprocess <path>/Contents/MacOS/python has crashed (EOFError('Ran out
    of input'), stderr=).")
jinja2 :
    No module named 'jinja2.ext'
keyring :
    ModuleNotFoundError: No module named 'keyring.backends.<mod>'
pandas :
    From Variable explorer: KeyError('pandas._libs.interval')
parso :
    jedi.api.environment.InvalidPythonEnvironment: Could not get version
    information for '/Users/rclary/opt/miniconda3/envs/c2w_37/bin/python':
    InternalError("The subprocess /Users/rclary/opt/miniconda3/envs/c2w_37/
    bin/python has crashed (EOFError('Ran out of input'), stderr=).")
PIL :
    Library not loaded: @loader_path/.dylibs/libjpeg.9.dylib
    Note: only applicable to not-Lite build
pkg_resources:
    ImportError: The 'more_itertools' package is required; normally this is
    bundled with this package so if you get this warning, consult the
    packager of your distribution.
pygments :
    ModuleNotFoundError: No module named 'pygments.formatters.latex'
pylint :
    <path>/Contents/MacOS/python: No module named pylint.__main__
pylsp :
    <path>/Contents/MacOS/python: No module named pylsp
    Note: still occurs in alias mode
pylsp_black :
    Mandatory: python-pyls-black >=1.0.0 : None (NOK)
pyls_spyder :
    Mandatory: pyls_spyder >=0.1.1 : None (NOK)
qtawesome :
    NotADirectoryError: [Errno 20] Not a directory: '<path>/Resourses/lib/
    python38.zip/qtawesome/fonts/fontawesome4.7-webfont.ttf'
setuptools :
    Mandatory: setuptools >=49.6.0 : None (NOK)
sphinx :
    No module named 'sphinx.builders.changes'
spyder :
    NotADirectoryError: [Errno 20] Not a directory: '<path>/Resources/lib/
    python38.zip/spyder/app/mac_stylesheet.qss'
spyder_kernels :
    No module named spyder_kernels.console.__main__
spyder_terminal :
    No module named spyder_terminal.server
textdistance :
    NotADirectoryError: [Errno 20] Not a directory: '<path>/Resources/lib/
    python39.zip/textdistance/libraries.json'
"""

# Packages that cannot be in the zip folder
PACKAGES = [
    'alabaster',
    'astroid',
    'blib2to3',
    'debugpy',
    'docutils',
    'humanfriendly',
    'IPython',
    'jedi',
    'jinja2',
    'keyring',
    'pkg_resources',
    'parso',
    'pygments',
    'pylint',
    'pylsp',
    'pylsp_black',
    'pyls_spyder',
    'qtawesome',
    'setuptools',
    'sphinx',
    'spyder',
    'spyder_kernels',
    'spyder_terminal',
    'textdistance',
]

# Packages to exclude
EXCLUDES = []

# modules that py2app misses
INCLUDES = [
    '_sitebuiltins',  # required for IPython help()
    'jellyfish',
    # required for sphinx
    'sphinxcontrib.applehelp',
    'sphinxcontrib.devhelp',
    'sphinxcontrib.htmlhelp',
    'sphinxcontrib.jsmath',
    'sphinxcontrib.qthelp',
    'sphinxcontrib.serializinghtml',
    'platformdirs.macos',  # required for platformdirs
]

SCIENTIFIC = [
    'cython',
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'sympy',
]
