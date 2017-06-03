# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for misc.py
"""

# Standard library imports
import os

# Test library imports
import pytest

# Local imports
from spyder.utils.misc import get_common_path

def test_get_common_path():
    """Test getting the common path."""
    if os.name == 'nt':
        assert get_common_path([
                                'D:\\Python\\spyder-v21\\spyder\\widgets',
                                'D:\\Python\\spyder\\spyder\\utils',
                                'D:\\Python\\spyder\\spyder\\widgets',
                                'D:\\Python\\spyder-v21\\spyder\\utils',
                                ]) == 'D:\\Python'
    else:
        assert get_common_path([
                                '/Python/spyder-v21/spyder.widgets',
                                '/Python/spyder/spyder.utils',
                                '/Python/spyder/spyder.widgets',
                                '/Python/spyder-v21/spyder.utils',
                                ]) == '/Python'


if __name__ == "__main__":
    pytest.main()
