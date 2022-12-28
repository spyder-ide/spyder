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
from spyder_kernels.utils.dochelpers import (getargtxt, getdoc, getobj,
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


if __name__ == "__main__":
    pytest.main()
