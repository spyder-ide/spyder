# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for the spyder.config.base module.
"""

# Third party imports
import pytest

# Local imports
from spyder.config.base import is_stable_version


# ============================================================================
# ---- Tests
# ============================================================================
@pytest.mark.parametrize('version_input, expected_result', [
    ('3.3.0', True), ('2', True), (('0', '5'), True), ('4.0.0b1', False),
    ('3.3.2.dev0', False), ('beta', False), (('2', '0', 'alpha'), False)])
def test_is_stable_version(version_input, expected_result):
    """Test that stable and non-stable versions are recognized correctly."""
    assert is_stable_version(version_input) == expected_result


if __name__ == '__main__':
    pytest.main()
