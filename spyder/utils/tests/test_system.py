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
        # Based on http://stackoverflow.com/a/42275253 RAM usage with only stdlib
        tot_m, used_m, free_m = map(int,
                                os.popen(
                                'free -t -m'
                                ).readlines()[-1].split()[1:])
        assert memory_usage() == round(used_m / tot_m, 2) * 100
    


if __name__ == "__main__":
    pytest.main()
