# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Lazy modules.

They are useful to not import big modules until it's really necessary.
"""

from spyder_kernels.utils.misc import is_module_installed


# =============================================================================
# Auxiliary classes
# =============================================================================
class FakeObject(object):
    """Fake class used in replacement of missing objects"""
    pass


class LazyModule(object):
    """Lazy module loader class."""

    def __init__(self, modname, second_level_attrs=None):
        """
        Lazy module loader class.

        Parameters
        ----------
        modname: str
            Module name to lazy load.
        second_level_attrs: list (optional)
            List of second level attributes to add to the FakeObject
            that stands for the module in case it's not found.
        """
        self.__spy_modname__ = modname
        self.__spy_mod__ = FakeObject

        # Set required second level attributes
        if second_level_attrs is not None:
            for attr in second_level_attrs:
                setattr(self.__spy_mod__, attr, FakeObject)

    def __getattr__(self, name):
        if is_module_installed(self.__spy_modname__):
            self.__spy_mod__ = __import__(self.__spy_modname__)
        else:
            return self.__spy_mod__

        return getattr(self.__spy_mod__, name)


# =============================================================================
# Lazy modules
# =============================================================================
numpy = LazyModule('numpy', ['MaskedArray'])

pandas = LazyModule('pandas')

PIL = LazyModule('PIL.Image', ['Image'])

bs4 = LazyModule('bs4', ['NavigableString'])

scipy = LazyModule('scipy.io')
