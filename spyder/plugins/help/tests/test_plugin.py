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
    help_plugin = Help(parent=window, configuration=None)
    help_widget = help_plugin.get_widget()
    webview = help_widget.rich_text.webview._webview

    window.setCentralWidget(help_widget)

    if WEBENGINE:
        help_widget._webpage = webview.page()
    else:
        help_widget._webpage = webview.page().mainFrame()

    qtbot.addWidget(window)
    window.show()
    return help_plugin


# =============================================================================
# Utility functions
# =============================================================================
def check_text(widget, text):
    """Check if some text is present in a widget."""
    if WEBENGINE:
        def callback(data):
            global html
            html = data
        widget.toHtml(callback)
        try:
            return text in html
        except NameError:
            return False
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
    qtbot.waitUntil(lambda: check_text(help_plugin.get_widget()._webpage,
                                       "No documentation available"),
                    timeout=4000)


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
    qtbot.waitUntil(lambda: check_text(help_plugin.get_widget()._webpage,
                                       "No further documentation available"),
                    timeout=3000)


def test_help_opens_when_show_tutorial_unit(help_plugin, qtbot):
    """
    'Show tutorial' opens the help plugin if closed.

    Test fix for spyder-ide/spyder#6317.
    """
    help_plugin.switch_to_plugin = Mock()
    help_plugin.show_tutorial()
    assert help_plugin.switch_to_plugin.call_count == 1


if __name__ == "__main__":
    pytest.main()
