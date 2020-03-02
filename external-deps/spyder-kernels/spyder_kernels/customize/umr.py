# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)

"""User module reloader."""

import os
import sys

from spyder_kernels.customize.utils import path_is_library
from spyder_kernels.py3compat import PY2, _print


class UserModuleReloader(object):
    """
    User Module Reloader (UMR) aims at deleting user modules
    to force Python to deeply reload them during import

    pathlist [list]: blacklist in terms of module path
    namelist [list]: blacklist in terms of module name
    """

    def __init__(self, namelist=None, pathlist=None):
        if namelist is None:
            namelist = []
        else:
            try:
                namelist = namelist.split(',')
            except Exception:
                namelist = []

        # Spyder modules
        spy_modules = ['spyder_kernels']

        # Matplotlib modules
        mpl_modules = ['matplotlib', 'tkinter', 'Tkinter']

        # Add other, necessary modules to the UMR blacklist
        # astropy: See spyder-ide/spyder#6962
        # pytorch: See spyder-ide/spyder#7041
        # fastmat: See spyder-ide/spyder#7190
        # pythoncom: See spyder-ide/spyder#7190
        # tensorflow: See spyder-ide/spyder#8697
        other_modules = ['pytorch', 'pythoncom', 'tensorflow']
        if PY2:
            py2_modules = ['astropy', 'fastmat']
            other_modules = other_modules + py2_modules
        self.namelist = namelist + spy_modules + mpl_modules + other_modules

        self.pathlist = pathlist

        # List of previously loaded modules
        self.previous_modules = list(sys.modules.keys())

        # List of module names to reload
        self.modnames_to_reload = []

        # Activate Cython support
        self.has_cython = False
        self.activate_cython()

        # Check if the UMR is enabled or not
        enabled = os.environ.get("SPY_UMR_ENABLED", "")
        self.enabled = enabled.lower() == "true"

        # Check if the UMR should print the list of reloaded modules or not
        verbose = os.environ.get("SPY_UMR_VERBOSE", "")
        self.verbose = verbose.lower() == "true"

    def is_module_reloadable(self, module, modname):
        """Decide if a module is reloadable or not."""
        if self.has_cython:
            # Don't return cached inline compiled .PYX files
            return False
        else:
            if (path_is_library(getattr(module, '__file__', None),
                                self.pathlist) or
                    self.is_module_in_namelist(modname)):
                return False
            else:
                return True

    def is_module_in_namelist(self, modname):
        """Decide if a module can be reloaded or not according to its name."""
        return set(modname.split('.')) & set(self.namelist)

    def activate_cython(self):
        """
        Activate Cython support.

        We need to run this here because if the support is
        active, we don't to run the UMR at all.
        """
        run_cython = os.environ.get("SPY_RUN_CYTHON") == "True"

        if run_cython:
            try:
                __import__('Cython')
                self.has_cython = True
            except Exception:
                pass

            if self.has_cython:
                # Import pyximport to enable Cython files support for
                # import statement
                import pyximport
                pyx_setup_args = {}

                # Add Numpy include dir to pyximport/distutils
                try:
                    import numpy
                    pyx_setup_args['include_dirs'] = numpy.get_include()
                except Exception:
                    pass

                # Setup pyximport and enable Cython files reload
                pyximport.install(setup_args=pyx_setup_args,
                                  reload_support=True)

    def run(self):
        """
        Delete user modules to force Python to deeply reload them

        Do not del modules which are considered as system modules, i.e.
        modules installed in subdirectories of Python interpreter's binary
        Do not del C modules
        """
        self.modnames_to_reload = []
        for modname, module in list(sys.modules.items()):
            if modname not in self.previous_modules:
                # Decide if a module can be reloaded or not
                if self.is_module_reloadable(module, modname):
                    self.modnames_to_reload.append(modname)
                    del sys.modules[modname]
                else:
                    continue

        # Report reloaded modules
        if self.verbose and self.modnames_to_reload:
            modnames = self.modnames_to_reload
            _print("\x1b[4;33m%s\x1b[24m%s\x1b[0m"
                   % ("Reloaded modules", ": "+", ".join(modnames)))