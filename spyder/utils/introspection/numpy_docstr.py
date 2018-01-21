# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Contents in this file are taken from
#
# https://github.com/davidhalter/jedi/pull/796
#
# to patch Jedi 0.9.0 (it probably doesn't work with
# higher versions)


from ast import literal_eval
import re

from spyder.utils.programs import is_module_installed

from jedi._compatibility import u, is_py3
from jedi.evaluate.cache import memoize_default
from jedi.evaluate.docstrings import (_evaluate_for_statement_string,
                                      _strip_rst_role,
                                      DOCSTRING_RETURN_PATTERNS)
from numpydoc.docscrape import NumpyDocString


def _expand_typestr(p_type):
    """
    Attempts to interpret the possible types
    """
    # Check if alternative types are specified
    if re.search(r'\bor\b', p_type):
        types = [t.strip() for t in p_type.split('or')]
    # Check if type has a set of valid literal values
    elif p_type.startswith('{'):
        if not is_py3:
            # python2 does not support literal set evals
            # workaround this by using lists instead
            p_type = p_type.replace('{', '[').replace('}', ']')
        types = set(type(x).__name__ for x in literal_eval(p_type))
        types = list(types)
    # Otherwise just return the typestr wrapped in a list
    else:
        types = [p_type]
    return types


def _search_param_in_numpydocstr(docstr, param_str):
    r"""
    Search `docstr` (in numpydoc format) for type(-s) of `param_str`.
    >>> from jedi.evaluate.docstrings import *  # NOQA
    >>> from jedi.evaluate.docstrings import _search_param_in_numpydocstr
    >>> docstr = (
    ...    'Parameters\n'
    ...    '----------\n'
    ...    'x : ndarray\n'
    ...    'y : int or str or list\n'
    ...    'z : {"foo", "bar", 100500}, optional\n'
    ... )
    >>> _search_param_in_numpydocstr(docstr, 'x')
    ['ndarray']
    >>> sorted(_search_param_in_numpydocstr(docstr, 'y'))
    ['int', 'list', 'str']
    >>> sorted(_search_param_in_numpydocstr(docstr, 'z'))
    ['int', 'str']
    """
    params = NumpyDocString(docstr)._parsed_data['Parameters']
    for p_name, p_type, p_descr in params:
        if p_name == param_str:
            m = re.match(r'([^,]+(,[^,]+)*?)(,[ ]*optional)?$', p_type)
            if m:
                p_type = m.group(1)
            return _expand_typestr(p_type)
    return []


def _search_return_in_numpydocstr(docstr):
    r"""
    Search `docstr` (in numpydoc format) for type(-s) of `param_str`.
    >>> from jedi.evaluate.docstrings import *  # NOQA
    >>> from jedi.evaluate.docstrings import _search_return_in_numpydocstr
    >>> from jedi.evaluate.docstrings import _expand_typestr
    >>> docstr = (
    ...    'Returns\n'
    ...    '----------\n'
    ...    'int\n'
    ...    '    can return an anoymous integer\n'
    ...    'out : ndarray\n'
    ...    '    can return a named value\n'
    ... )
    >>> _search_return_in_numpydocstr(docstr)
    ['int', 'ndarray']
    """
    doc = NumpyDocString(docstr)
    returns = doc._parsed_data['Returns']
    returns += doc._parsed_data['Yields']
    found = []
    for p_name, p_type, p_descr in returns:
        if not p_type:
            p_type = p_name
            p_name = ''

        m = re.match(r'([^,]+(,[^,]+)*?)$', p_type)
        if m:
            p_type = m.group(1)
        found.extend(_expand_typestr(p_type))
    return found

# Caching disabled because jedi_patch breaks it
# @memoize_default(None, evaluator_is_first_arg=True)
def find_return_types(module_context, func):
    """
    Determines a set of potential return types for `func` using docstring hints
    :type evaluator: jedi.evaluate.Evaluator
    :type param: jedi.parser.tree.Param
    :rtype: list
    >>> from jedi.evaluate.docstrings import *  # NOQA
    >>> from jedi.evaluate.docstrings import _search_param_in_docstr
    >>> from jedi.evaluate.docstrings import _evaluate_for_statement_string
    >>> from jedi.evaluate.docstrings import _search_return_in_gooogledocstr
    >>> from jedi.evaluate.docstrings import _search_return_in_numpydocstr
    >>> from jedi._compatibility import builtins
    >>> source = open(jedi.evaluate.docstrings.__file__.replace('.pyc', '.py'), 'r').read()
    >>> script = jedi.Script(source)
    >>> evaluator = script._evaluator
    >>> func = script._get_module().names_dict['find_return_types'][0].parent
    >>> types = find_return_types(evaluator, func)
    >>> print('types = %r' % (types,))
    >>> assert len(types) == 1
    >>> assert types[0].base.obj is builtins.list
    """
    def search_return_in_docstr(docstr):
        # Check for Sphinx/Epydoc return hint
        for p in DOCSTRING_RETURN_PATTERNS:
            match = p.search(docstr)
            if match:
                return [_strip_rst_role(match.group(1))]
        found = []

        if not found:
            # Check for numpy style return hint
            found = _search_return_in_numpydocstr(docstr)
        return found
    try:
        docstr = u(func.raw_doc)
    except AttributeError:
        docstr = u(func.doc)
    types = []
    for type_str in search_return_in_docstr(docstr):
        if is_module_installed('jedi', '>=0.10.0;<0.11'):
            type_ = _evaluate_for_statement_string(module_context, type_str)
        else:
            module = func.get_parent_until()
            type_ = _evaluate_for_statement_string(module_context,
                                                   type_str, module)
        types.extend(type_)
    return types
