# -*- coding:utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Input/Output Utilities

Note: 'load' functions has to return a dictionary from which a globals()
      namespace may be updated
"""

import os, cPickle, tarfile, os.path as osp


try:
    import scipy.io as spio
    def load_matlab(filename):
        try:
            return spio.loadmat(filename, struct_as_record=True), None
        except Exception, error:
            return str(error)
    def save_matlab(data, filename):
        try:
            spio.savemat(filename, data, oned_as='row')
        except Exception, error:
            return str(error)
except ImportError:
    load_matlab = None
    save_matlab = None


try:
    import numpy as np
    def load_array(filename):
        try:
            name = osp.splitext(osp.basename(filename))[0]
            return {name: np.load(filename)}, None
        except Exception, error:
            return str(error)    
    def __save_array(data, basename, index):
        """Save numpy array"""
        fname = basename + '_%04d.npy' % index
        np.save(fname, data)
        return fname
except ImportError:
    load_array = None


def save_dictionary(data, filename):
    """Save dictionary in a single file .spydata file"""
    filename = osp.abspath(filename)
    old_cwd = os.getcwdu()
    os.chdir(osp.dirname(filename))
    error_message = None
    try:
        saved_arrays = {}
        if load_array is not None:
            # Saving numpy arrays with np.save
            arr_fname = osp.splitext(filename)[0]
            for name in data.keys():
                if isinstance(data[name], np.ndarray) and data[name].size > 0:
                    # Saving arrays at data root
                    fname = __save_array(data[name], arr_fname,
                                       len(saved_arrays))
                    saved_arrays[(name, None)] = osp.basename(fname)
                    data.pop(name)
                elif isinstance(data[name], (list, dict)):
                    # Saving arrays nested in lists or dictionaries
                    if isinstance(data[name], list):
                        iterator = enumerate(data[name])
                    else:
                        iterator = data[name].iteritems()
                    to_remove = []
                    for index, value in iterator:
                        if isinstance(value, np.ndarray) and value.size > 0:
                            fname = __save_array(value, arr_fname,
                                               len(saved_arrays))
                            saved_arrays[(name, index)] = osp.basename(fname)
                            to_remove.append(index)
                    for index in sorted(to_remove, reverse=True):
                        data[name].pop(index)
            if saved_arrays:
                data['__saved_arrays__'] = saved_arrays
        pickle_filename = osp.splitext(filename)[0]+'.pickle'
        cPickle.dump(data, file(pickle_filename, 'w'))
        tar = tarfile.open(filename, "w")
        for fname in [pickle_filename]+[fn for fn in saved_arrays.itervalues()]:
            tar.add(osp.basename(fname))
            os.remove(fname)
        tar.close()
        if saved_arrays:
            data.pop('__saved_arrays__')
    except (RuntimeError, cPickle.PicklingError, TypeError), error:
        error_message = str(error)
    os.chdir(old_cwd)
    return error_message

def load_dictionary(filename):
    """Load dictionary from .spydata file"""
    filename = osp.abspath(filename)
    old_cwd = os.getcwdu()
    os.chdir(osp.dirname(filename))
    error_message = None
    try:
        tar = tarfile.open(filename, "r")
        tar.extractall()
        pickle_filename = osp.splitext(filename)[0]+'.pickle'
        data = cPickle.load(file(pickle_filename))
        saved_arrays = {}
        if load_array is not None:
            # Loading numpy arrays saved with np.save
            try:
                saved_arrays = data.pop('__saved_arrays__')
                for (name, index), fname in saved_arrays.iteritems():
                    arr = np.load( osp.join(osp.dirname(filename), fname) )
                    if index is None:
                        data[name] = arr
                    elif isinstance(data[name], dict):
                        data[name][index] = arr
                    else:
                        data[name].insert(index, arr)
            except KeyError:
                pass
        for fname in [pickle_filename]+[fn for fn in saved_arrays.itervalues()]:
            os.remove(fname)
    except (EOFError, ValueError), error:
        error_message = str(error)
    os.chdir(old_cwd)
    return data, error_message


if __name__ == "__main__":
    import datetime
    testdict = {'d': 1, 'a': np.random.rand(10, 10), 'b': [1, 2]}
    testdate = datetime.date(1945, 5, 8)
    example = {'str': 'kjkj kj k j j kj k jkj',
               'unicode': u'éù',
               'list': [1, 3, [4, 5, 6], 'kjkj', None],
               'tuple': ([1, testdate, testdict], 'kjkj', None),
               'dict': testdict,
               'float': 1.2233,
               'array': np.random.rand(4000, 400),
               'empty_array': np.array([]),
               'date': testdate,
               'datetime': datetime.datetime(1945, 5, 8),
               }
    import time
    t0 = time.time()
    save_dictionary(example, "test.spydata")
    print " Data saved in %.3f seconds" % (time.time()-t0)
    t0 = time.time()
    example2, ok = load_dictionary("test.spydata")
    print "Data loaded in %.3f seconds" % (time.time()-t0)
#    for key in example:
#        print key, ":", example[key] == example2[key]
