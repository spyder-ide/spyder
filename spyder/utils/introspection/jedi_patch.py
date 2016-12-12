# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Patching jedi:

[1] Adding numpydoc type returns to docstrings

[2] Adding type returns for compiled objects in jedi
"""

def apply():
    """Monkey patching jedi

    See [1] and [2] module docstring."""
    from spyder.utils.programs import is_module_installed
    if is_module_installed('jedi', '=0.9.0'):
        import jedi
    else:
        raise ImportError("jedi %s can't be patched" % jedi.__version__)

    # [1] Adding numpydoc type returns to docstrings
    from spyder.utils.introspection import docstrings
    jedi.evaluate.representation.docstrings = docstrings
    
    #[2] Adding type returns for compiled objects in jedi
    # Patching jedi.evaluate.compiled.CompiledObject...
    class PatchedCompiledObject(jedi.evaluate.compiled.CompiledObject):
        # ...adding docstrings int _execute_function...
        def _execute_function(self, evaluator, params):
            if self.type != 'funcdef':
                return
            #patching docstrings here
            from spyder.utils.introspection import docstrings
            types = docstrings.find_return_types(evaluator, self)
            if types:
                for result in types:
                    yield result
            #end patch
            for name in self._parse_function_doc()[1].split():
                try:
                    bltn_obj = _create_from_name(builtin, builtin, name)
                except AttributeError:
                    continue
                else:
                    if isinstance(bltn_obj, CompiledObject) and bltn_obj.obj is None:
                        # We want everything except None.
                        continue
                    for result in evaluator.execute(bltn_obj, params):
                        yield result
        # ...docstrings needs a raw_doc property
        @property
        def raw_doc(self):
            return self.doc

    jedi.evaluate.compiled.CompiledObject = PatchedCompiledObject
    return jedi
