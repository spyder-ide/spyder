# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""Matplotlib utilities."""

from spyder_kernels.utils.misc import is_module_installed


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
