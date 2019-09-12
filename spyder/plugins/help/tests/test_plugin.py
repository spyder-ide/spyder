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
try:
    from unittest.mock import Mock, MagicMock
except ImportError:
    from mock import Mock, MagicMock  # Python 2

# Third party imports
from qtpy import PYQT_VERSION
from qtpy.QtWidgets import QMainWindow
from qtpy.QtWebEngineWidgets import WEBENGINE
import pytest
from flaky import flaky

# Local imports
from spyder.plugins.help.plugin import Help
from spyder.plugins.completion.fallback.utils import default_info_response


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
    help_plugin = Help(parent=window)
    window.setCentralWidget(help_plugin)

    webview = help_plugin.rich_text.webview._webview
    if WEBENGINE:
        help_plugin._webpage = webview.page()
    else:
        help_plugin._webpage = webview.page().mainFrame()

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


# =============================================================================
# Tests
# =============================================================================
@flaky(max_runs=3)
@pytest.mark.skipif(PYQT_VERSION > '5.10', reason='Segfaults in PyQt 5.10+')
def test_no_docs_message(help_plugin, qtbot):
    """
    Test that no docs message is shown when instrospection plugins
    can't get any info.
    """
    help_plugin.render_sphinx_doc(default_info_response())
    qtbot.waitUntil(lambda: check_text(help_plugin._webpage,
                                       "No documentation available"),
                    timeout=4000)


@flaky(max_runs=3)
@pytest.mark.skipif(PYQT_VERSION > '5.10', reason='Segfaults in PyQt 5.10+')
def test_no_further_docs_message(help_plugin, qtbot):
    """
    Test that no further docs message is shown when instrospection
    plugins can get partial info.
    """
    info = default_info_response()
    info['name'] = 'foo'
    info['argspec'] = '(x, y)'

    help_plugin.render_sphinx_doc(info)
    qtbot.waitUntil(lambda: check_text(help_plugin._webpage,
                                       "No further documentation available"),
                    timeout=3000)


@pytest.mark.skipif(PYQT_VERSION > '5.10', reason='Segfaults in PyQt 5.10+')
def test_help_opens_when_show_tutorial_unit(help_plugin, qtbot):
    """
    'Show tutorial' opens the help plugin if closed.

    Test fix for spyder-ide/spyder#6317.
    """
    MockDockwidget = MagicMock()
    MockDockwidget.return_value.isVisible.return_value = False
    mockDockwidget_instance = MockDockwidget()
    mock_show_rich_text = Mock()

    help_plugin.dockwidget = mockDockwidget_instance
    help_plugin.show_rich_text = mock_show_rich_text

    help_plugin.show_tutorial()
    qtbot.wait(100)

    assert mock_show_rich_text.call_count == 1

    MockDockwidget.return_value.isVisible.return_value = True
    mockDockwidget_instance = MockDockwidget()
    help_plugin.dockwidget = mockDockwidget_instance

    help_plugin.show_tutorial()
    qtbot.wait(100)
    assert mock_show_rich_text.call_count == 2


if __name__ == "__main__":
    pytest.main()
