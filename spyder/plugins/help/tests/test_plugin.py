# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for the Spyder `help` plugn, `help.py`.
"""

# Standard library imports
from unittest.mock import Mock

# Third party imports
from qtpy.QtWidgets import QMainWindow
from qtpy.QtWebEngineWidgets import WEBENGINE
import pytest
from flaky import flaky

# Local imports
from spyder.config.manager import CONF
from spyder.plugins.help.plugin import Help


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def help_plugin(qtbot):
    """Help plugin fixture"""

    class MainMock(QMainWindow):
        def __getattr__(self, attr):
            if attr == 'ipyconsole' or attr == 'editor':
                return None
            else:
                return Mock()

    window = MainMock()
    help_plugin = Help(parent=window, configuration=CONF)
    help_widget = help_plugin.get_widget()
    webview = help_widget.rich_text.webview._webview

    window.setCentralWidget(help_widget)

    if WEBENGINE:
        help_widget._webpage = webview.page()
        with qtbot.waitSignal(help_widget._webpage.loadFinished):
            window.show()
    else:
        help_widget._webpage = webview.page().mainFrame()
        window.show()

    qtbot.addWidget(window)
    return help_plugin


# =============================================================================
# Utility functions
# =============================================================================
def check_text(widget, text, qtbot):
    """Check if some text is present in a widget."""
    if WEBENGINE:
        with qtbot.waitCallback(timeout=20000) as cb:
            widget.toHtml(cb)
        return text in cb.args[0]
    else:
        return text in widget.toHtml()


def default_info_response():
    """Default response when asking for info."""
    return dict(name='', argspec='', note='', docstring='', calltip='',
                obj_text='')


# =============================================================================
# Tests
# =============================================================================
@flaky(max_runs=3)
def test_no_docs_message(help_plugin, qtbot):
    """
    Test that no docs message is shown when instrospection plugins
    can't get any info.
    """
    help_plugin.set_editor_doc(default_info_response())
    qtbot.waitUntil(
        lambda: check_text(
            help_plugin.get_widget()._webpage,
            "No documentation available",
            qtbot,
        ),
        timeout=20000,
    )


@flaky(max_runs=3)
def test_no_further_docs_message(help_plugin, qtbot):
    """
    Test that no further docs message is shown when instrospection
    plugins can get partial info.
    """
    info = default_info_response()
    info['name'] = 'foo'
    info['argspec'] = '(x, y)'

    help_plugin.set_editor_doc(info)
    qtbot.waitUntil(
        lambda: check_text(
            help_plugin.get_widget()._webpage,
            "No further documentation available",
            qtbot,
        ),
        timeout=20000,
    )


def test_help_opens_when_show_tutorial_unit(help_plugin):
    """
    'Show tutorial' opens the help plugin if closed.

    Test fix for spyder-ide/spyder#6317.
    """
    help_plugin.switch_to_plugin = Mock()
    help_plugin.show_tutorial()
    assert help_plugin.switch_to_plugin.call_count == 1


def test_disable_show_source_on_close(help_plugin):
    widget = help_plugin.get_widget()

    # Enable show_source and check options are set as expected
    widget.show_source_action.setChecked(True)
    assert help_plugin.get_conf("show_source")
    assert help_plugin.get_conf("plain_mode")
    assert not help_plugin.get_conf("rich_mode")

    # Simulate the plugin was closed
    help_plugin.on_close()

    # Check options were set as expected
    assert not help_plugin.get_conf("show_source")
    assert not help_plugin.get_conf("plain_mode")
    assert help_plugin.get_conf("rich_mode")


if __name__ == "__main__":
    pytest.main()
