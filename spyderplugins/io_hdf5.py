# -*- coding:utf-8 -*-
#
# Copyright © 2011 David Anthony Powell
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""I/O plugin for loading/saving HDF5 files

Note that this is a fairly dumb implementation which reads the whole HDF5 file into
Spyder's variable explorer.  Since HDF5 files are designed for storing very large
data-sets, it may be much better to work directly with the HDF5 objects, thus keeping
the data on disk.  Nonetheless, this plugin gives quick and dirty but convenient 
access to HDF5 files.

There is no support for creating files with compression, chunking etc, although
these can be read without problem.

All datatypes to be saved must be convertible to a numpy array, otherwise an exception
will be raised.

Data attributes are currently ignored.

When reading an HDF5 file with sub-groups, groups in the HDF5 file will
correspond to dictionaries with the same layout.  However, when saving
data, dictionaries are not turned into HDF5 groups.

TODO: Look for the pytables library if h5py is not found??
TODO: Check issues with valid python names vs valid h5f5 names
"""

from __future__ import print_function

try:
    # Do not import h5py here because it will try to import IPython,
    # and this is freezing the Spyder GUI
    import imp
    imp.find_module('h5py')
    import numpy as np
    
    def load_hdf5(filename):
        import h5py
        def get_group(group):
            contents = {}
            for name, obj in list(group.items()):
                if isinstance(obj, h5py.Dataset):
                    contents[name] = np.array(obj)
                elif isinstance(obj, h5py.Group):
                    # it is a group, so call self recursively
                    contents[name] = get_group(obj)
                # other objects such as links are ignored
            return contents
            
        try:
            f = h5py.File(filename, 'r')
            contents = get_group(f)
            f.close()
            return contents, None
        except Exception as error:
            return None, str(error)
            
    def save_hdf5(data, filename):
        import h5py
        try:
            f = h5py.File(filename, 'w')
            for key, value in list(data.items()):
                f[key] = np.array(value)
            f.close()
        except Exception as error:
            return str(error)            
except ImportError:
    load_hdf5 = None
    save_hdf5 = None

#===============================================================================
# The following statements are required to register this I/O plugin:
#===============================================================================
FORMAT_NAME = "HDF5"
FORMAT_EXT  = ".h5"
FORMAT_LOAD = load_hdf5
FORMAT_SAVE = save_hdf5

if __name__ == "__main__":
    data = {'a' : [1, 2, 3, 4], 'b' : 4.5}
    print(save_hdf5(data, "test.h5"))
    print(load_hdf5("test.h5"))
