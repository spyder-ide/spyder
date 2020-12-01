# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""Miscellaneous utilities"""

import re


# Mapping of inline figure formats
INLINE_FIGURE_FORMATS = {
    '0': 'png',
    '1': 'svg'
}

# Mapping of matlotlib backends options to Spyder
MPL_BACKENDS_TO_SPYDER = {
    'module://ipykernel.pylab.backend_inline': 0,
    'Qt5Agg': 2,
    'Qt4Agg': 3,
    'MacOSX': 4,
    'GTK3Agg': 5,
    'GTKAgg': 6,
    'WX': 7,
    'TkAgg': 8
}


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


def automatic_backend():
    """Get Matplolib automatic backend option."""
    if is_module_installed('PyQt5'):
        auto_backend = 'qt5'
    elif is_module_installed('PyQt4'):
        auto_backend = 'qt4'
    elif is_module_installed('_tkinter'):
        auto_backend = 'tk'
    else:
        auto_backend = 'inline'
    return auto_backend


# Mapping of Spyder options to backends
MPL_BACKENDS_FROM_SPYDER = {
    '0': 'inline',
    '1': automatic_backend(),
    '2': 'qt5',
    '3': 'qt4',
    '4': 'osx',
    '5': 'gtk3',
    '6': 'gtk',
    '7': 'wx',
    '8': 'tk'
}


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
