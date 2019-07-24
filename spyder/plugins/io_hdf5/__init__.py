# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


# =============================================================================
# The following statements are required to register this I/O plugin:
# =============================================================================

from .plugin import load_hdf5, save_hdf5


FORMAT_NAME = "HDF5"
FORMAT_EXT  = ".h5"
FORMAT_LOAD = load_hdf5
FORMAT_SAVE = save_hdf5

PLUGIN_CLASS = True
