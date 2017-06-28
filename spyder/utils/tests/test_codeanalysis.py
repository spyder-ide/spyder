# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for codeanalysis.py
"""

# Standard library imports
import os

# Test library imports
import pytest

# Local imports
from spyder.utils.codeanalysis import (check_with_pep8, check_with_pyflakes,
                                       find_tasks)
from spyder.py3compat import PY2

TEST_FILE = os.path.join(os.path.dirname(__file__), 'data/example.py')

def test_codeanalysis():
    """Test codeanalysis with pyflakes and pep8."""
    code = open(TEST_FILE).read()
    check_results = check_with_pyflakes(code, TEST_FILE) + \
                    check_with_pep8(code, TEST_FILE) + find_tasks(code)
    if PY2:
        num_results = 87
    else:
        num_results = 88
    assert len(check_results) == num_results


if __name__ == "__main__":
    pytest.main()
