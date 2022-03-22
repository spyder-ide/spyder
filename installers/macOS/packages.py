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

humanfriendly :
    spyder-terminal plugin
    ModuleNotFoundError: No module named 'humanfriendly.tables'
pkg_resources:
    ImportError: The 'more_itertools' package is required; normally this is
    bundled with this package so if you get this warning, consult the
    packager of your distribution.
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
    'humanfriendly',
    'pkg_resources',
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


def patch_py2app():
    """
    Patch py2app PyQt recipe and site.py for version 0.27.
    Remove after version 0.28 is available.
    """
    from importlib.util import find_spec
    from importlib.metadata import version
    from packaging.version import parse
    from pathlib import Path

    from setup import logger

    logger.info('Patching py2app')

    py2app_ver = version('py2app')
    if parse(py2app_ver) > parse('0.27'):
        raise DeprecationWarning(f'py2app version {py2app_ver} > 0.27; '
                                 'stop using patch_py2app.')

    root = Path(find_spec('py2app').origin).parent

    # Patch site.py
    site_file = root / 'apptemplate' / 'lib' / 'site.py'
    append_text = ("builtins.quit = "
                   "_sitebuiltins.Quitter('quit', 'Ctrl-D (i.e. EOF)')\n"
                   "builtins.exit = "
                   "_sitebuiltins.Quitter('exit', 'Ctrl-D (i.e. EOF)')\n")
    text = site_file.read_text()
    if append_text not in text:
        site_file.write_text(text + append_text)

    # Patch qt5.py
    qt5_file = root / 'recipes' / 'qt5.py'
    search_text = "if qtdir != os.path.dirname(PyQt5.__file__):"
    replace_text = "if os.path.dirname(PyQt5.__file__) not in qtdir:"
    text = qt5_file.read_text()
    if replace_text not in text:
        qt5_file.write_text(text.replace(search_text, replace_text))


patch_py2app()
