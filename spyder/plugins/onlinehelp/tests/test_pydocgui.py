# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for pydocgui.py
"""

# Test library imports
import pytest

# Local imports
from spyder.plugins.onlinehelp.widgets import PydocBrowser


@pytest.fixture
def pydocbrowser(qtbot):
    """Set up pydocbrowser."""
    widget = PydocBrowser(None)
    qtbot.addWidget(widget)
    return qtbot, widget


def test_pydocbrowser(pydocbrowser):
    """Run Pydoc Browser."""
    qtbot, browser = pydocbrowser
    assert pydocbrowser


@pytest.mark.parametrize(
    "lib", [('pandas', 'pandas', 11),
            ('str', 'class str', 1)])
def test_get_pydoc(pydocbrowser, lib):
    """
    Go to the documentation by url.
    Regression test for spyder-ide/spyder#10740
    """
    qtbot, browser = pydocbrowser
    element, doc, matches = lib
    webview = browser.webview
    with qtbot.waitSignal(webview.loadFinished, timeout=2000):
        browser.initialize()
    browser.show()
    element_url = browser.text_to_url(element)
    with qtbot.waitSignal(webview.loadFinished):
        browser.set_url(element_url)
    qtbot.waitUntil(lambda: webview.get_number_matches(doc) == matches)


if __name__ == "__main__":
    pytest.main()
