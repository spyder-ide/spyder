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

# Local imports
from spyder.widgets.browser import WebBrowser


@pytest.fixture
def browser(qtbot):
    """Set up WebBrowser."""
    WebBrowser.CONF_SECTION = ''
    widget = WebBrowser(None)
    widget.show()
    yield widget
    widget.webview.stop()
    widget.close()


def test_browser(browser):
    """Run web browser."""
    browser.set_home_url('https://www.google.com/')
    browser.go_home()
    assert browser


if __name__ == "__main__":
    pytest.main()
