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
from unittest.mock import call
import sys

# Third party imports
from flaky import flaky
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import SpyderPluginV2
from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.app.cli_options import get_options
from spyder.plugins.console.plugin import Console
from spyder.widgets.reporterror import SpyderErrorDialog


# =============================================================================
# Auxiliary classes
# =============================================================================
class MyPlugin(SpyderPluginV2):
    NAME = 'my-plugin'
    CONF_SECTION = 'my_plugin'


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def console_plugin(qtbot):
    """Console plugin fixture."""

    class MainWindowMock(QMainWindow):
        def __init__(self):
            # This avoids using the cli options passed to pytest
            sys_argv = [sys.argv[0]]
            self._cli_options = get_options(sys_argv)[0]
            super().__init__()

    window = MainWindowMock()
    console_plugin = PLUGIN_REGISTRY.register_plugin(
        window, Console, external=False)
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


@flaky(max_runs=20)
def test_handle_exception(console_plugin, mocker):
    """Test that error dialog is called."""
    widget = console_plugin.get_widget()
    shell = widget.shell

    # Avoid showing the error dialog.
    mocker.patch('spyder.widgets.reporterror.SpyderErrorDialog.show',
                 return_value=None)

    # --- Test internal errors in Spyder
    # Write error in the console
    error = """Traceback (most recent call last):
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
        ),
        sender=console_plugin
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
    console_plugin.set_conf('previous_crash', error,
                            section='main')
    console_plugin.on_initialize()

    # Make sure the error dialog was generated.
    assert widget.error_dlg is not None

    # Check that the traceback was shown in the error dialog.
    assert widget.error_dlg.title.text() == 'Segmentation fault crash'

    # Reset config
    console_plugin.set_conf('previous_crash', '', section='main')


def test_handle_warnings(console_plugin):
    """Test that we don't show warnings in our error dialog."""
    widget = console_plugin.get_widget()
    shell = widget.shell

    # Write warning in the console
    warning = ("/home/foo/bar.py:1926: UserWarning: baz\n"
               "Line 1\n"
               "Line 2\n"
               "  warnings.warn('baz')")
    shell.append_text_to_shell(warning, error=True, prompt=False)

    # Make sure the error dialog was not generated.
    assert widget.error_dlg is None


def test_report_external_repo(console_plugin, mocker):
    """
    Test that we use an external Github repo to report errors for
    external plugins.
    """
    widget = console_plugin.get_widget()
    my_plugin = MyPlugin(None)

    # Avoid showing the error dialog.
    mocker.patch('spyder.widgets.reporterror.SpyderErrorDialog.show',
                 return_value=None)

    # To get the external repo
    mocker.patch.object(SpyderErrorDialog, 'set_github_repo_org')

    # Error data (repo is added later)
    error_data = {
        "text": 'UserError',
        "is_traceback": True,
        "title": 'My plugin error',
        "label": '',
        "steps": '',
    }

    # Check that we throw an error if error_data doesn't contain repo
    with pytest.raises(SpyderAPIError) as excinfo:
        widget.handle_exception(error_data, sender=my_plugin)
        assert "does not define 'repo'" in str(excinfo.value)

    # Check that we don't allow our main repo in external plugins
    error_data['repo'] = 'spyder-ide/spyder'
    with pytest.raises(SpyderAPIError) as excinfo:
        widget.handle_exception(error_data, sender=my_plugin)
        assert "needs to be different from" in str(excinfo.value)

    # Make sure the error dialog is generated with the right repo
    error_data['repo'] = 'my-plugin-org/my-plugin'
    widget.handle_exception(error_data, sender=my_plugin)
    assert widget.error_dlg is not None

    # Assert we called the method that sets the repo in SpyderErrorDialog
    call_args = SpyderErrorDialog.set_github_repo_org.call_args
    assert call_args == call(error_data['repo'])

    # Assert repo is not necessary for internal plugins
    error_data.pop('repo')
    widget.error_dlg = None
    widget.handle_exception(error_data, sender=console_plugin)
    assert widget.error_dlg is not None

    # Assert we use our main repo for internal plugins
    call_args = SpyderErrorDialog.set_github_repo_org.call_args
    assert call_args == call('spyder-ide/spyder')


if __name__ == "__main__":
    pytest.main()
