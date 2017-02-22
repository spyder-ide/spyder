# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for browser.py
"""

# Standard library imports
import sys

# Test library imports
import pytest

# Local imports
from spyder.widgets.browser import WebBrowser
from spyder.utils.qthelpers import qapplication

def test_browser():
    """Run web browser"""
    app = qapplication(test_time=8)
    widget = WebBrowser()
    widget.show()
    widget.set_home_url('http://www.google.com/')
    widget.go_home()
    sys.exit(app.exec_())

if __name__ == "__main__":
    pytest.main()
