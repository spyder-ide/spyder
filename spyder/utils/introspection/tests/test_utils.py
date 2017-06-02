# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for utils.py
"""

# Standard library imports
import pickle

# Test library imports
import pytest

# Local imports
from spyder.utils.introspection.utils import CodeInfo

def test_codeinfo():
    """Test CodeInfo."""
    code = 'import numpy'
    test = CodeInfo('test', code, len(code) - 2)
    assert test.obj == 'num'
    assert test.full_obj == 'numpy'
    test2 = CodeInfo('test', code, len(code) - 2)
    assert test == test2
    test3 = pickle.loads(pickle.dumps(test2.__dict__))
    assert test3['full_obj'] == 'numpy'    

if __name__ == "__main__":
    pytest.main()
