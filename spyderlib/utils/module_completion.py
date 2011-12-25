# -*- coding: utf-8 -*-
"""Module completion auxiliary functions"""

#*****************************************************************************
#
#  The functions on this file were taken from the file ipy_completers,
#  which belongs to the IPython project. They were added here because a)
#  IPython is not a runtime dependency of Spyder, and b) we want to perfom
#  module completion not only on an ipython shell, but also on a regular
#  python interpreter and a source code editor.
#  Besides, we needed to modify moduleCompletion to make it work as a regular
#  python function, and not as a mix of python and readline completion, which
#  is how we think it works on IPython.
#
#  Distributed under the terms of the BSD License.
#
#*****************************************************************************

import inspect
import os.path
from time import time
import sys
from zipimport import zipimporter

from spyderlib.baseconfig import get_conf_path
from spyderlib.utils.external.pickleshare import PickleShareDB

MODULES_PATH = get_conf_path('db')
TIMEOUT_GIVEUP = 20 #Time in seconds after which we give up

db = PickleShareDB(MODULES_PATH)

def getRootModules():
    """
    Returns a list containing the names of all the modules available in the
    folders of the pythonpath.
    """
    modules = []
    if db.has_key('rootmodules'):
        return db['rootmodules']
    t = time()
    for path in sys.path:
        modules += moduleList(path)        
        if time() - t > TIMEOUT_GIVEUP:
            print "Module list generation is taking too long, we give up."
            print
            db['rootmodules'] = []
            return []
    
    modules += sys.builtin_module_names
      
    modules = list(set(modules))
    if '__init__' in modules:
        modules.remove('__init__')
    modules = list(set(modules))
    db['rootmodules'] = modules
    return modules

def moduleList(path):
    """
    Return the list containing the names of the modules available in the given
    folder.
    """

    if os.path.isdir(path):
        folder_list = os.listdir(path)
    elif path.endswith('.egg'):
        try:
            folder_list = [f for f in zipimporter(path)._files]
        except:
            folder_list = []
    else:
        folder_list = []
    #folder_list = glob.glob(os.path.join(path,'*'))
    folder_list = [p for p in folder_list  \
       if os.path.exists(os.path.join(path, p,'__init__.py'))\
           or p[-3:] in ('.py','.so')\
           or p[-4:] in ('.pyc','.pyo','.pyd')]

    folder_list = [os.path.basename(p).split('.')[0] for p in folder_list]
    return folder_list

def moduleCompletion(line):
    """
    Returns a list containing the completion possibilities for an import line.
    The line looks like this :
    'import xml.d'
    'from xml.dom import'
    """
    def tryImport(mod, only_modules=False):
        def isImportable(module, attr):
            if only_modules:
                return inspect.ismodule(getattr(module, attr))
            else:
                return not(attr[:2] == '__' and attr[-2:] == '__')
        try:
            m = __import__(mod)
        except:
            return []
        completion_list = []
        mods = mod.split('.')
        for module in mods[1:]:
            try:
                m = getattr(m,module)
            except:
                return []
        if (not hasattr(m, '__file__')) or (not only_modules) or\
           (hasattr(m, '__file__') and '__init__' in m.__file__):
            completion_list = [attr for attr in dir(m) if isImportable(m, attr)]
        completion_list.extend(getattr(m,'__all__',[]))
        if hasattr(m, '__file__') and '__init__' in m.__file__:
            completion_list.extend(moduleList(os.path.dirname(m.__file__)))
        completion_list = list(set(completion_list))
        if '__init__' in completion_list:
            completion_list.remove('__init__')
        return completion_list
        
    def dotCompletion(mod):
        if len(mod) < 2:
            return filter(lambda x: x.startswith(mod[0]), getRootModules())
        
        completion_list = tryImport('.'.join(mod[:-1]), True)
        completion_list = filter(lambda x: x.startswith(mod[-1]),
                                 completion_list)
        completion_list = ['.'.join(mod[:-1] + [el]) for el in completion_list]
        return completion_list

    words = line.split(' ')
    
    if len(words) == 3 and words[0] == 'from':
        if words[2].startswith('i') or words[2] == '':
            return ['import ']
        else:
            return []
            
    if words[0] == 'import':
        if len(words) == 2 and words[1] == '':
            return getRootModules()

        if ',' == words[-1][-1]:
            return [' ']
        
        mod = words[-1].split('.')
        return dotCompletion(mod)
        
    if len(words) < 3 and (words[0] == 'from'):
        if len(words) == 1:
            return getRootModules()
        
        mod = words[1].split('.')
        return dotCompletion(mod)
    
    if len(words) >= 3 and words[0] == 'from':
        mod = words[1]
        completion_list = tryImport(mod)
        if words[2] == 'import' and words[3] != '':
            if '(' in words[-1]:
                words = words[:-2] + words[-1].split('(')
            if ',' in words[-1]:
                words = words[:-2] + words[-1].split(',')
            return filter(lambda x: x.startswith(words[-1]), completion_list)
        else:
            return completion_list
    
    return []
        

if __name__ == "__main__":
    # Some simple tests.
    # Sort operations are done by the completion widget, so we have to
    # replicate them here.
    # We've chosen to use xml on all tests because it's on the standard
    # library. This way we can ensure they work on all plataforms.
    
    assert sorted(moduleCompletion('import xml.')) == \
        ['xml.dom', 'xml.etree', 'xml.parsers', 'xml.sax']

    assert sorted(moduleCompletion('import xml.d')) ==  ['xml.dom']

    assert moduleCompletion('from xml.etree ') == ['import ']

    assert sorted(moduleCompletion('from xml.etree import '),key=str.lower) ==\
        ['cElementTree', 'ElementInclude', 'ElementPath', 'ElementTree']
        
    s = 'from xml.etree.ElementTree import '
    assert moduleCompletion(s + 'V') == ['VERSION']

    assert sorted(moduleCompletion(s + 'VERSION,XM')) == \
        ['XML', 'XMLID', 'XMLParser', 'XMLTreeBuilder']

    assert moduleCompletion(s + '(dum') == ['dump']

    assert moduleCompletion(s + '(dump,Su') == ['SubElement']
