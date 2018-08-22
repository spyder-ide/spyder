# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for plugin_client.py."""

# Test library imports
import pytest

# Local imports
from spyder.utils.introspection.plugin_client import PluginClient
from spyder.utils.introspection.manager import PLUGINS


@pytest.mark.parametrize("plugin_name", PLUGINS)
def test_plugin_client(qtbot, plugin_name):
    """Test creation of the diferent plugin clients."""
    plugin = PluginClient(plugin_name=plugin_name)

    assert plugin


if __name__ == "__main__":
    pytest.main()
