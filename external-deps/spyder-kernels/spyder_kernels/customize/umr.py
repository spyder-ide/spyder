# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)

"""User module reloader."""

import sys
from typing import Optional, TYPE_CHECKING

from spyder_kernels.customize.utils import path_is_library


if TYPE_CHECKING:
    from spyder_kernels.console.shell import SpyderShell


class UserModuleReloader:
    """
    User Module Reloader (UMR) aims at deleting user modules
    to force Python to deeply reload them during import

    pathlist [list]: blacklist in terms of module path
    namelist [list]: blacklist in terms of module name
    """

    def __init__(
        self,
        pathlist: list[str] | None = None,
        shell: Optional["SpyderShell"] = None,
    ):
        self.pathlist = pathlist
        self._shell = shell

        # Add necessary modules to the UMR blacklist
        # Spyder modules
        self._spy_modules = ['spyder_kernels']

        # Matplotlib modules
        self._mpl_modules = ['matplotlib', 'tkinter', 'Tkinter']

        # Other modules
        # pytorch: See spyder-ide/spyder#7041
        # pythoncom: See spyder-ide/spyder#7190
        # tensorflow: See spyder-ide/spyder#8697
        self._other_modules = ['pytorch', 'pythoncom', 'tensorflow']

        # List of previously loaded modules
        self.previous_modules = list(sys.modules.keys())

    @property
    def enabled(self) -> bool:
        """Check if the UMR is enabled."""
        return self._shell.umr_enabled if self._shell else True

    @property
    def verbose(self) -> bool:
        """Check if the UMR should print the list of reloaded modules."""
        return self._shell.umr_verbose if self._shell else True

    @property
    def namelist(self) -> list[str]:
        """List of blacklisted modules."""
        users_namelist = self._shell.umr_namelist if self._shell else []

        return (
            users_namelist
            + self._spy_modules
            + self._mpl_modules
            + self._other_modules
        )

    def is_module_reloadable(self, module, modname):
        """Decide if a module is reloadable."""
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
            colors = {"dark": "33", "light": "31"}
            color = colors["dark"]
            if self._shell:
                color = colors[self._shell.get_spyder_theme()]
            content = ": "+", ".join(modnames)
            print(f"\x1b[4;{color}mReloaded modules\x1b[24m{content}\x1b[0m")

        return modnames_to_reload
