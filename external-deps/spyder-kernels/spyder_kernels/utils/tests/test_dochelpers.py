# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for dochelpers.py
"""

# Standard library imports
import os
import sys

# Test library imports
import pytest

# Local imports
from spyder_kernels.utils.dochelpers import (
    getargtxt, getargspecfromtext, getdoc, getobj, getsignaturefromtext,
    isdefined)
from spyder_kernels.py3compat import PY2


class Test(object):
    def method(self, x, y=2):
        pass


@pytest.mark.skipif(
    PY2 or os.name == 'nt', reason="Only works on Linux and Mac")
@pytest.mark.skipif(
    sys.platform == 'darwin' and sys.version_info[:2] == (3, 8),
    reason="Fails on Mac with Python 3.8")
def test_dochelpers():
    """Test dochelpers."""
    assert getargtxt(Test.method) == ['x, ', 'y=2']
    assert not getargtxt(Test.__init__)

    assert getdoc(sorted) == {
        'note': 'Function of builtins module',
        'argspec': '(...)',
        'docstring': 'Return a new list containing all items from the '
                     'iterable in ascending order.\n\nA custom key function '
                     'can be supplied to customize the sort order, and the\n'
                     'reverse flag can be set to request the result in '
                     'descending order.',
        'name': 'sorted'
    }
    assert not getargtxt(sorted)

    assert isdefined('numpy.take', force_import=True)
    assert isdefined('__import__')
    assert not isdefined('zzz', force_import=True)

    assert getobj('globals') == 'globals'
    assert not getobj('globals().keys')
    assert getobj('+scipy.signal.') == 'scipy.signal'
    assert getobj('4.') == '4'


@pytest.mark.skipif(PY2, reason="Fails in Python 2")
def test_no_signature():
    """
    Test that we can get documentation for objects for which Python can't get a
    signature directly because it gives an error.

    This is a regression test for issue spyder-ide/spyder#21148
    """
    import numpy as np
    doc = getdoc(np.where)
    signature = doc['argspec']
    assert signature and signature != "(...)" and signature.startswith("(")
    assert doc['docstring']


@pytest.mark.parametrize(
    'text, name, expected',
    [
         ('foo(x, y)', 'foo', '(x, y)'),
         ('foo(x, y)', '', '(x, y)'),
    ]
)
def test_getsignaturefromtext_py2(text, name, expected):
    assert getsignaturefromtext(text, name) == expected


@pytest.mark.skipif(PY2, reason="Don't work in Python 2")
@pytest.mark.parametrize(
    'text, name, expected',
    [
         # Simple text with and without name
         ('foo(x, y)', 'foo', '(x, y)'),
         ('foo(x, y)', '', '(x, y)'),
         # Single arg
         ('foo(x)', '', '(x)'),
         ('foo(x = {})', '', '(x = {})'),
         # Not a valid identifier
         ('1a(x, y)', '', ''),
         # Valid identifier
         ('a1(x, y=2)', '', '(x, y=2)'),
         # Unicode identifier with and without name
         ('ΣΔ(x, y)', 'ΣΔ', '(x, y)'),
         ('ΣΔ(x, y)', '', '(x, y)'),
         # Multiple signatures in a single line
         ('ΣΔ(x, y) foo(a, b)', '', '(x, y)'),
         ('1a(x, y) foo(a, b)', '', '(a, b)'),
         # Multiple signatures in multiple lines
         ('foo(a, b = 1)\n\nΣΔ(x, y=2)', '', '(a, b = 1)'),
         ('1a(a, b = 1)\n\nΣΔ(x, y=2)', '', '(x, y=2)'),
         # Signature after math operations
         ('2(3 + 5) 3*(99) ΣΔ(x, y)', '', '(x, y)'),
         # No identifier
         ('(x, y)', '', ''),
         ('foo (a=1, b = 2)', '', ''),
         # Empty signature
         ('foo()', '', ''),
         ('foo()', 'foo', ''),
    ]
)
def test_getsignaturefromtext(text, name, expected):
    assert getsignaturefromtext(text, name) == expected


def test_multisignature():
    """
    Test that we can get at least one signature from an object with multiple
    ones declared in its docstring.
    """
    def foo():
        """
        foo(x, y) foo(a, b)
        foo(c, d)
        """

    signature = getargspecfromtext(foo.__doc__)
    assert signature == "(x, y)"


def test_multiline_signature():
    """
    Test that we can get signatures splitted into multiple lines in a
    docstring.
    """
    def foo():
        """
        foo(x,
            y)

        This is a docstring.
        """

    signature = getargspecfromtext(foo.__doc__)
    assert signature.startswith("(x, ")


if __name__ == "__main__":
    pytest.main()
