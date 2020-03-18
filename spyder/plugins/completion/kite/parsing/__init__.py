# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import logging
import re

# Local imports
from spyder.py3compat import PY2


ident_re = r'[a-zA-Z_][a-zA-Z0-9_]*'
dotted_path_re = r'{ident}(?:\.{ident})*'.format(ident=ident_re)
ident_full_re = ident_re+r'\Z'


def find_returning_function_path(text, cursor, line_start='\n'):
    """
    :param text: Python source to analyze
    :param cursor: The starting cursor in the source
    :param line_start: line_start used in the source
    :return: a string representing the defintion value or None

    Finds the (syntactic) path of the function that
    returned the value of the name before the cursor.

    For example, the following input yields "bar.baz":
      foo = bar.baz("abc")
      foo.ca‸r
    """

    # Find the previous space to get the expression before the cursor
    for i, c in enumerate(reversed(text[:cursor])):
        if c == '.' or c == '_' or c.isalnum():
            continue
        break
    else:
        return None
    expr = text[cursor-i:cursor]

    # Take the first part of the expression, and check that it's a name
    name = expr.split('.', 1)[0]
    if not re.match(ident_full_re, name):
        return None

    if PY2:
        line_start = line_start.encode('utf-8')

    assign_re = r'{line_start}\s*{name}\s*=\s*({dotted_path})\('.format(
        line_start=re.escape(line_start),
        name=re.escape(name),
        dotted_path=dotted_path_re)
    match = None
    for match in re.finditer(assign_re, text[:cursor]):
        pass
    if match is None:
        return None

    return match.group(1)
