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
from unittest.mock import Mock

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow
import pytest
from flaky import flaky

# Local imports
from spyder.config.manager import CONF
from spyder.plugins.console.plugin import Console


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def console_plugin(qtbot):
    """Console plugin fixture."""

    class MainWindowMock(QMainWindow):
        def __init__(self):
            super().__init__()
            self._INTERNAL_PLUGINS = {'internal_console': Console}

        def __getattr__(self, attr):
            if attr == '_PLUGINS':
                return {}
            elif attr != '_INTERNAL_PLUGINS':
                return Mock()
            else:
                return self.__dict__[attr]

    window = MainWindowMock()
    console_plugin = Console(parent=window, configuration=CONF)
    console_plugin.start_interpreter({})
    window.setCentralWidget(console_plugin.get_widget())

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
    shell = console_plugin.get_widget().shell

    # Run a simple code
    shell.insert_text('2+2', at_end=True)
    shell._key_enter()

    # Capture stdout and assert that it's the expected one
    sys_stream = capsys.readouterr()
    assert sys_stream.out == u'4\n'


@flaky(max_runs=3)
def test_completions(console_plugin, qtbot):
    """Test that completions work as expected."""
    shell = console_plugin.get_widget().shell

    # Get completions
    qtbot.keyClicks(shell, 'impor')
    qtbot.keyClick(shell, Qt.Key_Tab)
    qtbot.keyClick(shell.completion_widget, Qt.Key_Enter)

    # Assert completion was introduced in the console
    assert u'import' in shell.toPlainText()


def test_handle_exception(console_plugin, mocker):
    """Test that error dialog is called."""
    widget = console_plugin.get_widget()
    shell = widget.shell

    # Avoid showing the error dialog.
    mocker.patch('spyder.widgets.reporterror.SpyderErrorDialog.show',
                 return_value=None)

    # --- Test internal errors in Spyder
    # Write error in the console
    error = """
Traceback (most recent call last):
  File "/home/foo/miniconda3/envs/py37/lib/python3.7/code.py", line 90, in runcode
    exec(code, self.locals)
  File "<console>", line 2, in <module>
ZeroDivisionError: division by zero
"""
    shell.append_text_to_shell(error, error=True, prompt=False)

    # Make sure the error dialog was generated.
    assert widget.error_dlg is not None

    # Check that the traceback was shown in the error dialog.
    widget.error_dlg.details_btn.clicked.emit()
    assert 'foo' in widget.error_dlg.details.toPlainText()
    assert 'code.py' in widget.error_dlg.details.toPlainText()

    # Remove error dialog
    widget.error_dlg = None

    # --- Test PyLS errors
    console_plugin.handle_exception(
        dict(
            text=error,
            is_traceback=True,
            title='Internal Python Language Server error',
        )
    )

    # Make sure the error dialog was generated.
    assert widget.error_dlg is not None

    # Check that the traceback was shown in the error dialog.
    assert (widget.error_dlg.title.text() ==
            'Internal Python Language Server error')

    # Remove error dialog
    widget.error_dlg = None

    # --- Test segfault errors
    # Set config and call register so the dialog is created
    console_plugin.set_conf_option('previous_crash', error,
                                   section='main')
    console_plugin.register()

    # Make sure the error dialog was generated.
    assert widget.error_dlg is not None

    # Check that the traceback was shown in the error dialog.
    assert widget.error_dlg.title.text() == 'Segmentation fault crash'

    # Reset config
    console_plugin.set_conf_option('previous_crash', '', section='main')


if __name__ == "__main__":
    pytest.main()
