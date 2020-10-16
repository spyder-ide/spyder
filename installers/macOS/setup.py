# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Create a stand-alone macOS app using py2app

To be used like this:
$ python setup.py py2app

NOTES
-----
py2app includes all packages in Spyder.app/Contents/Resources/lib/python38.zip
but some packages have issues when placed there.
The following packages are included in py2app's PACKAGES option so that they
will be placed in Spyder.app/Contents/Resources/lib/python38 instead.

alabaster :
    Error message: [Errno 20] Not a directory: '<path>/Resources/lib/
    python38.zip/alabaster'
astroid :
    ImportError: cannot import name 'context' from 'astroid'
    (<path>/Resources/lib/python38.zip/astroid/__init__.pyc)
ipykernel :
    ModuleNotFoundError: No module named 'ipykernel.datapub'
ipython :
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
parso :
    NotADirectoryError: [Errno 20] Not a directory:
    '<path>/Resources/lib/python38.zip/parso/python/grammar38.txt'
pygments :
    ModuleNotFoundError: No module named 'pygments.formatters.latex'
pyls :
    <path>/Contents/MacOS/python: No module named pyls
    Note: still occurs in alias mode
qtawesome :
    NotADirectoryError: [Errno 20] Not a directory: '<path>/Resourses/lib/
    python38.zip/qtawesome/fonts/fontawesome4.7-webfont.ttf'
spyder :
    NotADirectoryError: [Errno 20] Not a directory: '<path>/Resources/lib/
    python38.zip/spyder/app/mac_stylesheet.qss'
spyder_kernels :
    No module named spyder_kernels.console.__main__
sphinx :
    No module named 'sphinx.builders.changes'

"""

import os
import sys
import shutil
import argparse
import pkg_resources
from logging import getLogger, StreamHandler, Formatter
from setuptools import setup
from dmgbuild import build_dmg

# parse additional arguments for setup.py
parser = argparse.ArgumentParser()
parser.add_argument('--lite', dest='make_lite', action='store_true',
                    default=False, help='Build with minimal internal packages')
parser.add_argument('--dmg', dest='make_dmg', action='store_true',
                    default=False, help='Create DMG')

# parse additional arguments for py2app
subparsers = parser.add_subparsers()
py2app_parser = subparsers.add_parser('py2app')
py2app_parser.add_argument('--make-app', dest='make_app',
                           help=argparse.SUPPRESS)

args, _ = parser.parse_known_args()
[sys.argv.remove(s) for s in ['--lite', '--dmg'] if s in sys.argv]

# setup logger
fmt = Formatter('%(asctime)s [%(levelname)s] [%(name)s] -> %(message)s')
h = StreamHandler()
h.setFormatter(fmt)
logger = getLogger('spyder-macOS')
logger.addHandler(h)
logger.setLevel('INFO')

# setup paths
here = os.path.abspath(__file__)
thisdir = os.path.dirname(here)
distdir = os.path.join(thisdir, 'dist')
spy_repo = os.path.realpath(os.path.join(thisdir, '..', '..'))

# symlink to spyder package
spy_link = os.path.join(thisdir, 'spyder')
if not os.path.islink(spy_link):
    os.symlink(os.path.join(spy_repo, 'spyder'), spy_link)

# =============================================================================
# App Creation
# =============================================================================
from spyder import __version__ as spy_version                    # noqa
from spyder.config.utils import EDIT_FILETYPES, _get_extensions  # noqa
from spyder.config.base import MAC_APP_NAME                      # noqa

iconfile = os.path.join(spy_repo, 'img_src', 'spyder.icns')

py_ver = [sys.version_info.major, sys.version_info.minor,
          sys.version_info.micro]

PACKAGES = ['alabaster', 'astroid', 'ipykernel', 'IPython', 'jedi', 'jinja2',
            'keyring', 'parso', 'pygments', 'pyls', 'qtawesome', 'spyder',
            'spyder_kernels', 'sphinx',
            ]

if args.make_lite:
    INCLUDES = []
    EXCLUDES = ['numpy', 'scipy', 'pandas', 'matplotlib', 'cython', 'sympy']
else:
    INCLUDES = ['numpy', 'scipy', 'pandas', 'matplotlib', 'cython', 'sympy']
    EXCLUDES = []

EDIT_EXT = [ext[1:] for ext in _get_extensions(EDIT_FILETYPES)]

OPTIONS = {
    'optimize': 0,
    'packages': PACKAGES,
    'includes': INCLUDES,
    'excludes': EXCLUDES,
    'iconfile': iconfile,
    'plist': {'CFBundleDocumentTypes': [{'CFBundleTypeExtensions': EDIT_EXT,
                                         'CFBundleTypeName': 'Text File',
                                         'CFBundleTypeRole': 'Editor'}],
              'CFBundleIdentifier': 'org.spyder-ide',
              'CFBundleShortVersionString': spy_version}
}

# copy main application script
app_script_name = MAC_APP_NAME.replace('.app', '.py')
app_script_path = os.path.join(spy_repo, 'scripts', app_script_name)
shutil.copy2(os.path.join(spy_repo, 'scripts', 'spyder'), app_script_path)

if 'make_app' in args:
    logger.info('Creating app bundle...')
    setup(app=[app_script_path], options={'py2app': OPTIONS})
else:
    logger.info('Skipping app bundle...')

# =============================================================================
# Post App Creation
# =============================================================================
if 'make_app' in args:
    _py_ver = f'python{py_ver[0]}.{py_ver[1]}'
    # copy egg info from site-packages: fixes pkg_resources issue for pyls
    for dist in pkg_resources.working_set:
        if dist.egg_info is None:
            continue
        dest = os.path.join(distdir, MAC_APP_NAME, 'Contents', 'Resources',
                            'lib', _py_ver, os.path.basename(dist.egg_info))
        shutil.copytree(dist.egg_info, dest)

# =============================================================================
# DMG Creation
# =============================================================================
appfile = os.path.join(distdir, MAC_APP_NAME)
volume_name = '{}-{} Py-{}.{}.{}'.format(MAC_APP_NAME[:-4],
                                         spy_version, *py_ver)
if args.make_lite:
    volume_name += ' (lite)'
dmgfile = os.path.join(distdir, volume_name + '.dmg')

settings_file = os.path.join(thisdir, 'dmg_settings.py')
settings = {
    'files': [appfile],
    'badge_icon': iconfile,
    'icon_locations': {MAC_APP_NAME: (140, 120), 'Applications': (500, 120)}
}

if args.make_dmg:
    logger.info('Building dmg file...')
    build_dmg(dmgfile, volume_name, settings_file=settings_file,
              settings=settings)
else:
    logger.info('Skipping dmg file...')

# =============================================================================
# Clean up
# =============================================================================
logger.info('Cleaning up...')
os.remove(app_script_path)
os.remove(spy_link)
