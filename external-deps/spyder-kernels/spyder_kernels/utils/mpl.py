# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""Matplotlib utilities."""

from spyder_kernels.utils.misc import is_module_installed


# Inline backend
if is_module_installed('matplotlib_inline'):
    inline_backend = 'module://matplotlib_inline.backend_inline'
else:
    inline_backend = 'module://ipykernel.pylab.backend_inline'


# Mapping of matlotlib backends options to Spyder
MPL_BACKENDS_TO_SPYDER = {
    'inline': 'inline',  # For Matplotlib >=3.9
    inline_backend: "inline",  # For Matplotlib <3.9
    'qt5agg': 'qt',
    'qtagg': 'qt',  # For Matplotlib 3.5+
    'tkagg': 'tk',
    'macosx': 'osx',
}


def automatic_backend():
    """Get Matplolib automatic backend option."""
    if is_module_installed('PyQt5'):
        auto_backend = 'qt'
    elif is_module_installed('_tkinter'):
        auto_backend = 'tk'
    else:
        auto_backend = 'inline'
    return auto_backend
