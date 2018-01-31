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

# Third party imports
from qtpy.QtWebEngineWidgets import WEBENGINE
import pytest

# Local imports
from spyder.plugins.help import Help
from spyder.utils.introspection.utils import default_info_response


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def help_plugin(qtbot):
    """Help plugin fixture"""
    help_plugin = Help()
    webview = help_plugin.rich_text.webview._webview

    if WEBENGINE:
        help_plugin._webpage = webview.page()
    else:
        help_plugin._webpage = webview.page().mainFrame()

    qtbot.addWidget(help_plugin)
    return help_plugin


# =============================================================================
# Tests
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


def test_no_docs_message(help_plugin, qtbot):
    """
    Test that no docs message is shown when instrospection plugins
    can't get any info.
    """
    help_plugin.render_sphinx_doc(default_info_response())
    qtbot.waitUntil(lambda: check_text(help_plugin._webpage,
                                       "No documentation available"),
                    timeout=2000)


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
                    timeout=2000)


if __name__ == "__main__":
    pytest.main()
