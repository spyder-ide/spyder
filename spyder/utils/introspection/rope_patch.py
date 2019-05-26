# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Patching rope:

[1] For compatibility with Spyder's standalone version, built with py2exe or
    cx_Freeze

[2] For better performance, see this thread:
    https://groups.google.com/forum/#!topic/rope-dev/V95XMfICU3o

[3] To avoid considering folders without __init__.py as Python packages, thus
    avoiding side effects as non-working introspection features on a Python
    module or package when a folder in current directory has the same name.
    See this thread:
    https://groups.google.com/forum/#!topic/rope-dev/kkxLWmJo5hg

[4] To avoid rope adding a 2 spaces indent to every docstring it gets, because
    it breaks the work of Sphinx on the Help plugin. Also, to better
    control how to get calltips and docstrings of forced builtin objects.

[5] To make matplotlib return its docstrings in proper rst, instead of a mix
    of rst and plain text.
"""

def apply():
    """Monkey patching rope

    See [1], [2], [3], [4] and [5] in module docstring."""
    from spyder.utils.programs import is_module_installed
    if is_module_installed('rope', '<0.9.4'):
        import rope
        raise ImportError("rope %s can't be patched" % rope.VERSION)

    # [1] Patching project.Project for compatibility with py2exe/cx_Freeze
    #     distributions
    from spyder.config.base import is_py2exe_or_cx_Freeze
    if is_py2exe_or_cx_Freeze():
        from rope.base import project
        class PatchedProject(project.Project):
            def _default_config(self):
                # py2exe/cx_Freeze distribution
                from spyder.config.base import get_module_source_path
                fname = get_module_source_path('spyder',
                                               'default_config.py')
                return open(fname, 'rb').read()
        project.Project = PatchedProject

    # Patching pycore.PyCore...
    from rope.base import pycore
    class PatchedPyCore(pycore.PyCore):
        # [2] ...so that forced builtin modules (i.e. modules that were
        # declared as 'extension_modules' in rope preferences) will be indeed
        # recognized as builtins by rope, as expected
        #
        # This patch is included in rope 0.9.4+ but applying it anyway is ok
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
        # [3] ...to avoid considering folders without __init__.py as Python
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

    # [2] Patching BuiltinName for the go to definition feature to simply work
    # with forced builtins
    from rope.base import builtins, libutils, pyobjects
    import inspect
    import os.path as osp
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
                if path.endswith('pyc') and osp.isfile(path[:-1]):
                    path = path[:-1]
                pycore = self._pycore()
                if pycore and pycore.project:
                    resource = libutils.path_to_resource(pycore.project, path)
                    module = pyobjects.PyModule(pycore, None, resource)
                    return (module, lineno)
            return (None, None)
    builtins.BuiltinName = PatchedBuiltinName

    # [4] Patching several PyDocExtractor methods:
    # 1. get_doc:
    # To force rope to return the docstring of any object which has one, even
    # if it's not an instance of AbstractFunction, AbstractClass, or
    # AbstractModule.
    # Also, to use utils.dochelpers.getdoc to get docs from forced builtins.
    #
    # 2. _get_class_docstring and _get_single_function_docstring:
    # To not let rope add a 2 spaces indentation to every docstring, which was
    # breaking our rich text mode. The only value that we are modifying is the
    # 'indents' keyword of those methods, from 2 to 0.
    #
    # 3. get_calltip
    # To easily get calltips of forced builtins
    from rope.contrib import codeassist
    from spyder_kernels.utils.dochelpers import getdoc
    from rope.base import exceptions
    class PatchedPyDocExtractor(codeassist.PyDocExtractor):
        def get_builtin_doc(self, pyobject):
            buitin = pyobject.builtin
            return getdoc(buitin)

        def get_doc(self, pyobject):
            if hasattr(pyobject, 'builtin'):
                doc = self.get_builtin_doc(pyobject)
                return doc
            elif isinstance(pyobject, builtins.BuiltinModule):
                docstring = pyobject.get_doc()
                if docstring is not None:
                    docstring = self._trim_docstring(docstring)
                else:
                    docstring = ''
                # TODO: Add a module_name key, so that the name could appear
                # on the OI text filed but not be used by sphinx to render
                # the page
                doc = {'name': '',
                       'argspec': '',
                       'note': '',
                       'docstring': docstring
                       }
                return doc
            elif isinstance(pyobject, pyobjects.AbstractFunction):
                return self._get_function_docstring(pyobject)
            elif isinstance(pyobject, pyobjects.AbstractClass):
                return self._get_class_docstring(pyobject)
            elif isinstance(pyobject, pyobjects.AbstractModule):
                return self._trim_docstring(pyobject.get_doc())
            elif pyobject.get_doc() is not None:  # Spyder patch
                return self._trim_docstring(pyobject.get_doc())
            return None

        def get_calltip(self, pyobject, ignore_unknown=False, remove_self=False):
            if hasattr(pyobject, 'builtin'):
                doc = self.get_builtin_doc(pyobject)
                return doc['name'] + doc['argspec']
            try:
                if isinstance(pyobject, pyobjects.AbstractClass):
                    pyobject = pyobject['__init__'].get_object()
                if not isinstance(pyobject, pyobjects.AbstractFunction):
                    pyobject = pyobject['__call__'].get_object()
            except exceptions.AttributeNotFoundError:
                return None
            if ignore_unknown and not isinstance(pyobject, pyobjects.PyFunction):
                return
            if isinstance(pyobject, pyobjects.AbstractFunction):
                result = self._get_function_signature(pyobject, add_module=True)
                if remove_self and self._is_method(pyobject):
                    return result.replace('(self)', '()').replace('(self, ', '(')
                return result

        def _get_class_docstring(self, pyclass):
            contents = self._trim_docstring(pyclass.get_doc(), indents=0)
            supers = [super.get_name() for super in pyclass.get_superclasses()]
            doc = 'class %s(%s):\n\n' % (pyclass.get_name(), ', '.join(supers)) + contents

            if '__init__' in pyclass:
                init = pyclass['__init__'].get_object()
                if isinstance(init, pyobjects.AbstractFunction):
                    doc += '\n\n' + self._get_single_function_docstring(init)
            return doc

        def _get_single_function_docstring(self, pyfunction):
            docs = pyfunction.get_doc()
            docs = self._trim_docstring(docs, indents=0)
            return docs
    codeassist.PyDocExtractor = PatchedPyDocExtractor


    # [5] Get the right matplotlib docstrings for Help
    try:
        import matplotlib as mpl
        mpl.rcParams['docstring.hardcopy'] = True
    except:
        pass
