# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Tests for the Existing Kernel Connection widget."""

# Third party imports
import pytest
from qtpy.QtCore import Qt

# Local imports
from spyder.plugins.ipythonconsole.widgets.kernelconnect import KernelConnectionDialog

# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def setup_dialog(qtbot):
    """Set up error report dialog."""
    widget = KernelConnectionDialog()
    qtbot.addWidget(widget)
    return widget


