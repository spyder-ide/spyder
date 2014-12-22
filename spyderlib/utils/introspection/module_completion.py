# -*- coding: utf-8 -*-
"""Module completion auxiliary functions"""

#------------------------------------------------------------------------------
#
#  Most functions on this file were taken from the file core/completerlib,
#  which belongs to the IPython project (v0.13). They were added here because
#  a) IPython is not an Spyder runtime dependency, and b) we want to perfom
#  module completion not only on our Python console, but also on our source
#  code editor.
#
#  Several of these functions were modified to make it work according to our
#  needs
#
#  Distributed under the terms of the BSD License.
#  Copyright (C) 2010-2011 The IPython Development Team.
#  Copyright (C) 2013 The Spyder Development Team
#
#------------------------------------------------------------------------------

import imp
import inspect
import os.path
import pkgutil
import re
from time import time
import sys
from zipimport import zipimporter

from spyderlib.baseconfig import get_conf_path, running_in_mac_app
from spyderlib.utils.external.pickleshare import PickleShareDB

#-----------------------------------------------------------------------------
# Globals and constants
#-----------------------------------------------------------------------------

# Path to the modules database
MODULES_PATH = get_conf_path('db')

# Time in seconds after which we give up
TIMEOUT_GIVEUP = 20

# Py2app only uses .pyc files for the stdlib when optimize=0,
# so we need to add it as another suffix here
if running_in_mac_app():
    suffixes = imp.get_suffixes() + [('.pyc', 'rb', '2')]
else:
    suffixes = imp.get_suffixes()

# Regular expression for the python import statement
import_re = re.compile(r'(?P<name>[a-zA-Z_][a-zA-Z0-9_]*?)'
                       r'(?P<package>[/\\]__init__)?'
                       r'(?P<suffix>%s)$' %
                       r'|'.join(re.escape(s[0]) for s in suffixes))

# Modules database
modules_db = PickleShareDB(MODULES_PATH)

#-----------------------------------------------------------------------------
# Utility functions
#-----------------------------------------------------------------------------

def module_list(path):
    """
    Return the list containing the names of the modules available in the given
    folder.
    """
    # sys.path has the cwd as an empty string, but isdir/listdir need it as '.'
    if path == '':
        path = '.'

    # A few local constants to be used in loops below
    pjoin = os.path.join

    if os.path.isdir(path):
        # Build a list of all files in the directory and all files
        # in its subdirectories. For performance reasons, do not
        # recurse more than one level into subdirectories.
        files = []
        for root, dirs, nondirs in os.walk(path):
            subdir = root[len(path)+1:]
            if subdir:
                files.extend(pjoin(subdir, f) for f in nondirs)
                dirs[:] = [] # Do not recurse into additional subdirectories.
            else:
                files.extend(nondirs)
    else:
        try:
            files = list(zipimporter(path)._files.keys())
        except:
            files = []

    # Build a list of modules which match the import_re regex.
    modules = []
    for f in files:
        m = import_re.match(f)
        if m:
            modules.append(m.group('name'))
    return list(set(modules))


def get_root_modules(paths):
    """
    Returns list of names of all modules from PYTHONPATH folders.
    
    paths : list
        A list of additional paths that Spyder adds to PYTHONPATH. They are
        comming from our PYTHONPATH manager and from the currently selected
        project.
    """
    modules = []
    spy_modules = []
    
    for path in paths:
        spy_modules += module_list(path)
    spy_modules = set(spy_modules)
    if '__init__' in spy_modules:
        spy_modules.remove('__init__')
    spy_modules = list(spy_modules)
    
    if 'rootmodules' in modules_db:
        return spy_modules + modules_db['rootmodules']

    t = time()
    modules = list(sys.builtin_module_names)
    # TODO: Change this sys.path for console's interpreter sys.path
    for path in sys.path:
        modules += module_list(path)        
        if time() - t > TIMEOUT_GIVEUP:
            print("Module list generation is taking too long, we give up.\n")
            modules_db['rootmodules'] = []
            return []
    
    modules = set(modules)
    excluded_modules = ['__init__'] + spy_modules
    for mod in excluded_modules:
        if mod in modules:
            modules.remove(mod)
    modules = list(modules)

    modules_db['rootmodules'] = modules
    return spy_modules + modules


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


def is_importable(module, attr, only_modules):
    if only_modules:
        return inspect.ismodule(getattr(module, attr))
    else:
        return not(attr[:2] == '__' and attr[-2:] == '__')


def try_import(mod, only_modules=False):
    try:
        m = __import__(mod)
    except:
        return []
    mods = mod.split('.')
    for module in mods[1:]:
        m = getattr(m, module)

    m_is_init = hasattr(m, '__file__') and '__init__' in m.__file__

    completions = []
    if (not hasattr(m, '__file__')) or (not only_modules) or m_is_init:
        completions.extend([attr for attr in dir(m) if
                            is_importable(m, attr, only_modules)])

    completions.extend(getattr(m, '__all__', []))
    if m_is_init:
        completions.extend(module_list(os.path.dirname(m.__file__)))
    completions = set(completions)
    if '__init__' in completions:
        completions.remove('__init__')
    return list(completions)


def dot_completion(mod, paths):
    if len(mod) < 2:
        return [x for x in get_root_modules(paths) if x.startswith(mod[0])]
    completion_list = try_import('.'.join(mod[:-1]), True)
    completion_list = [x for x in completion_list if x.startswith(mod[-1])]
    completion_list = ['.'.join(mod[:-1] + [el]) for el in completion_list]
    return completion_list

#-----------------------------------------------------------------------------
# Main functions
#-----------------------------------------------------------------------------

def module_completion(line, paths=[]):
    """
    Returns a list containing the completion possibilities for an import line.
    
    The line looks like this :
    'import xml.d'
    'from xml.dom import'
    """

    words = line.split(' ')
    nwords = len(words)
    
    # from whatever <tab> -> 'import '
    if nwords == 3 and words[0] == 'from':
        if words[2].startswith('i') or words[2] == '':
            return ['import ']
        else:
            return []

    # 'import xy<tab> or import xy<tab>, '
    if words[0] == 'import':
        if nwords == 2 and words[1] == '':
            return get_root_modules(paths)
        if ',' == words[-1][-1]:
            return [' ']       
        mod = words[-1].split('.')
        return dot_completion(mod, paths)

    # 'from xy<tab>'
    if nwords < 3 and (words[0] == 'from'):
        if nwords == 1:
            return get_root_modules(paths)
        mod = words[1].split('.')
        return dot_completion(mod, paths)

    # 'from xyz import abc<tab>'
    if nwords >= 3 and words[0] == 'from':
        mod = words[1]
        completion_list = try_import(mod)
        if words[2] == 'import' and words[3] != '':
            if '(' in words[-1]:
                words = words[:-2] + words[-1].split('(')
            if ',' in words[-1]:
                words = words[:-2] + words[-1].split(',')
            return [x for x in completion_list if x.startswith(words[-1])]
        else:
            return completion_list
    
    return []
        

def reset():
    """Clear root modules database"""
    if 'rootmodules' in modules_db:
        del modules_db['rootmodules']


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

#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------

if __name__ == "__main__":
    # Some simple tests.
    # Sort operations are done by the completion widget, so we have to
    # replicate them here.
    # We've chosen to use xml on most tests because it's on the standard
    # library. This way we can ensure they work on all plataforms.
    
    assert sorted(module_completion('import xml.')) == \
        ['xml.dom', 'xml.etree', 'xml.parsers', 'xml.sax']

    assert sorted(module_completion('import xml.d')) ==  ['xml.dom']

    assert module_completion('from xml.etree ') == ['import ']

    assert sorted(module_completion('from xml.etree import '), key=str.lower) ==\
        ['cElementTree', 'ElementInclude', 'ElementPath', 'ElementTree']

    assert module_completion('import sys, zl') == ['zlib']

    s = 'from xml.etree.ElementTree import '
    assert module_completion(s + 'V') == ['VERSION']

    assert sorted(module_completion(s + 'VERSION, XM')) == \
        ['XML', 'XMLID', 'XMLParser', 'XMLTreeBuilder']

    assert module_completion(s + '(dum') == ['dump']

    assert module_completion(s + '(dump, Su') == ['SubElement']
