# -*- coding: utf-8 -*-
"""Module completion auxiliary functions"""

#*****************************************************************************
#
#  The functions on this file were taken from the file core/completerlib,
#  which belongs to the IPython project (v0.13). They were added here because
#  a) IPython is not a runtime dependency of Spyder, and b) we want to perfom
#  module completion not only on our Python console, but also on our source
#  code editor.
#  Several of these functions were modified to make it work according to our
#  needs
#
#  Distributed under the terms of the BSD License.
#
#*****************************************************************************

import imp
import inspect
import os.path
import re
from time import time
import sys
from zipimport import zipimporter

from spyderlib.baseconfig import get_conf_path
from spyderlib.utils.external.pickleshare import PickleShareDB

MODULES_PATH = get_conf_path('db')
TIMEOUT_GIVEUP = 20 # Time in seconds after which we give up

# Regular expression for the python import statement
import_re = re.compile(r'(?P<name>[a-zA-Z_][a-zA-Z0-9_]*?)'
                       r'(?P<package>[/\\]__init__)?'
                       r'(?P<suffix>%s)$' %
                       r'|'.join(re.escape(s[0]) for s in imp.get_suffixes()))

modules_db = PickleShareDB(MODULES_PATH)


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


def get_root_modules():
    """
    Returns list of names of all modules from PYTHONPATH folders.
    """
    modules = []
    if modules_db.has_key('rootmodules'):
        return modules_db['rootmodules']

    t = time()
    modules = list(sys.builtin_module_names)
    for path in sys.path:
        modules += module_list(path)        
        if time() - t > TIMEOUT_GIVEUP:
            print "Module list generation is taking too long, we give up.\n"
            modules_db['rootmodules'] = []
            return []
    
    modules = set(modules)
    if '__init__' in modules:
        modules.remove('__init__')
    modules = list(modules)
    modules_db['rootmodules'] = modules
    return modules


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


def dot_completion(mod):
    if len(mod) < 2:
        return filter(lambda x: x.startswith(mod[0]), get_root_modules())
    completion_list = try_import('.'.join(mod[:-1]), True)
    completion_list = filter(lambda x: x.startswith(mod[-1]), completion_list)
    completion_list = ['.'.join(mod[:-1] + [el]) for el in completion_list]
    return completion_list


def module_completion(line):
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
            return get_root_modules()
        if ',' == words[-1][-1]:
            return [' ']       
        mod = words[-1].split('.')
        return dot_completion(mod)

    # 'from xy<tab>'
    if nwords < 3 and (words[0] == 'from'):
        if nwords == 1:
            return get_root_modules()
        mod = words[1].split('.')
        return dot_completion(mod)

    # 'from xyz import abc<tab>'
    if nwords >= 3 and words[0] == 'from':
        mod = words[1]
        completion_list = try_import(mod)
        if words[2] == 'import' and words[3] != '':
            if '(' in words[-1]:
                words = words[:-2] + words[-1].split('(')
            if ',' in words[-1]:
                words = words[:-2] + words[-1].split(',')
            return filter(lambda x: x.startswith(words[-1]), completion_list)
        else:
            return completion_list
    
    return []
        

def reset():
    """Clear root modules database"""
    if modules_db.has_key('rootmodules'):
        del modules_db['rootmodules']


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
    
    s = 'from xml.etree.ElementTree import '
    assert module_completion(s + 'V') == ['VERSION']

    assert sorted(module_completion(s + 'VERSION, XM')) == \
        ['XML', 'XMLID', 'XMLParser', 'XMLTreeBuilder']

    assert module_completion(s + '(dum') == ['dump']

    assert module_completion(s + '(dump, Su') == ['SubElement']
