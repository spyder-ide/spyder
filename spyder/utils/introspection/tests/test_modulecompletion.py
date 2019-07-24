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
from spyder.py3compat import PY3
from spyder.utils.introspection.module_completion import get_preferred_submodules


@pytest.mark.skipif(sys.platform == 'darwin' and PY3,
                    reason="It's very slow in this combo")
def test_module_completion():
    """Test module_completion."""
    assert 'numpy.linalg' in get_preferred_submodules()


if __name__ == "__main__":
    pytest.main()
