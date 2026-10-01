# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for pydocgui.py
"""
# Standard library imports
import os
import sys
from unittest.mock import MagicMock

# Test library imports
import numpy as np
from numpy.lib import NumpyVersion
import pytest
from flaky import flaky

# Local imports
from spyder.config.base import running_in_ci
from spyder.plugins.onlinehelp.pydoc_patch import _url_handler
from spyder.plugins.onlinehelp.widgets import PydocBrowser


@pytest.fixture
def pydocbrowser(qtbot):
    """Set up pydocbrowser."""
    plugin_mock = MagicMock()
    plugin_mock.CONF_SECTION = 'onlinehelp'
    widget = PydocBrowser(parent=None, plugin=plugin_mock, name='pydoc')
    with qtbot.waitSignal(widget.webview.loadFinished, timeout=20000):
        widget._setup()
        widget.setup()
        widget.resize(640, 480)
        widget.show()
        widget.initialize(force=True)
    yield widget
    widget.close()


@flaky(max_runs=5)
@pytest.mark.order(1)
@pytest.mark.parametrize(
    "lib",
    [('str', 'class str', [1, 2]),
     ('numpy.testing', 'numpy.testing', [5, 10]),
     ('numpy.finfo', 'numpy.finfo', [1, 5])]
)
def test_get_pydoc(pydocbrowser, qtbot, lib):
    """
    Go to the documentation by url.
    Regression test for spyder-ide/spyder#10740
    """
    browser = pydocbrowser
    element, doc, matches = lib

    webview = browser.webview
    element_url = browser.text_to_url(element)
    with qtbot.waitSignal(webview.loadFinished):
        browser.set_url(element_url)

    expected_range = list(range(matches[0], matches[1]))
    qtbot.waitUntil(lambda: webview.get_number_matches(doc) in expected_range)


def test_html_getfile(qtbot):
    """
    Check that the source file link generated for a module's docs page
    can be loaded back without errors.

    Regression test for spyder-ide/spyder#26367
    """
    page = _url_handler("os.html")
    start = page.find('getfile?key=')
    end = page.find('"', start)
    getfile_href = page[start:end]

    result_page = _url_handler(getfile_href)
    assert '<title>Pydoc: Error' not in result_page
    assert 'File Listing' in result_page


if __name__ == "__main__":
    pytest.main()
