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
from types import SimpleNamespace
from unittest.mock import Mock

# Test library imports
import pytest

# Local imports
from spyder.utils import system
from spyder.utils.system import (memory_usage, windows_memory_usage)


@pytest.mark.parametrize('platform, expected', [('nt', 73.0), ('posix', 41.0)])
def test_memory_usage_platform_dispatch(monkeypatch, platform, expected):
    """Use the native Windows query without calling the slower psutil path."""
    native_query = Mock(return_value=73.0)
    virtual_query = Mock(return_value=SimpleNamespace(percent=41.0))
    monkeypatch.setattr(system, 'os', SimpleNamespace(name=platform))
    monkeypatch.setattr(system, 'windows_memory_usage', native_query)
    monkeypatch.setattr(system.psutil, 'virtual_memory', virtual_query)

    assert memory_usage() == expected
    if platform == 'nt':
        native_query.assert_called_once_with()
        virtual_query.assert_not_called()
    else:
        virtual_query.assert_called_once_with()
        native_query.assert_not_called()


def test_system():
    """Test system physical memory usage."""
    if os.name == 'nt':
        #  windll can only be imported if os.name = 'nt' or 'ce'
        assert windows_memory_usage() > 0
    else:
        assert memory_usage() > 0



if __name__ == "__main__":
    pytest.main()
