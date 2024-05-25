# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for finding plugins.
"""

import pytest

from spyder.api.plugins import Plugins
from spyder.api.utils import get_class_values
from spyder.app.find_plugins import (
    find_internal_plugins, find_external_plugins)
from spyder.config.base import running_in_ci


def test_find_internal_plugins():
    """Test that we return all internal plugins available."""
    # We don't take the 'All' plugin into account here because it's not
    # really a plugin.
    expected_names = get_class_values(Plugins)
    expected_names.remove(Plugins.All)

    # Dictionary of internal plugins
    internal_plugins = find_internal_plugins()

    # Lengths must be the same
    assert len(expected_names) == len(internal_plugins.values())

    # Names must be the same
    assert sorted(expected_names) == sorted(list(internal_plugins.keys()))


@pytest.mark.skipif(not running_in_ci(), reason="Only works in CIs")
def test_find_external_plugins():
    """Test that we return the external plugins installed when testing."""
    internal_names = get_class_values(Plugins)
    expected_names = ['spyder_boilerplate']
    expected_special_attrs = {
        'spyder_boilerplate': [
            'spyder_boilerplate.spyder.plugin',
            'spyder-boilerplate',
            '0.0.1'
        ]
    }

    # Dictionary of external plugins
    external_plugins = find_external_plugins()

    # External plugins must be the ones installed while testing
    assert len(external_plugins.keys()) == len(expected_names)

    # Names must not be among internal plugins
    for name in external_plugins.keys():
        assert name not in internal_names

    # Names must be the expected ones.
    assert sorted(expected_names) == sorted(list(external_plugins.keys()))

    # Assert special attributes are present
    for name in external_plugins.keys():
        plugin_class = external_plugins[name]
        special_attrs = [
            plugin_class._spyder_module_name,
            plugin_class._spyder_package_name,
            plugin_class._spyder_version
        ]

        assert expected_special_attrs[name] == special_attrs
