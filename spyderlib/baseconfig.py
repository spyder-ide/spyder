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

import os.path as osp, os

# Local imports
from spyderlib.userconfig import get_home_dir
from spyderlib import __version__
from spyderlib.utils.translations import get_translation


# Translation support
_ = get_translation("spyderlib")


SUBFOLDER = '.spyder%s' % __version__.split('.')[0]


def get_conf_path(filename=None):
    """Return absolute path for configuration file with specified filename"""
    conf_dir = osp.join(get_home_dir(), SUBFOLDER)
    if not osp.isdir(conf_dir):
        os.mkdir(conf_dir)
    if filename is None:
        return conf_dir
    else:
        return osp.join(conf_dir, filename)


#===============================================================================
# Namespace Browser (Variable Explorer) configuration management
#===============================================================================
from datetime import date
EDITABLE_TYPES = [int, long, float, list, dict, tuple, str, unicode, date]
try:
    from numpy import ndarray, matrix
    EDITABLE_TYPES += [ndarray, matrix]
except ImportError:
    pass
PICKLABLE_TYPES = EDITABLE_TYPES[:]
try:
    from PIL.Image import Image
    EDITABLE_TYPES.append(Image)
except ImportError:
    pass

# Max number of filter iterations for worskpace display:
# (for workspace saving, itermax == -1, see Workspace.save)
ITERMAX = -1 #XXX: To be adjusted if it takes too much to compute... 2, 3?

EXCLUDED = ['nan', 'inf', 'infty', 'little_endian', 'colorbar_doc',
            'typecodes', '__builtins__', '__main__', '__doc__', 'NaN',
            'Inf', 'Infinity']

def type2str(types):
    """Convert types to strings"""
    return [typ.__name__ for typ in types]

def str2type(strings):
    """Convert strings to types"""
    return tuple( [eval(string) for string in strings] )
