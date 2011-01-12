#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Buiding instructions:
# python setup.py py2exe

from distutils.core import setup
import py2exe # Patching distutils setup
from guidata.disthelpers import (remove_build_dist, get_default_excludes,
                         get_default_dll_excludes, create_vs2008_data_files,
                         add_module_data_files, add_modules)

# Removing old build/dist folders
remove_build_dist()

# Including/excluding DLLs and Python modules
EXCLUDES = get_default_excludes()
INCLUDES = []
DLL_EXCLUDES = get_default_dll_excludes()
DATA_FILES = create_vs2008_data_files()

# Distributing application-specific data files
add_module_data_files("spyderlib", ("images", ),
                      ('.png', '.svg',), DATA_FILES, copy_to_root=False)
add_module_data_files("spyderlib", ("", ),
                      ('.qm', '.py'), DATA_FILES, copy_to_root=False)

# Configuring/including Python modules
add_modules(('PyQt4', ), # add 'matplotlib' after 'PyQt4' if you need it
            DATA_FILES, INCLUDES, EXCLUDES)

setup(
      options={
               "py2exe": {"compressed": 2, "optimize": 2, 'bundle_files': 1,
                          "includes": INCLUDES, "excludes": EXCLUDES,
                          "dll_excludes": DLL_EXCLUDES,
                          "dist_dir": "dist",},
               },
      data_files=DATA_FILES,
      windows=[{
                "script": "example.pyw",
                "dest_base": "example",
                "version": "1.0",
                "company_name": "Pierre Raybaut",
                "copyright": u"Copyright © 2009-2010 Pierre Raybaut",
                "name": u"AppWithSpyder",
                "description": u"Application using Spyder console",
                },],
      zipfile = None,
      )
