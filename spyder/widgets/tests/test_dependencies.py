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
from spyder.widgets.dependencies import DependenciesDialog
from spyder import dependencies


@pytest.fixture
def dependencies_dialog(qtbot):
    """Set up dependency widget test."""
    widget = DependenciesDialog(None)
    qtbot.addWidget(widget)
    return widget


def test_dependencies(dependencies_dialog):
    """Run dependency widget test."""
    # Test sample
    dependencies.add("zmq", "Run introspection services", ">=10.0")
    dependencies.add("foo", "Non-existent module", ">=1.0")
    dependencies.add("bar", "Non-existing optional module", ">=10.0", optional=True)

    dependencies_dialog.set_data(dependencies.DEPENDENCIES)
    dependencies_dialog.show()
    assert dependencies_dialog


if __name__ == "__main__":
    pytest.main()
