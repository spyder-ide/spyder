# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""
Tests for manager.py
"""

# Standard library imports
import sys

# Test library imports
import pytest

# Local imports
from spyder.utils.introspection.manager import IntrospectionManager


@pytest.fixture
def introspector_manager():
    """Create a basic instrospection manager."""
    introspector = IntrospectionManager()

    return introspector


def test_introspector_manager_extra_path(introspector_manager):
    """Test adding of extra path.

    Extra path is used for adding spyder_path to plugin clients.
    """
    introspector = introspector_manager
    extra_path = ['/some/dummy/path']

    assert set(introspector.sys_path) == set(sys.path)

    # Add extra path
    introspector.change_extra_path(extra_path)
    assert set(sys.path).issubset(set(introspector.sys_path))
    assert set(extra_path).issubset(set(introspector.sys_path))

    # Remove extra path
    introspector.change_extra_path([])
    print(introspector.sys_path)
    assert set(sys.path).issubset(set(introspector.sys_path))
    assert not set(extra_path).issubset(set(introspector.sys_path))
