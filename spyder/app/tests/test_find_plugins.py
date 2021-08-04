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

from spyder.api.plugins import Plugins
from spyder.api.utils import get_class_values
from spyder.app.find_plugins import find_internal_plugins


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
