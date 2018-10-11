# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2010-2011 The IPython Development Team
# Copyright (c) 2011- Spyder Project Contributors
#
# Distributed under the terms of the Modified BSD License
# (BSD 3-clause; see NOTICE.txt in the Spyder root directory for details).
# -----------------------------------------------------------------------------

"""
Module completion auxiliary functions.
"""

import pkgutil

from pickleshare import PickleShareDB

from spyder.config.base import get_conf_path

# Path to the modules database
MODULES_PATH = get_conf_path('db')

# Modules database
modules_db = PickleShareDB(MODULES_PATH)


def get_submodules(mod):
    """Get all submodules of a given module"""
    def catch_exceptions(module):
        pass
    try:
        m = __import__(mod)
        submodules = [mod]
        submods = pkgutil.walk_packages(m.__path__, m.__name__ + '.',
                                        catch_exceptions)
        for sm in submods:
            sm_name = sm[1]
            submodules.append(sm_name)
    except ImportError:
        return []
    except:
        return [mod]
    
    return submodules


def get_preferred_submodules():
    """
    Get all submodules of the main scientific modules and others of our
    interest
    """
    if 'submodules' in modules_db:
        return modules_db['submodules']
    
    mods = ['numpy', 'scipy', 'sympy', 'pandas', 'networkx', 'statsmodels',
            'matplotlib', 'sklearn', 'skimage', 'mpmath', 'os', 'PIL',
            'OpenGL', 'array', 'audioop', 'binascii', 'cPickle', 'cStringIO',
            'cmath', 'collections', 'datetime', 'errno', 'exceptions', 'gc',
            'imageop', 'imp', 'itertools', 'marshal', 'math', 'mmap', 'msvcrt',
            'nt', 'operator', 'parser', 'rgbimg', 'signal', 'strop', 'sys',
            'thread', 'time', 'wx', 'xxsubtype', 'zipimport', 'zlib', 'nose',
            'PyQt4', 'PySide', 'os.path']

    submodules = []

    for m in mods:
        submods = get_submodules(m)
        submodules += submods
    
    modules_db['submodules'] = submodules
    return submodules
