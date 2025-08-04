# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""Miscellaneous utilities"""

import re

from functools import lru_cache


@lru_cache(maxsize=100)
def is_module_installed(module_name):
    """
    Simpler version of spyder.utils.programs.is_module_installed.
    """
    try:
        mod = __import__(module_name)
        # This is necessary to not report that the module is installed
        # when only its __pycache__ directory is present.
        if getattr(mod, '__file__', None):
            return True
        else:
            return False
    except Exception:
        # Module is not installed
        return False


def get_package_version(package_name):
    from importlib.metadata import PackageNotFoundError, version as package_version
    from packaging.version import parse as parse_version
    try:
        return parse_version(package_version(package_name))
    except PackageNotFoundError:
        return None


def fix_reference_name(name, blacklist=None):
    """Return a syntax-valid Python reference name from an arbitrary name"""
    name = "".join(re.split(r'[^0-9a-zA-Z_]', name))
    while name and not re.match(r'([a-zA-Z]+[0-9a-zA-Z_]*)$', name):
        if not re.match(r'[a-zA-Z]', name[0]):
            name = name[1:]
            continue
    name = str(name)
    if not name:
        name = "data"
    if blacklist is not None and name in blacklist:
        get_new_name = lambda index: name+('_%03d' % index)
        index = 0
        while get_new_name(index) in blacklist:
            index += 1
        name = get_new_name(index)
    return name
