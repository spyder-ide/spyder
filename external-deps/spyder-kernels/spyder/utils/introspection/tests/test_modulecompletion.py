# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for module_completion.py
"""

# Stdlib imports
import sys

# Test library imports
import pytest

# Local imports
from spyder.utils.introspection.module_completion import get_preferred_submodules


@pytest.mark.skipif(sys.platform == 'darwin',
                    reason="It's very slow on Mac")
def test_module_completion():
    """Test module_completion."""
    assert 'numpy.linalg' in get_preferred_submodules()


if __name__ == "__main__":
    pytest.main()
