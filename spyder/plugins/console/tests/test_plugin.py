# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for the console plugin.
"""

# Standard library imports
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow
import pytest
from flaky import flaky

# Local imports
from spyder.plugins.console.plugin import Console


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def console_plugin(qtbot):
    """Console plugin fixture."""

    class MainWindowMock(QMainWindow):
        def __getattr__(self, attr):
            return Mock()

    window = MainWindowMock()
    console_plugin = Console(parent=window)
    window.setCentralWidget(console_plugin)

    qtbot.addWidget(window)
    window.resize(640, 480)
    window.show()
    return console_plugin


# =============================================================================
# Tests
# =============================================================================
@flaky(max_runs=3)
def test_run_code(console_plugin, capsys):
    """Test that the console runs code."""
    shell = console_plugin.shell

    # Run a simple code
    shell.insert_text('2+2', at_end=True)
    shell._key_enter()

    # Capture stdout and assert that it's the expected one
    sys_stream = capsys.readouterr()
    assert sys_stream.out == u'4\n'


@flaky(max_runs=3)
def test_completions(console_plugin, qtbot):
    """Test that completions work as expected."""
    shell = console_plugin.shell

    # Get completions
    qtbot.keyClicks(shell, 'impor')
    qtbot.keyClick(shell, Qt.Key_Tab)
    qtbot.keyClick(shell.completion_widget, Qt.Key_Enter)

    # Assert completion was introduced in the console
    assert u'import' in shell.toPlainText()


if __name__ == "__main__":
    pytest.main()
