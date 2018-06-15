# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for the history log
"""

# Standard library imports
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

# Third party imports
from qtpy.QtWidgets import QWidget
import pytest

# Local imports
from spyder.plugins.history import HistoryLog
from spyder.py3compat import to_text_string


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def history_plugin(qtbot):
    """History plugin fixture"""

    class MainMock(QWidget):
        def __getattr__(self, attr):
            return Mock()

    history = HistoryLog(parent=MainMock())
    qtbot.addWidget(history)
    return history


# =============================================================================
# Tests
# =============================================================================
def test_max_entries(history_plugin, tmpdir):
    """Test that history is truncated at max_entries."""
    max_entries = history_plugin.get_option('max_entries')

    # Write more than max entries in a test file
    history = ''
    for i in range(max_entries + 1):
        history = history + '{}\n'.format(i)

    history_file = tmpdir.join('history.py')
    history_file.write(history)

    # Load test file in plugin
    history_plugin.add_history(to_text_string(history_file))

    # Assert that we have max_entries after loading history and
    # that there's no 0 in the first line
    assert len(history_file.readlines()) == max_entries
    assert '0' not in history_file.readlines()[0]


if __name__ == "__main__":
    pytest.main()
