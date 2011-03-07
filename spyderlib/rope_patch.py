# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Patching rope for better performances
See this thread:
http://groups.google.com/group/rope-dev/browse_thread/thread/57de5731f202537a
"""

def apply():
    """Monkey patching rope for better performances"""
    import rope
    if rope.VERSION not in ('0.9.3', '0.9.2'):
        raise ImportError, "rope %s can't be patched" % rope.VERSION
    
    # Patching pycore.PyCore, so that forced builtin modules (i.e. modules 
    # that were declared as 'extension_modules' in rope preferences)
    # will be indeed recognized as builtins by rope, as expected
    from rope.base import pycore
    class PatchedPyCore(pycore.PyCore):
        def get_module(self, name, folder=None):
            """Returns a `PyObject` if the module was found."""
            # check if this is a builtin module
            pymod = self._builtin_module(name)
            if pymod is not None:
                return pymod
            module = self.find_module(name, folder)
            if module is None:
                raise pycore.ModuleNotFoundError(
                                            'Module %s not found' % name)
            return self.resource_to_pyobject(module)
    pycore.PyCore = PatchedPyCore
    
    # Patching BuiltinFunction for the calltip/doc functions to be 
    # able to retrieve the function signatures with forced builtins
    from rope.base import builtins, pyobjects
    from spyderlib.utils.dochelpers import getargs
    class PatchedBuiltinFunction(builtins.BuiltinFunction):
        def __init__(self, returned=None, function=None, builtin=None,
                     argnames=[], parent=None):
            builtins._BuiltinElement.__init__(self, builtin, parent)
            pyobjects.AbstractFunction.__init__(self)
            self.argnames = argnames
            if not argnames and builtin:
                self.argnames = getargs(self.builtin)
            if self.argnames is None:
                self.argnames = []
            self.returned = returned
            self.function = function
    builtins.BuiltinFunction = PatchedBuiltinFunction

    # Patching BuiltinName for the go to definition feature to simply work 
    # with forced builtins
    from rope.base import libutils
    import inspect
    class PatchedBuiltinName(builtins.BuiltinName):
        def _pycore(self):
            p = self.pyobject
            while p.parent is not None:
                p = p.parent
            if isinstance(p, builtins.BuiltinModule) and p.pycore is not None:
                return p.pycore
        def get_definition_location(self):
            if not inspect.isbuiltin(self.pyobject):
                _lines, lineno = inspect.getsourcelines(self.pyobject.builtin)
                path = inspect.getfile(self.pyobject.builtin)
                pycore = self._pycore()
                if pycore and pycore.project:
                    resource = libutils.path_to_resource(pycore.project, path)
                    module = pyobjects.PyModule(pycore, None, resource)
                    return (module, lineno)
            return (None, None)
    builtins.BuiltinName = PatchedBuiltinName
