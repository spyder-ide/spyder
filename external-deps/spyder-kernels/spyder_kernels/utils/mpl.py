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


# Inline backend
if is_module_installed('matplotlib_inline'):
    inline_backend = 'module://matplotlib_inline.backend_inline'
else:
    inline_backend = 'module://ipykernel.pylab.backend_inline'


# Mapping of matlotlib backends options to Spyder
MPL_BACKENDS_TO_SPYDER = {
    inline_backend: 0,
    'Qt5Agg': 2,
    'QtAgg': 2,  # For Matplotlib 3.5+
    'TkAgg': 3,
    'MacOSX': 4,
}


def automatic_backend():
    """Get Matplolib automatic backend option."""
    if is_module_installed('PyQt5'):
        auto_backend = 'qt5'
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
    '3': 'tk',
    '4': 'osx'
}
