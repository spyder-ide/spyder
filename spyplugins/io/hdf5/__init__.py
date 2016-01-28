# =============================================================================
# The following statements are required to register this I/O plugin:
# =============================================================================
from .hdf5 import load_hdf5, save_hdf5

FORMAT_NAME = "HDF5"
FORMAT_EXT  = ".h5"
FORMAT_LOAD = load_hdf5
FORMAT_SAVE = save_hdf5
