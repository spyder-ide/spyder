#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Buiding instructions:
# python setup.py py2exe

from distutils.core import setup
import py2exe # Patching distutils setup
from guidata.disthelpers import (remove_build_dist, get_default_excludes,
                         get_default_dll_excludes, create_vs2008_data_files,
                         add_text_data_file, add_module_data_files, add_modules,
                         strip_version)

# Removing old build/dist folders
remove_build_dist()

# Including/excluding DLLs and Python modules
EXCLUDES = get_default_excludes()
INCLUDES = []
DLL_EXCLUDES = get_default_dll_excludes()
DATA_FILES = create_vs2008_data_files()

from spyderlib import __version__

# Distributing application-specific data files
add_module_data_files("spyderlib", ("images", ),
                      ('.png', '.svg',), DATA_FILES, copy_to_root=False)
add_module_data_files("spyderlib", ("doc", ),
                      ('.html', '.png', '.txt', '.js', '.inv', '.ico', '.css',
                       '.doctree'), DATA_FILES, copy_to_root=False)
add_module_data_files("spyderlib", ("", ),
                      ('.qm', '.py'), DATA_FILES, copy_to_root=False)
add_module_data_files("spyderplugins", ("", ),
                      ('.py',), DATA_FILES, copy_to_root=False)

# Configuring/including Python modules
add_modules(('PyQt4', 'matplotlib'),
            DATA_FILES, INCLUDES, EXCLUDES)

EXCLUDES += ['spyderplugins']
INCLUDES += ['spyderlib.widgets.externalshell.startup',
             'spyderlib.widgets.externalshell.sitecustomize',
             'IPython']

setup(
      options={
               "py2exe": {"skip_archive": True,
                          "includes": INCLUDES, "excludes": EXCLUDES,
                          "dll_excludes": DLL_EXCLUDES,
                          "dist_dir": "dist",},
               },
      data_files=DATA_FILES,
      windows=[{
                "script": "spyderlib/spyder.py",
                "icon_resources": [(0, "spyder.ico")],
                "bitmap_resources": [],
                "other_resources": [],
                "dest_base": "spyder",
                "version": strip_version(__version__),
                "company_name": "Pierre Raybaut",
                "copyright": u"Copyright © 2009-2010 Pierre Raybaut",
                "name": u"Spyder",
                "description": u"Scientific PYthon Development EnviRonment",
                },],
      )
