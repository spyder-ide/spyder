# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for dependencies.py
"""

# Test library imports
import pytest

# Local imports
from spyder import dependencies
from spyder.plugins.console.widgets.dependencies import DependenciesDialog


@pytest.fixture
def dependencies_dialog(qtbot):
    """Set up dependency widget test."""
    widget = DependenciesDialog(None)
    qtbot.addWidget(widget)
    return widget


def test_dependencies(dependencies_dialog):
    """Run dependency widget test."""
    # Test sample
    dependencies.add("zmq", "zmq", "Run introspection services", ">=10.0")
    dependencies.add("foo", "foo", "Non-existent module", ">=1.0")
    dependencies.add("bar", "bar", "Non-existing optional module", ">=10.0",
                     kind=dependencies.OPTIONAL)
    dependencies_dialog.set_data(dependencies.DEPENDENCIES)
    dependencies_dialog.show()
    assert dependencies_dialog


if __name__ == "__main__":
    pytest.main()
