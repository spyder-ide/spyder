# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for plugin_client.py."""

# Standard library imports
import os.path as osp

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


@pytest.mark.parametrize("plugin_name", PLUGINS)
def test_plugin_client_extra_path(qtbot, plugin_name):
    """Test adding of extra path.

    Extra path is used for adding spyder_path to plugin clients.
    """
    extra_path = '/some/dummy/path'

    plugin = PluginClient(plugin_name=plugin_name, extra_path=[extra_path])
    plugin.run()
    python_path = plugin.process.processEnvironment().value('PYTHONPATH')
    assert extra_path in python_path.split(osp.pathsep)


if __name__ == "__main__":
    pytest.main()
