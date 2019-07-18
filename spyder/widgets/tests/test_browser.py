# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for browser.py
"""

# Test library imports
import pytest
from qtpy.QtWebEngineWidgets import QWebEnginePage
# Local imports
from spyder.widgets.browser import WebBrowser, WebView


@pytest.fixture
def browser(qtbot):
    """Set up WebBrowser."""
    widget = WebBrowser()
    qtbot.addWidget(widget)
    return widget


def test_browser(browser):
    """Run web browser."""
    browser.set_home_url('https://www.google.com/')
    browser.go_home()
    browser.show()
    assert browser


def test_webview_open_regression(qtbot):
    """Check creating of new window."""
    wb = WebView(None)
    qtbot.addWidget(wb)
    wb.setUrl('problem_url')
    wb.createWindow(QWebEnginePage.WebBrowserWindow)


if __name__ == "__main__":
    pytest.main()
