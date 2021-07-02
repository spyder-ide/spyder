# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import sys
from textwrap import dedent

from pylsp import uris
from pylsp.plugins.folding import pylsp_folding_range
from pylsp.workspace import Document

DOC_URI = uris.from_fs_path(__file__)
DOC = dedent("""
def func(arg1, arg2, arg3,
         arg4, arg5, default=func(
             2, 3, 4
         )):
    return (2, 3,
            4, 5)

@decorator(
    param1,
    param2
)
def decorated_func(x, y, z):
    if x:
        return y
    elif y:
        return z
    elif x + y > z:
        return True
    else:
        return x

class A():
    def method(self, x1):
        def inner():
            return x1

        if x2:
            func(3, 4, 5, 6,
                 7)
        elif x3 < 2:
            pass
        else:
            more_complex_func(2, 3, 4, 5, 6,
                              8)
        return inner

a = 2
operation = (a_large_variable_that_fills_all_space +
             other_embarrasingly_long_variable - 2 * 3 / 5)

(a, b, c,
 d, e, f) = func(3, 4, 5, 6,
                 7, 8, 9, 10)

for i in range(0, 3):
    i += 1
    while x < i:
        expr = (2, 4)
        a = func(expr + i, arg2, arg3, arg4,
                 arg5, var(2, 3, 4,
                           5))
    for j in range(0, i):
        if i % 2 == 1:
            pass

compren = [x for x in range(0, 3)
           if x == 2]

with open('doc', 'r') as f:
    try:
        f / 0
    except:
        pass
    finally:
        raise SomeException()

def testC():
    pass
""")

SYNTAX_ERR = dedent("""
def func(arg1, arg2, arg3,
         arg4, arg5, default=func(
             2, 3, 4
         )):
    return (2, 3,
            4, 5)

class A(:
    pass

a = 2
operation = (a_large_variable_that_fills_all_space +
             other_embarrasingly_long_variable - 2 * 3 /

(a, b, c,
 d, e, f) = func(3, 4, 5, 6,
                 7, 8, 9, 10
a = 2
for i in range(0, 3)
    i += 1
    while x < i:
        expr = (2, 4)
        a = func(expr + i, arg2, arg3, arg4,
                 arg5, var(2, 3, 4,
                           5))
    for j in range(0, i):
        if i % 2 == 1:
            pass
""")


def test_folding(workspace):
    doc = Document(DOC_URI, workspace, DOC)
    ranges = pylsp_folding_range(doc)
    expected = [{'startLine': 1, 'endLine': 6},
                {'startLine': 2, 'endLine': 3},
                {'startLine': 5, 'endLine': 6},
                {'startLine': 8, 'endLine': 11},
                {'startLine': 12, 'endLine': 20},
                {'startLine': 13, 'endLine': 14},
                {'startLine': 15, 'endLine': 16},
                {'startLine': 17, 'endLine': 18},
                {'startLine': 19, 'endLine': 20},
                {'startLine': 22, 'endLine': 35},
                {'startLine': 23, 'endLine': 35},
                {'startLine': 24, 'endLine': 25},
                {'startLine': 27, 'endLine': 29},
                {'startLine': 28, 'endLine': 29},
                {'startLine': 30, 'endLine': 31},
                {'startLine': 32, 'endLine': 34},
                {'startLine': 33, 'endLine': 34},
                {'startLine': 38, 'endLine': 39},
                {'startLine': 41, 'endLine': 43},
                {'startLine': 42, 'endLine': 43},
                {'startLine': 45, 'endLine': 54},
                {'startLine': 47, 'endLine': 51},
                {'startLine': 49, 'endLine': 51},
                {'startLine': 50, 'endLine': 51},
                {'startLine': 52, 'endLine': 54},
                {'startLine': 53, 'endLine': 54},
                {'startLine': 56, 'endLine': 57},
                {'startLine': 59, 'endLine': 65},
                {'startLine': 60, 'endLine': 61},
                {'startLine': 62, 'endLine': 63},
                {'startLine': 64, 'endLine': 65},
                {'startLine': 67, 'endLine': 68}]
    if sys.version_info[:2] >= (3, 9):
        # the argument list of the decorator is also folded in Python >= 3.9
        expected.insert(4, {'startLine': 9, 'endLine': 10})

    assert ranges == expected


def test_folding_syntax_error(workspace):
    doc = Document(DOC_URI, workspace, SYNTAX_ERR)
    ranges = pylsp_folding_range(doc)
    expected = [{'startLine': 1, 'endLine': 6},
                {'startLine': 2, 'endLine': 3},
                {'startLine': 5, 'endLine': 6},
                {'startLine': 8, 'endLine': 9},
                {'startLine': 12, 'endLine': 13},
                {'startLine': 15, 'endLine': 17},
                {'startLine': 16, 'endLine': 17},
                {'startLine': 19, 'endLine': 28},
                {'startLine': 21, 'endLine': 25},
                {'startLine': 23, 'endLine': 25},
                {'startLine': 24, 'endLine': 25},
                {'startLine': 26, 'endLine': 28},
                {'startLine': 27, 'endLine': 28}]
    assert ranges == expected
