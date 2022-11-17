# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Variable Explorer Plugin plotting library management.
"""

# Standard library imports
import importlib

# Local imports
from spyder.config.base import _


# Defining compatible plotting libraries
# (default library is the first available, see `get_default_plotlib`)
LIBRARIES = ("matplotlib", "guiqwt")


def is_package_installed(modname):
    """Check if package is installed **without importing it**
    
    Note: As Spyder won't start if matplotlib has been imported too early,
    we do not use `utils.programs.is_module_installed` here because
    it imports module to check if it's installed.
    """
    return importlib.util.find_spec(modname) is not None


def get_available_plotlibs():
    """Return list of available plotting libraries"""
    return [name for name in LIBRARIES if is_package_installed(name)]


def get_default_plotlib():
    """Return default plotting library"""
    names = get_available_plotlibs()
    if names is not None:
        return names[0]


def get_requirement_error_message():
    """Return html error message when no library is available"""
    txt = ", ".join(["<b>%s</b>" % name for name in LIBRARIES])
    return _("Please install a compatible plotting library (%s).") % txt


AVAILABLE_PLOTLIBS = get_available_plotlibs()
DEFAULT_PLOTLIB = get_default_plotlib()
REQ_ERROR_MSG = get_requirement_error_message()
