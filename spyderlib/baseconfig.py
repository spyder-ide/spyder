# -*- coding: utf-8 -*-
#
# Copyright © 2011-2013 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder base configuration management

As opposed to spyderlib/config.py, this configuration script deals 
exclusively with non-GUI features configuration only
(in other words, we won't import any PyQt object here, avoiding any 
sip API incompatibility issue in spyderlib's non-gui modules)
"""

from __future__ import print_function

import os.path as osp
import os
import sys

# Local imports
from spyderlib import __version__
from spyderlib.utils import encoding
from spyderlib.py3compat import (is_unicode, TEXT_TYPES, INT_TYPES, PY3,
                                 to_text_string, is_text_string)


#==============================================================================
# Only for development
#==============================================================================
# To activate/deactivate certain things for development
# SPYDER_DEV is (and *only* has to be) set in bootstrap.py
DEV = os.environ.get('SPYDER_DEV')

# For testing purposes
# SPYDER_TEST can be set using the --test option of bootstrap.py
TEST = os.environ.get('SPYDER_TEST')


#==============================================================================
# Debug helpers
#==============================================================================
STDOUT = sys.stdout
STDERR = sys.stderr
def _get_debug_env():
    debug_env = os.environ.get('SPYDER_DEBUG', '')
    if not debug_env.isdigit():
        debug_env = bool(debug_env)
    return int(debug_env)    
DEBUG = _get_debug_env()

def debug_print(message):
    """Output debug messages to stdout"""
    if DEBUG:
        ss = STDOUT
        print(message, file=ss)

#==============================================================================
# Configuration paths
#==============================================================================
# Spyder settings dir
if TEST is None:
    SUBFOLDER = '.spyder%s' % __version__.split('.')[0]
else:
    SUBFOLDER = 'spyder_test'


# We can't have PY2 and PY3 settings in the same dir because:
# 1. This leads to ugly crashes and freezes (e.g. by trying to
#    embed a PY2 interpreter in PY3)
# 2. We need to save the list of installed modules (for code
#    completion) separately for each version
if PY3:
    SUBFOLDER = SUBFOLDER + '-py3'


def get_home_dir():
    """
    Return user home directory
    """
    try:
        # expanduser() returns a raw byte string which needs to be
        # decoded with the codec that the OS is using to represent file paths.
        path = encoding.to_unicode_from_fs(osp.expanduser('~'))
    except:
        path = ''
    for env_var in ('HOME', 'USERPROFILE', 'TMP'):
        if osp.isdir(path):
            break
        # os.environ.get() returns a raw byte string which needs to be
        # decoded with the codec that the OS is using to represent environment
        # variables.
        path = encoding.to_unicode_from_fs(os.environ.get(env_var, ''))
    if path:
        return path
    else:
        raise RuntimeError('Please define environment variable $HOME')


def get_conf_path(filename=None):
    """Return absolute path for configuration file with specified filename"""
    if TEST is None:
        conf_dir = osp.join(get_home_dir(), SUBFOLDER)
    else:
         import tempfile
         conf_dir = osp.join(tempfile.gettempdir(), SUBFOLDER)
    if not osp.isdir(conf_dir):
        os.mkdir(conf_dir)
    if filename is None:
        return conf_dir
    else:
        return osp.join(conf_dir, filename)
        

def get_module_path(modname):
    """Return module *modname* base path"""
    return osp.abspath(osp.dirname(sys.modules[modname].__file__))


def get_module_data_path(modname, relpath=None, attr_name='DATAPATH'):
    """Return module *modname* data path
    Note: relpath is ignored if module has an attribute named *attr_name*
    
    Handles py2exe/cx_Freeze distributions"""
    datapath = getattr(sys.modules[modname], attr_name, '')
    if datapath:
        return datapath
    else:
        datapath = get_module_path(modname)
        parentdir = osp.join(datapath, osp.pardir)
        if osp.isfile(parentdir):
            # Parent directory is not a directory but the 'library.zip' file:
            # this is either a py2exe or a cx_Freeze distribution
            datapath = osp.abspath(osp.join(osp.join(parentdir, osp.pardir),
                                            modname))
        if relpath is not None:
            datapath = osp.abspath(osp.join(datapath, relpath))
        return datapath


def get_module_source_path(modname, basename=None):
    """Return module *modname* source path
    If *basename* is specified, return *modname.basename* path where 
    *modname* is a package containing the module *basename*
    
    *basename* is a filename (not a module name), so it must include the
    file extension: .py or .pyw
    
    Handles py2exe/cx_Freeze distributions"""
    srcpath = get_module_path(modname)
    parentdir = osp.join(srcpath, osp.pardir)
    if osp.isfile(parentdir):
        # Parent directory is not a directory but the 'library.zip' file:
        # this is either a py2exe or a cx_Freeze distribution
        srcpath = osp.abspath(osp.join(osp.join(parentdir, osp.pardir),
                                       modname))
    if basename is not None:
        srcpath = osp.abspath(osp.join(srcpath, basename))
    return srcpath


def is_py2exe_or_cx_Freeze():
    """Return True if this is a py2exe/cx_Freeze distribution of Spyder"""
    return osp.isfile(osp.join(get_module_path('spyderlib'), osp.pardir))


SCIENTIFIC_STARTUP = get_module_source_path('spyderlib',
                                            'scientific_startup.py')


#==============================================================================
# Image path list
#==============================================================================

IMG_PATH = []
def add_image_path(path):
    if not osp.isdir(path):
        return
    global IMG_PATH
    IMG_PATH.append(path)
    for _root, dirs, _files in os.walk(path):
        for dir in dirs:
            IMG_PATH.append(osp.join(path, dir))

add_image_path(get_module_data_path('spyderlib', relpath='images'))

from spyderlib.otherplugins import PLUGIN_PATH
if PLUGIN_PATH is not None:
    add_image_path(osp.join(PLUGIN_PATH, 'images'))

def get_image_path(name, default="not_found.png"):
    """Return image absolute path"""
    for img_path in IMG_PATH:
        full_path = osp.join(img_path, name)
        if osp.isfile(full_path):
            return osp.abspath(full_path)
    if default is not None:
        return osp.abspath(osp.join(img_path, default))


#==============================================================================
# Translations
#==============================================================================
def get_translation(modname, dirname=None):
    """Return translation callback for module *modname*"""
    if dirname is None:
        dirname = modname
    locale_path = get_module_data_path(dirname, relpath="locale",
                                       attr_name='LOCALEPATH')
    # fixup environment var LANG in case it's unknown
    if "LANG" not in os.environ:
        import locale
        lang = locale.getdefaultlocale()[0]
        if lang is not None:
            os.environ["LANG"] = lang
    import gettext
    try:
        _trans = gettext.translation(modname, locale_path, codeset="utf-8")
        lgettext = _trans.lgettext
        def translate_gettext(x):
            if not PY3 and is_unicode(x):
                x = x.encode("utf-8")
            y = lgettext(x)
            if is_text_string(y) and PY3:
                return y
            else:
                return to_text_string(y, "utf-8")
        return translate_gettext
    except IOError as _e:  # analysis:ignore
        #print "Not using translations (%s)" % _e
        def translate_dumb(x):
            if not is_unicode(x):
                return to_text_string(x, "utf-8")
            return x
        return translate_dumb

# Translation callback
_ = get_translation("spyderlib")


#==============================================================================
# Namespace Browser (Variable Explorer) configuration management
#==============================================================================

def get_supported_types():
    """
    Return a dictionnary containing types lists supported by the 
    namespace browser:
    dict(picklable=picklable_types, editable=editables_types)
         
    See:
    get_remote_data function in spyderlib/widgets/externalshell/monitor.py
    get_internal_shell_filter method in namespacebrowser.py
    
    Note:
    If you update this list, don't forget to update doc/variablexplorer.rst
    """
    from datetime import date
    editable_types = [int, float, complex, list, dict, tuple, date
                      ] + list(TEXT_TYPES) + list(INT_TYPES)
    try:
        from numpy import ndarray, matrix, generic
        editable_types += [ndarray, matrix, generic]
    except ImportError:
        pass
    try:
        from pandas import DataFrame, TimeSeries
        editable_types += [DataFrame, TimeSeries]
    except ImportError:
        pass
    picklable_types = editable_types[:]
    try:
        from spyderlib.pil_patch import Image
        editable_types.append(Image.Image)
    except ImportError:
        pass
    return dict(picklable=picklable_types, editable=editable_types)

# Variable explorer display / check all elements data types for sequences:
# (when saving the variable explorer contents, check_all is True,
#  see widgets/externalshell/namespacebrowser.py:NamespaceBrowser.save_data)
CHECK_ALL = False #XXX: If True, this should take too much to compute...

EXCLUDED_NAMES = ['nan', 'inf', 'infty', 'little_endian', 'colorbar_doc',
                  'typecodes', '__builtins__', '__main__', '__doc__', 'NaN',
                  'Inf', 'Infinity', 'sctypes', 'rcParams', 'rcParamsDefault',
                  'sctypeNA', 'typeNA', 'False_', 'True_',]

#==============================================================================
# Mac application utilities
#==============================================================================

if PY3:
    MAC_APP_NAME = 'Spyder.app'
else:
    MAC_APP_NAME = 'Spyder-Py2.app'

def running_in_mac_app():
    if sys.platform == "darwin" and MAC_APP_NAME in __file__:
        return True
    else:
        return False
