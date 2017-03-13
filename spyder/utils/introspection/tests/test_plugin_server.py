# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for plugin_server.py
"""

# Standard library imports
import sys

# Test library imports
import pytest

# Local imports
from spyder.utils.introspection.plugin_server import PluginServer

def test_plugin_server(qtbot):
    """Test creation of a separate process for interacting with a plugin."""
    args = sys.argv[1:]
    if len(args) == 2:
       plugin = PluginServer(*args)
       plugin.run()
       assert plugin

if __name__ == "__main__":
    pytest.main()
