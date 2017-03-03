# -*- coding:utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Input/Output Utilities

Note: 'load' functions has to return a dictionary from which a globals()
      namespace may be updated
"""

from __future__ import print_function

import sys
import os
import tarfile
import tempfile
import os.path as osp
import shutil
import warnings
import json
import inspect
import dis

# - If pandas fails to import here (for any reason), Spyder
#   will crash at startup (e.g. see Issue 2300)
# - This also prevents Spyder to start IPython kernels
#   (see Issue 2456)
try:
    import pandas as pd
except:
    pd = None            #analysis:ignore

# Local imports
from spyder.config.base import _, get_conf_path
from spyder.py3compat import pickle, to_text_string, getcwd, PY2


class MatlabStruct(dict):
    """
    Matlab style struct, enhanced.

    Supports dictionary and attribute style access.  Can be pickled,
    and supports code completion in a REPL.

    Examples
    ========
    >>> from spyder.utils.iofuncs import MatlabStruct
    >>> a = MatlabStruct()
    >>> a.b = 'spam'  # a["b"] == 'spam'
    >>> a.c["d"] = 'eggs'  # a.c.d == 'eggs'
    >>> print(a)
    {'c': {'d': 'eggs'}, 'b': 'spam'}

    """
    def __getattr__(self, attr):
        """Access the dictionary keys for unknown attributes."""
        try:
            return self[attr]
        except KeyError:
            msg = "'MatlabStruct' object has no attribute %s" % attr
            raise AttributeError(msg)

    def __getitem__(self, attr):
        """
        Get a dict value; create a MatlabStruct if requesting a submember.

        Do not create a key if the attribute starts with an underscore.
        """
        if attr in self.keys() or attr.startswith('_'):
            return dict.__getitem__(self, attr)
        frame = inspect.currentframe()
        # step into the function that called us
        if frame.f_back.f_back and self._is_allowed(frame.f_back.f_back):
            dict.__setitem__(self, attr, MatlabStruct())
        elif self._is_allowed(frame.f_back):
            dict.__setitem__(self, attr, MatlabStruct())
        return dict.__getitem__(self, attr)

    def _is_allowed(self, frame):
        """Check for allowed op code in the calling frame"""
        allowed = [dis.opmap['STORE_ATTR'], dis.opmap['LOAD_CONST'],
                   dis.opmap.get('STOP_CODE', 0)]
        bytecode = frame.f_code.co_code
        instruction = bytecode[frame.f_lasti + 3]
        instruction = ord(instruction) if PY2 else instruction
        return instruction in allowed

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    @property
    def __dict__(self):
        """Allow for code completion in a REPL"""
        return self.copy()


def get_matlab_value(val):
    """
    Extract a value from a Matlab file

    From the oct2py project, see
    http://pythonhosted.org/oct2py/conversions.html
    """
    import numpy as np

    # Extract each item of a list.
    if isinstance(val, list):
        return [get_matlab_value(v) for v in val]

    # Ignore leaf objects.
    if not isinstance(val, np.ndarray):
        return val

    # Convert user defined classes.
    if hasattr(val, 'classname'):
        out = dict()
        for name in val.dtype.names:
            out[name] = get_matlab_value(val[name].squeeze().tolist())
        cls = type(val.classname, (object,), out)
        return cls()

    # Extract struct data.
    elif val.dtype.names:
        out = MatlabStruct()
        for name in val.dtype.names:
            out[name] = get_matlab_value(val[name].squeeze().tolist())
        val = out

    # Extract cells.
    elif val.dtype.kind == 'O':
        val = val.squeeze().tolist()
        if not isinstance(val, list):
            val = [val]
        val = get_matlab_value(val)

    # Compress singleton values.
    elif val.size == 1:
        val = val.item()

    # Compress empty values.
    elif val.size == 0:
        if val.dtype.kind in 'US':
            val = ''
        else:
            val = []

    return val


try:
    import numpy as np
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import scipy.io as spio
    except AttributeError:
        # Python 2.5: warnings.catch_warnings was introduced in Python 2.6
        import scipy.io as spio  # analysis:ignore
    except:
        spio = None

    if spio is None:
        load_matlab = None
        save_matlab = None
    else:
        def load_matlab(filename):
            try:
                out = spio.loadmat(filename, struct_as_record=True)
                data = dict()
                for (key, value) in out.items():
                    data[key] = get_matlab_value(value)
                return data, None
            except Exception as error:
                return None, str(error)

        def save_matlab(data, filename):
            try:
                spio.savemat(filename, data, oned_as='row')
            except Exception as error:
                return str(error)
except:
    load_matlab = None
    save_matlab = None


try:
    import numpy as np  # analysis:ignore

    def load_array(filename):
        try:
            name = osp.splitext(osp.basename(filename))[0]
            data = np.load(filename)
            if hasattr(data, 'keys'):
                return data, None
            else:
                return {name: data}, None
        except Exception as error:
            return None, str(error)

    def __save_array(data, basename, index):
        """Save numpy array"""
        fname = basename + '_%04d.npy' % index
        np.save(fname, data)
        return fname
except:
    load_array = None


try:
    from spyder.pil_patch import Image

    if sys.byteorder == 'little':
        _ENDIAN = '<'
    else:
        _ENDIAN = '>'
    DTYPES = {
              "1": ('|b1', None),
              "L": ('|u1', None),
              "I": ('%si4' % _ENDIAN, None),
              "F": ('%sf4' % _ENDIAN, None),
              "I;16": ('|u2', None),
              "I;16S": ('%si2' % _ENDIAN, None),
              "P": ('|u1', None),
              "RGB": ('|u1', 3),
              "RGBX": ('|u1', 4),
              "RGBA": ('|u1', 4),
              "CMYK": ('|u1', 4),
              "YCbCr": ('|u1', 4),
              }
    def __image_to_array(filename):
        img = Image.open(filename)
        try:
            dtype, extra = DTYPES[img.mode]
        except KeyError:
            raise RuntimeError("%s mode is not supported" % img.mode)
        shape = (img.size[1], img.size[0])
        if extra is not None:
            shape += (extra,)
        return np.array(img.getdata(), dtype=np.dtype(dtype)).reshape(shape)

    def load_image(filename):
        try:
            name = osp.splitext(osp.basename(filename))[0]
            return {name: __image_to_array(filename)}, None
        except Exception as error:
            return None, str(error)
except:
    load_image = None


def load_pickle(filename):
    """Load a pickle file as a dictionary"""
    try:
        if pd:
            return pd.read_pickle(filename), None
        else:
            with open(filename, 'rb') as fid:
                data = pickle.load(fid)
            return data, None
    except Exception as err:
        return None, str(err)


def load_json(filename):
    """Load a json file as a dictionary"""
    try:
        if PY2:
            args = 'rb'
        else:
            args = 'r'
        with open(filename, args) as fid:
            data = json.load(fid)
        return data, None
    except Exception as err:
        return None, str(err)


def save_dictionary(data, filename):
    """Save dictionary in a single file .spydata file"""
    filename = osp.abspath(filename)
    old_cwd = getcwd()
    os.chdir(osp.dirname(filename))
    error_message = None
    try:
        saved_arrays = {}
        if load_array is not None:
            # Saving numpy arrays with np.save
            arr_fname = osp.splitext(filename)[0]
            for name in list(data.keys()):
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
                        iterator = iter(list(data[name].items()))
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
        with open(pickle_filename, 'wb') as fdesc:
            pickle.dump(data, fdesc, 2)
        tar = tarfile.open(filename, "w")
        for fname in [pickle_filename]+[fn for fn in list(saved_arrays.values())]:
            tar.add(osp.basename(fname))
            os.remove(fname)
        tar.close()
        if saved_arrays:
            data.pop('__saved_arrays__')
    except (RuntimeError, pickle.PicklingError, TypeError) as error:
        error_message = to_text_string(error)
    os.chdir(old_cwd)
    return error_message


def load_dictionary(filename):
    """Load dictionary from .spydata file"""
    filename = osp.abspath(filename)
    old_cwd = getcwd()
    tmp_folder = tempfile.mkdtemp()
    os.chdir(tmp_folder)
    data = None
    error_message = None
    try:
        tar = tarfile.open(filename, "r")
        tar.extractall()
        data_file = osp.basename(filename)
        pickle_filename = osp.splitext(data_file)[0]+'.pickle'
        try:
            # Old format (Spyder 2.0-2.1 for Python 2)
            with open(pickle_filename, 'U') as fdesc:
                data = pickle.loads(fdesc.read())
        except (pickle.PickleError, TypeError, UnicodeDecodeError):
            # New format (Spyder >=2.2 for Python 2 and Python 3)
            with open(pickle_filename, 'rb') as fdesc:
                data = pickle.loads(fdesc.read())
        saved_arrays = {}
        if load_array is not None:
            # Loading numpy arrays saved with np.save
            try:
                saved_arrays = data.pop('__saved_arrays__')
                for (name, index), fname in list(saved_arrays.items()):
                    arr = np.load( osp.join(tmp_folder, fname) )
                    if index is None:
                        data[name] = arr
                    elif isinstance(data[name], dict):
                        data[name][index] = arr
                    else:
                        data[name].insert(index, arr)
            except KeyError:
                pass
    except (EOFError, ValueError) as error:
        error_message = to_text_string(error)
    os.chdir(old_cwd)
    try:
        shutil.rmtree(tmp_folder)
    except OSError as error:
        error_message = to_text_string(error)
    return data, error_message


class IOFunctions(object):
    def __init__(self):
        self.load_extensions = None
        self.save_extensions = None
        self.load_filters = None
        self.save_filters = None
        self.load_funcs = None
        self.save_funcs = None

    def setup(self):
        iofuncs = self.get_internal_funcs()+self.get_3rd_party_funcs()
        load_extensions = {}
        save_extensions = {}
        load_funcs = {}
        save_funcs = {}
        load_filters = []
        save_filters = []
        load_ext = []
        for ext, name, loadfunc, savefunc in iofuncs:
            filter_str = to_text_string(name + " (*%s)" % ext)
            if loadfunc is not None:
                load_filters.append(filter_str)
                load_extensions[filter_str] = ext
                load_funcs[ext] = loadfunc
                load_ext.append(ext)
            if savefunc is not None:
                save_extensions[filter_str] = ext
                save_filters.append(filter_str)
                save_funcs[ext] = savefunc
        load_filters.insert(0, to_text_string(_("Supported files")+" (*"+\
                                              " *".join(load_ext)+")"))
        load_filters.append(to_text_string(_("All files (*.*)")))
        self.load_filters = "\n".join(load_filters)
        self.save_filters = "\n".join(save_filters)
        self.load_funcs = load_funcs
        self.save_funcs = save_funcs
        self.load_extensions = load_extensions
        self.save_extensions = save_extensions

    def get_internal_funcs(self):
        return [
                ('.spydata', _("Spyder data files"),
                             load_dictionary, save_dictionary),
                ('.npy', _("NumPy arrays"), load_array, None),
                ('.npz', _("NumPy zip arrays"), load_array, None),
                ('.mat', _("Matlab files"), load_matlab, save_matlab),
                ('.csv', _("CSV text files"), 'import_wizard', None),
                ('.txt', _("Text files"), 'import_wizard', None),
                ('.jpg', _("JPEG images"), load_image, None),
                ('.png', _("PNG images"), load_image, None),
                ('.gif', _("GIF images"), load_image, None),
                ('.tif', _("TIFF images"), load_image, None),
                ('.pkl', _("Pickle files"), load_pickle, None),
                ('.pickle', _("Pickle files"), load_pickle, None),
                ('.json', _("JSON files"), load_json, None),
                ]

    def get_3rd_party_funcs(self):
        other_funcs = []
        from spyder.otherplugins import get_spyderplugins_mods
        for mod in get_spyderplugins_mods(io=True):
            try:
                other_funcs.append((mod.FORMAT_EXT, mod.FORMAT_NAME,
                                    mod.FORMAT_LOAD, mod.FORMAT_SAVE))
            except AttributeError as error:
                print("%s: %s" % (mod, str(error)), file=STDERR)
        return other_funcs

    def save(self, data, filename):
        ext = osp.splitext(filename)[1].lower()
        if ext in self.save_funcs:
            return self.save_funcs[ext](data, filename)
        else:
            return _("<b>Unsupported file type '%s'</b>") % ext

    def load(self, filename):
        ext = osp.splitext(filename)[1].lower()
        if ext in self.load_funcs:
            return self.load_funcs[ext](filename)
        else:
            return None, _("<b>Unsupported file type '%s'</b>") % ext

iofunctions = IOFunctions()
iofunctions.setup()


def save_auto(data, filename):
    """Save data into filename, depending on file extension"""
    pass


if __name__ == "__main__":
    import io
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
    print(" Data saved in %.3f seconds" % (time.time()-t0))  # spyder: test-skip
    t0 = time.time()
    example2, ok = load_dictionary("test.spydata")
    print("Data loaded in %.3f seconds" % (time.time()-t0))  # spyder: test-skip
    os.remove("test.spydata")

    a = MatlabStruct()
    a.b = 'spam'
    assert a["b"] == 'spam'
    a.c["d"] = 'eggs'
    assert a.c.d == 'eggs'
    assert a == {'c': {'d': 'eggs'}, 'b': 'spam'}
    a['d'] = [1, 2, 3]

    if save_matlab:
        buf = io.BytesIO()
        save_matlab(a, buf)
        buf.seek(0)
        data, err = load_matlab(buf)
        assert data['b'] == 'spam'
        assert data['c'].d == 'eggs'
        assert data['d'].tolist() == [[1, 2, 3]]
