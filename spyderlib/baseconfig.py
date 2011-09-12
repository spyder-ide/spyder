# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder base configuration management

As opposed to spyderlib/config.py, this configuration script deals 
exclusively with non-GUI features configuration only
(in other words, we won't import any PyQt object here, avoiding any 
sip API incompatibility issue in spyderlib's non-gui modules)
"""

import os.path as osp, os, sys

# Local imports
from spyderlib.userconfig import get_home_dir
from spyderlib import __version__


SUBFOLDER = '.spyder%s' % __version__.split('.')[0]


#==============================================================================
# Configuration paths
#==============================================================================
def get_conf_path(filename=None):
    """Return absolute path for configuration file with specified filename"""
    conf_dir = osp.join(get_home_dir(), SUBFOLDER)
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


SCIENTIFIC_STARTUP = osp.join(get_module_path('spyderlib'),
                              'scientific_startup.py')


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
            if isinstance(x, unicode):
                x = x.encode("utf-8")
            return unicode(lgettext(x), "utf-8")
        return translate_gettext
    except IOError, _e:
        #print "Not using translations (%s)" % _e
        def translate_dumb(x):
            if not isinstance(x, unicode):
                return unicode(x, "utf-8")
            return x
        return translate_dumb

# Translation callback
_ = get_translation("spyderlib")


#==============================================================================
# Namespace Browser (Variable Explorer) configuration management
#==============================================================================

def get_supported_types():
    """Return a dictionnary containing types lists supported by the 
    namespace browser:
    dict(picklable=picklable_types,
         editableeditables_types)
         
    See:
    get_remote_data function in spyderlib/widgets/externalshell/monitor.py
    get_internal_shell_filter method in namespacebrowser.py"""
    from datetime import date
    editable_types = [int, long, float, list, dict, tuple, str, unicode, date]
    try:
        from numpy import ndarray, matrix
        editable_types += [ndarray, matrix]
    except ImportError:
        pass
    picklable_types = editable_types[:]
    try:
        from PIL.Image import Image
        editable_types.append(Image)
    except ImportError:
        pass
    return dict(picklable=picklable_types, editable=editable_types)

# Max number of filter iterations for worskpace display:
# (for workspace saving, itermax == -1, see Workspace.save)
ITERMAX = -1 #XXX: To be adjusted if it takes too much to compute... 2, 3?

EXCLUDED = ['nan', 'inf', 'infty', 'little_endian', 'colorbar_doc',
            'typecodes', '__builtins__', '__main__', '__doc__', 'NaN',
            'Inf', 'Infinity']
