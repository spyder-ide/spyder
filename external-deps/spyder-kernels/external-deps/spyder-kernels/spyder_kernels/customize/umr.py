# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)

"""User module reloader."""

import os
import sys

from spyder_kernels.customize.utils import path_is_library


class UserModuleReloader:
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
        self.namelist = namelist + spy_modules + mpl_modules + other_modules

        self.pathlist = pathlist

        # List of previously loaded modules
        self.previous_modules = list(sys.modules.keys())

        # Check if the UMR is enabled or not
        enabled = os.environ.get("SPY_UMR_ENABLED", "")
        self.enabled = enabled.lower() == "true"

        # Check if the UMR should print the list of reloaded modules or not
        verbose = os.environ.get("SPY_UMR_VERBOSE", "")
        self.verbose = verbose.lower() == "true"

    def is_module_reloadable(self, module, modname):
        """Decide if a module is reloadable or not."""
        if (
            path_is_library(getattr(module, '__file__', None), self.pathlist)
            or self.is_module_in_namelist(modname)
        ):
            return False
        else:
            return True

    def is_module_in_namelist(self, modname):
        """Decide if a module can be reloaded or not according to its name."""
        return set(modname.split('.')) & set(self.namelist)

    def run(self):
        """
        Delete user modules to force Python to deeply reload them

        Do not del modules which are considered as system modules, i.e.
        modules installed in subdirectories of Python interpreter's binary
        Do not del C modules
        """
        modnames_to_reload = []
        for modname, module in list(sys.modules.items()):
            if modname not in self.previous_modules:
                # Decide if a module can be reloaded or not
                if self.is_module_reloadable(module, modname):
                    modnames_to_reload.append(modname)
                    del sys.modules[modname]
                else:
                    continue

        # Report reloaded modules
        if self.verbose and modnames_to_reload:
            modnames = modnames_to_reload
            print("\x1b[4;33m%s\x1b[24m%s\x1b[0m"
                  % ("Reloaded modules", ": "+", ".join(modnames)))

        return modnames_to_reload
