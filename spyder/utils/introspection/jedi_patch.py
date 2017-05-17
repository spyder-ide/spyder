# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Patching jedi:

[1] Adding numpydoc type returns to docstrings

[2] Adding type returns for compiled objects in jedi

[3] Fixing introspection for matplotlib Axes objects

[4] Fixing None for parents in matplotlib Figure objects
"""


def apply():
    """Monkey patching jedi

    See [1] and [2] module docstring."""
    from spyder.utils.programs import is_module_installed
    if (is_module_installed('jedi', '=0.9.0') or
            is_module_installed('jedi', '>=0.10.0;<0.11')):
        import jedi
    else:
        raise ImportError("jedi not =0.9.0 or 0.10.0, can't be patched")

    # [1] Adding numpydoc type returns to docstrings
    from spyder.utils.introspection import numpy_docstr
    jedi.evaluate.representation.docstrings._search_param_in_numpydocstr = \
        numpy_docstr._search_param_in_numpydocstr
    jedi.evaluate.representation.docstrings.find_return_types = \
        numpy_docstr.find_return_types

    # [2] Adding type returns for compiled objects in jedi
    # Patching jedi.evaluate.compiled.CompiledObject...
    if is_module_installed('jedi', '=0.9.0'):
        from jedi.evaluate.compiled import (builtin, _create_from_name,
                                            debug, CompiledObject)

        def _execute_function(self, evaluator, params):
            if self.type != 'funcdef':
                return
            # patching docstrings here
            from spyder.utils.introspection import numpy_docstr
            types = numpy_docstr.find_return_types(evaluator, self)
            if types:
                for result in types:
                    debug.dbg('docstrings type return: %s in %s', result, self)
                    yield result
            # end patch
            for name in self._parse_function_doc()[1].split():
                try:
                    bltn_obj = _create_from_name(builtin, builtin, name)
                except AttributeError:
                    continue
                else:
                    if (isinstance(bltn_obj, CompiledObject) and
                            bltn_obj.obj is None):
                        # We want everything except None.
                        continue
                    for result in evaluator.execute(bltn_obj, params):
                        yield result

    else:  # Code for Jedi 0.10.0
        from jedi.evaluate.compiled import debug, create
        from jedi._compatibility import builtins as _builtins

        def _execute_function(self, params):
            from spyder.utils.introspection import numpy_docstr
            if self.type != 'funcdef':
                return
            types = set([])
            types |= set(numpy_docstr.find_return_types(self.parent_context,
                                                        self))
            debug.dbg('docstrings type return: %s in %s', types, self)
            for name in self._parse_function_doc()[1].split():
                try:
                    bltn_obj = getattr(_builtins, name)
                except AttributeError:
                    continue
                else:
                    if bltn_obj is None:
                        # We want to evaluate everything except None.
                        continue
                    bltn_obj = create(self.evaluator, bltn_obj)
                    types |= set(self.evaluator.execute(bltn_obj, params))
            for result in types:
                yield result

    jedi.evaluate.compiled.CompiledObject._execute_function = _execute_function

    if is_module_installed('jedi', '=0.9.0'):
        # [3] Fixing introspection for matplotlib Axes objects
        # Patching jedi.evaluate.precedence...
        from jedi.evaluate.precedence import tree, calculate

        def calculate_children(evaluator, children):
            """
            Calculate a list of children with operators.
            """
            iterator = iter(children)
            types = evaluator.eval_element(next(iterator))
            for operator in iterator:
                try:  # PATCH: Catches StopIteration error
                    right = next(iterator)
                    if tree.is_node(operator, 'comp_op'):  # not in / is not
                        operator = ' '.join(str(c.value) for c in
                                            operator.children)

                    # handle lazy evaluation of and/or here.
                    if operator in ('and', 'or'):
                        left_bools = set([left.py__bool__() for left in types])
                        if left_bools == set([True]):
                            if operator == 'and':
                                types = evaluator.eval_element(right)
                        elif left_bools == set([False]):
                            if operator != 'and':
                                types = evaluator.eval_element(right)
                        # Otherwise continue, because of uncertainty.
                    else:
                        types = calculate(evaluator, types, operator,
                                          evaluator.eval_element(right))
                except StopIteration:
                    debug.warning('calculate_children StopIteration %s', types)
            debug.dbg('calculate_children types %s', types)
            return types

        jedi.evaluate.precedence.calculate_children = calculate_children

        # [4] Fixing introspection for matplotlib Axes objects
        # Patching jedi.evaluate.precedence...
        from jedi.evaluate.representation import (InstanceName, Instance,
                                                  compiled, FunctionExecution,
                                                  InstanceElement)

        def get_instance_el(evaluator, instance, var, is_class_var=False):
            """
            Returns an InstanceElement if it makes sense, otherwise leaves the
            object untouched.

            Basically having an InstanceElement is context information. That is
            needed in quite a lot of cases, which includes Nodes like
            ``power``, that need to know where a self name comes from for
            example.
            """
            if isinstance(var, tree.Name):
                parent = get_instance_el(evaluator, instance, var.parent,
                                         is_class_var)
                return InstanceName(var, parent)
            # PATCH: compiled objects can be None
            elif var is None:
                return var
            elif var.type != 'funcdef' \
                    and isinstance(var, (Instance, compiled.CompiledObject,
                                   tree.Leaf, tree.Module, FunctionExecution)):
                return var

            var = evaluator.wrap(var)
            return InstanceElement(evaluator, instance, var, is_class_var)

        jedi.evaluate.representation.get_instance_el = get_instance_el

    return jedi
