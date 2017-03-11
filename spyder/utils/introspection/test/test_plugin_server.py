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

@pytest.fixture
def setup_plugin_server(qtbot):
    "Setup the plugin in a separate proccess."    
    args = sys.argv[1:]
    if not len(args) == 2:
        return
    plugin = PluginServer(*args)
    qtbot.addWidget(plugin)
    
    return plugin

def test_plugin_server(qtbot):
    """Test creation of a separate process for interacting with a plugin."""
    plugin = setup_plugin_server(qtbot)
    if plugin:
        plugin.run()
        assert plugin


if __name__ == "__main__":
    pytest.main()
