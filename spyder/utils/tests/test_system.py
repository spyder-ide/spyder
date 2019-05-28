# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for system.py
"""

# Standard library imports
import os

# Test library imports
import pytest

# Local imports
from spyder.utils.system import (memory_usage, windows_memory_usage)

def test_system():
    """Test system physical memory usage."""
    if os.name == 'nt':
        #  windll can only be imported if os.name = 'nt' or 'ce'
        assert windows_memory_usage() > 0
    else:
        assert memory_usage() > 0



if __name__ == "__main__":
    pytest.main()
