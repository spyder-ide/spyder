# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Patching rope:

[1] For better performances, see this thread:
http://groups.google.com/group/rope-dev/browse_thread/thread/57de5731f202537a

[2] To avoid considering folders without __init__.py as Python packages, thus
avoiding side effects as non-working introspection features on a Python module
or package when a folder in current directory has the same name.
See this thread:
http://groups.google.com/group/rope-dev/browse_thread/thread/924c4b5a6268e618
"""

def apply():
    """Monkey patching rope
    
    See [1] and [2] in module docstring."""
    import rope
    if rope.VERSION not in ('0.9.3', '0.9.2'):
        raise ImportError, "rope %s can't be patched" % rope.VERSION
    
    # Patching pycore.PyCore...
    from rope.base import pycore
    class PatchedPyCore(pycore.PyCore):
        # [1] ...so that forced builtin modules (i.e. modules that were 
        # declared as 'extension_modules' in rope preferences) will be indeed
        # recognized as builtins by rope, as expected
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
        # [2] ...to avoid considering folders without __init__.py as Python
        # packages
        def _find_module_in_folder(self, folder, modname):
            module = folder
            packages = modname.split('.')
            for pkg in packages[:-1]:
                if  module.is_folder() and module.has_child(pkg):
                    module = module.get_child(pkg)
                else:
                    return None
            if module.is_folder():
                if module.has_child(packages[-1]) and \
                   module.get_child(packages[-1]).is_folder() and \
                   module.get_child(packages[-1]).has_child('__init__.py'):
                    return module.get_child(packages[-1])
                elif module.has_child(packages[-1] + '.py') and \
                     not module.get_child(packages[-1] + '.py').is_folder():
                    return module.get_child(packages[-1] + '.py')
    pycore.PyCore = PatchedPyCore
    
    # [1] Patching BuiltinFunction for the calltip/doc functions to be 
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

    # [1] Patching BuiltinName for the go to definition feature to simply work 
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
