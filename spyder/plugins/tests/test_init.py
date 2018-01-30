# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Tests for the base plugin classes ('__init__.py')."""

# Standard library imports
import os
try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock  # Python 2

# 3rd party imports
import pytest
from flaky import flaky
from qtpy.QtCore import QEvent
from qtpy.QtWidgets import QTabBar

# Local imports
from spyder.plugins import TabFilter
from spyder.app import start
from spyder.config.main import CONF


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def main_window(request):
    """Main Window fixture"""
    # Disable unneeded introspection to save on startup time
    try:
        os.environ.pop('SPY_TEST_USE_INTROSPECTION')
    except KeyError:
        pass

    # Make sure single instance mode is disabled
    CONF.set('main', 'single_instance', False)

    # Start the window
    window = start.main()

    # Teardown
    def close_window():
        window.close()
    request.addfinalizer(close_window)

    return window


# =============================================================================
# Tests
# =============================================================================
@flaky(max_runs=3)
@pytest.mark.slow
def test_tabfilter_typeerror_full(main_window):
    """Test for #5813 ; event filter handles None indicies when moving tabs."""
    MockEvent = MagicMock()
    MockEvent.return_value.type.return_value = QEvent.MouseMove
    MockEvent.return_value.pos.return_value = 0
    mockEvent_instance = MockEvent()

    test_tabbar = main_window.findChildren(QTabBar)[0]
    test_tabfilter = TabFilter(test_tabbar, main_window)
    test_tabfilter.from_index = None
    test_tabfilter.moving = True

    assert test_tabfilter.eventFilter(None, mockEvent_instance)
    mockEvent_instance.pos.assert_called_once()


if __name__ == "__main__":
    pytest.main()
