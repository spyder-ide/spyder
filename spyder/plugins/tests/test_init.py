# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Tests for the base plugin classes ('__init__.py')."""

# Standard library imports
try:
    from unittest.mock import Mock, MagicMock
except ImportError:
    from mock import Mock, MagicMock  # Python 2

# 3rd party imports
import pytest
from qtpy.QtCore import QEvent

# Local imports
from spyder.plugins import TabFilter


# =============================================================================
# Tests
# =============================================================================
def test_tabfilter_typeerror_simple():
    """Test for #5813 ; event filter handles None indicies when moving tabs."""
    MockEvent = MagicMock()
    MockEvent.return_value.type.return_value = QEvent.MouseMove
    MockEvent.return_value.pos.return_value = 0
    mockEvent_instance = MockEvent()

    MockTabBar = MagicMock()
    MockTabBar.return_value.tabAt.return_value = 0
    mockTabBar_instance = MockTabBar()

    MockMainWindow = Mock()
    mockMainWindow_instance = MockMainWindow()

    test_tabfilter = TabFilter(mockTabBar_instance, mockMainWindow_instance)
    test_tabfilter.from_index = None
    test_tabfilter.moving = True

    assert test_tabfilter.eventFilter(None, mockEvent_instance)
    assert mockEvent_instance.pos.call_count == 1
    assert mockTabBar_instance.tabAt.call_count == 1


if __name__ == "__main__":
    pytest.main()
