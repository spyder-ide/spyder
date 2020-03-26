# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Create a stand-alone Mac OS X app using py2app

To be used like this:
$ python create_app.py py2app   (to build the app)
"""

import os
import sys
import shutil
from setuptools import setup

from spyder import __version__ as spy_version
from spyder.config.utils import EDIT_FILETYPES, _get_extensions
from spyder.config.base import MAC_APP_NAME

#==============================================================================
# App creation
#==============================================================================
APP_MAIN_SCRIPT = MAC_APP_NAME[:-4] + '.py'
shutil.copyfile('scripts/spyder', APP_MAIN_SCRIPT)

APP = [APP_MAIN_SCRIPT]
EXCLUDES = []
PACKAGES = ['spyder', 'sphinx', 'jinja2', 'docutils', 'alabaster', 'babel',
			'snowballstemmer', 'IPython', 'ipykernel', 'ipython_genutils',
			'jupyter_client', 'jupyter_core', 'traitlets', 'qtconsole',
			'pexpect', 'jedi', 'jsonschema', 'nbconvert', 'nbformat', 'qtpy',
			'qtawesome', 'zmq', 'pygments', 'distutils', 'PyQt5', 'psutil',
			'wrapt', 'lazy_object_proxy', 'spyder_kernels', 'pyls',
			'pylint', 'astroid', 'pycodestyle', 'pyflakes']

INCLUDES = []
EDIT_EXT = [ext[1:] for ext in _get_extensions(EDIT_FILETYPES)]

OPTIONS = {
    'optimize': 0,
    'packages': PACKAGES,
    'includes': INCLUDES,
    'excludes': EXCLUDES,
    'iconfile': 'img_src/spyder.icns',
    'plist': {'CFBundleDocumentTypes': [{'CFBundleTypeExtensions': EDIT_EXT,
                                         'CFBundleTypeName': 'Text File',
                                         'CFBundleTypeRole': 'Editor'}],
              'CFBundleIdentifier': 'org.spyder-ide',
              'CFBundleShortVersionString': spy_version}
}

setup(app=APP, options={'py2app': OPTIONS})

os.remove(APP_MAIN_SCRIPT)
