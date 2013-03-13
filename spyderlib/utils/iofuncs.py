# -*- coding:utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Input/Output Utilities

Note: 'load' functions has to return a dictionary from which a globals()
      namespace may be updated
"""

from __future__ import with_statement

import sys
import os
import cPickle
import tarfile
import os.path as osp
import shutil
import warnings


try:
    import numpy as np
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import scipy.io as spio
    except AttributeError:
        # Python 2.5: warnings.catch_warnings was introduced in Python 2.6
        import scipy.io as spio  # analysis:ignore
    def load_matlab(filename):
        try:
            out = spio.loadmat(filename, struct_as_record=True,
                               squeeze_me=True)
            for key, value in out.iteritems():
                if isinstance(value, np.ndarray):
                    if value.shape == ():
                        out[key] = value.tolist()
                    # The following would be needed if squeeze_me=False:
#                    elif value.shape == (1,):
#                        out[key] = value[0]
#                    elif value.shape == (1, 1):
#                        out[key] = value[0][0]
            return out, None
        except Exception, error:
            return None, str(error)
    def save_matlab(data, filename):
        try:
            spio.savemat(filename, data, oned_as='row')
        except Exception, error:
            return str(error)
except ImportError:
    load_matlab = None
    save_matlab = None


try:
    import numpy as np  # analysis:ignore
    def load_array(filename):
        try:
            name = osp.splitext(osp.basename(filename))[0]
            return {name: np.load(filename)}, None
        except Exception, error:
            return None, str(error)    
    def __save_array(data, basename, index):
        """Save numpy array"""
        fname = basename + '_%04d.npy' % index
        np.save(fname, data)
        return fname
except ImportError:
    load_array = None


try:
    from spyderlib.pil_patch import Image
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
        except Exception, error:
            return None, str(error)
except ImportError:
    load_image = None


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
        with open(pickle_filename, 'wb') as fdesc:
            cPickle.dump(data, fdesc, 2)
        tar = tarfile.open(filename, "w")
        for fname in [pickle_filename]+[fn for fn in saved_arrays.itervalues()]:
            tar.add(osp.basename(fname))
            os.remove(fname)
        tar.close()
        if saved_arrays:
            data.pop('__saved_arrays__')
    except (RuntimeError, cPickle.PicklingError, TypeError), error:
        error_message = unicode(error)
    os.chdir(old_cwd)
    return error_message

def load_dictionary(filename):
    """Load dictionary from .spydata file"""
    filename = osp.abspath(filename)
    old_cwd = os.getcwdu()
    os.chdir(osp.dirname(filename))
    data = None
    error_message = None
    try:
        tar = tarfile.open(filename, "r")
        tar.extractall()
        pickle_filename = osp.splitext(filename)[0]+'.pickle'
        try:
            # Old format (Spyder 2.0-2.1 for Python 2)
            with open(pickle_filename, 'U') as fdesc:
                data = cPickle.loads(fdesc.read())
        except cPickle.PickleError:
            # New format (Spyder >=2.2 for Python 2 and Python 3)
            with open(pickle_filename, 'rb') as fdesc:
                data = cPickle.loads(fdesc.read())
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
        error_message = unicode(error)
    os.chdir(old_cwd)
    return data, error_message


from spyderlib.baseconfig import get_conf_path, STDERR

SAVED_CONFIG_FILES = ('.inspector', '.onlinehelp', '.path', '.pylint.results',
                      '.spyder.ini', '.temp.py', '.temp.spydata', 'template.py',
                      '.projects', '.history.py', '.history_internal.py',
                      '.spyderproject', '.ropeproject', '.workingdir',
                      'monitor.log', 'monitor_debug.log', 'rope.log')

def reset_session():
    """Remove all config files"""
    print >>STDERR, "*** Reset Spyder settings to defaults ***"
    for fname in SAVED_CONFIG_FILES:
        cfg_fname = get_conf_path(fname)
        if osp.isfile(cfg_fname):
            os.remove(cfg_fname)
        elif osp.isdir(cfg_fname):
            shutil.rmtree(cfg_fname)
        else:
            continue
        print >>STDERR, "removing:", cfg_fname

def save_session(filename):
    """Save Spyder session"""
    local_fname = get_conf_path(osp.basename(filename))
    filename = osp.abspath(filename)
    old_cwd = os.getcwdu()
    os.chdir(get_conf_path())
    error_message = None
    try:
        tar = tarfile.open(local_fname, "w")
        for fname in SAVED_CONFIG_FILES:
            if osp.isfile(fname):
                tar.add(fname)
        tar.close()
        shutil.move(local_fname, filename)
    except Exception, error:
        error_message = unicode(error)
    os.chdir(old_cwd)
    return error_message

def load_session(filename):
    """Load Spyder session"""
    filename = osp.abspath(filename)
    old_cwd = os.getcwdu()
    os.chdir(osp.dirname(filename))
    error_message = None
    renamed = False
    try:
        tar = tarfile.open(filename, "r")
        extracted_files = tar.getnames()
        
        # Rename original config files
        for fname in extracted_files:
            orig_name = get_conf_path(fname)
            bak_name = get_conf_path(fname+'.bak')
            if osp.isfile(bak_name):
                os.remove(bak_name)
            if osp.isfile(orig_name):
                os.rename(orig_name, bak_name)
        renamed = True
        
        tar.extractall()
        
        for fname in extracted_files:
            shutil.move(fname, get_conf_path(fname))
            
    except Exception, error:
        error_message = unicode(error)
        if renamed:
            # Restore original config files
            for fname in extracted_files:
                orig_name = get_conf_path(fname)
                bak_name = get_conf_path(fname+'.bak')
                if osp.isfile(orig_name):
                    os.remove(orig_name)
                if osp.isfile(bak_name):
                    os.rename(bak_name, orig_name)
                    
    finally:
        # Removing backup config files
        for fname in extracted_files:
            bak_name = get_conf_path(fname+'.bak')
            if osp.isfile(bak_name):
                os.remove(bak_name)
        
    os.chdir(old_cwd)
    return error_message


from spyderlib.baseconfig import _

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
            filter_str = unicode(name + " (*%s)" % ext)
            if loadfunc is not None:
                load_filters.append(filter_str)
                load_extensions[filter_str] = ext
                load_funcs[ext] = loadfunc
                load_ext.append(ext)
            if savefunc is not None:
                save_extensions[filter_str] = ext
                save_filters.append(filter_str)
                save_funcs[ext] = savefunc
        load_filters.insert(0, unicode(_("Supported files")+" (*"+\
                                       " *".join(load_ext)+")"))
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
                ('.mat', _("Matlab files"), load_matlab, save_matlab),
                ('.csv', _("CSV text files"), 'import_wizard', None),
                ('.txt', _("Text files"), 'import_wizard', None),
                ('.jpg', _("JPEG images"), load_image, None),
                ('.png', _("PNG images"), load_image, None),
                ('.gif', _("GIF images"), load_image, None),
                ('.tif', _("TIFF images"), load_image, None),
                ]
        
    def get_3rd_party_funcs(self):
        other_funcs = []
        from spyderlib.otherplugins import get_spyderplugins_mods
        for mod in get_spyderplugins_mods(prefix='io_', extension='.py'):
            try:
                other_funcs.append((mod.FORMAT_EXT, mod.FORMAT_NAME,
                                    mod.FORMAT_LOAD, mod.FORMAT_SAVE))
            except AttributeError, error:
                print >>STDERR, "%s: %s" % (mod, str(error))
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
