# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder
======

Interactive Python shell and related widgets based on PyQt4
"""

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import os, os.path as osp

def get_package_data(name, extlist):
    """Return data files for package *name* with extensions in *extlist*"""
    flist = []
    # Workaround to replace os.path.relpath (not available until Python 2.6):
    offset = len(name)+len(os.pathsep)
    for dirpath, _dirnames, filenames in os.walk(name):
        for fname in filenames:
            if osp.splitext(fname)[1] in extlist:
                flist.append(osp.join(dirpath, fname)[offset:])
    return flist

name = 'spyder'
libname = 'spyderlib'
from spyderlib import __version__ as version
google_url = 'http://%s.googlecode.com' % libname
download_url = '%s/files/%s-%s.tar.gz' % (google_url, name, version)
packages = [libname+p for p in ['', '.widgets', '.widgets.externalshell',
                                '.widgets.qteditor', '.widgets.qscieditor',
                                '.plugins', '.utils']]+['spyderplugins']
extensions = ('.qm', '.api', '.svg', '.png',
              '.html', '.js', '', '.inv', '.txt', '.css', '.ico', '.doctree')
package_data={libname: get_package_data(libname, extensions)}
if os.name == 'nt':
    scripts = ['spyder.pyw', 'spyder.py']
else:
    scripts = ['spyder']
description = 'Spyder development environment and its PyQt4-based IDE tools: interactive Python shell, Python code editor, workspace (dict/list/string/array editor), doc viewer, history log, environment variables editor, ...'
long_description = 'spyderlib is intended to be an extension to PyQt4 providing a simple development environment named "Spyder" - a powerful alternative to IDLE (see screenshots: %s) based on independent widgets interacting with each other: workspace (globals explorer with dict/list editor and numpy arrays editor), docstring viewer (calltip), history log, multiline code editor (support drag and drop, autocompletion, syntax coloring, ...), environment variables editor (including a Windows-specific editor to change current user environement variables) and working directory browser.' % google_url
keywords = 'PyQt4 shell console widgets IDE'
classifiers = ['Development Status :: 5 - Production/Stable',
               'Topic :: Scientific/Engineering',
               'Topic :: Software Development :: Widget Sets',
               ]

setup(
      name = name,
      version = version,
      description = description,
      long_description = long_description,
      download_url = download_url,
      author = "Pierre Raybaut",
      author_email = 'contact@pythonxy.com',
      url = google_url,
      license = 'MIT',
      keywords = keywords,
      platforms = ['any'],
      packages = packages,
      package_data = package_data,
      requires=["pyflakes (>0.3.0)", "PyQt4 (>4.3)"],
      scripts = scripts,
      classifiers = classifiers + [
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: OS Independent',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        ],
    )
