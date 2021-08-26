# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------

"""Tests for status bar widgets."""

# Standard library imports
import os

# Third party imports
import pytest


# Local imports
from spyder.plugins.statusbar.widgets.tests.test_status import status_bar
from spyder.plugins.completion.widgets.status import CompletionStatus


def test_status_bar_completion_status(status_bar, qtbot):
    """Test status bar message with conda interpreter."""
    # We patch where the method is used not where it is imported from
    plugin, window = status_bar
    w = CompletionStatus(window)
    plugin.add_status_widget(w)

    value = 'env_type(env_name)'
    tool_tip = os.path.join('path', 'to', 'env_type', 'env_name')

    # Update status
    w.update_status(value, tool_tip)

    assert w.value == value
    assert w.get_tooltip() == tool_tip
