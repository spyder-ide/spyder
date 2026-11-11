# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for qthelpers.py
"""

# Standard library imports
import os

# Third party imports
import pytest
from qtpy.QtCore import QUrl

# Local imports
from spyder.utils.qthelpers import file_uri


@pytest.mark.skipif(os.name != 'nt', reason="Only meaningful on Windows")
@pytest.mark.parametrize(
    "fname, host",
    [
        ("C:\\Users\\spyder\\file.txt", ""),
        ("\\\\server\\share\\dir\\file.txt", "server"),
    ]
)
def test_file_uri_windows(fname, host):
    """
    Check that file_uri gives valid URLs for local and UNC paths.

    This is a regression test for spyder-ide/spyder#26432
    """
    url = QUrl()
    url.setUrl(file_uri(fname))
    assert url.isValid()
    assert url.isLocalFile()
    assert url.host() == host
    assert os.path.normpath(url.toLocalFile()) == fname
