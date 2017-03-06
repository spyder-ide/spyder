# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for dochelpers.py
"""

# Test library imports
import pytest

# Local imports
from spyder.utils.dochelpers import getargtxt, getdoc, getobj, isdefined

def test_dochelpers():
    """Test dochelpers."""
    class Test(object):
        def method(self, x, y=2):
            pass
    assert getargtxt(Test.__init__) == None
    assert getargtxt(Test.method) == ['x,', 'y=2']
    assert isdefined('numpy.take', force_import=True) == True
    assert isdefined('__import__') == True
    assert isdefined('.keys', force_import=True) == False
    assert getobj('globals') == 'globals'
    assert getobj('globals().keys') == None
    assert getobj('+scipy.signal.') == 'scipy.signal'
    assert getobj('4.') == '4'
    assert getdoc(sorted) == {'note': 'Function of builtins module',
                              'argspec': '(...)',
                              'docstring': 'Return a new list containing all '
                                           'items from the iterable in '
                                           'ascending order.\n\nA custom '
                                           'key function can be supplied to '
                                           'customise the sort order, and '
                                           'the\nreverse flag can be set to '
                                           'request the result in descending '
                                           'order.',
                              'name': 'sorted'}
    assert getargtxt(sorted) == None



if __name__ == "__main__":
    pytest.main()
