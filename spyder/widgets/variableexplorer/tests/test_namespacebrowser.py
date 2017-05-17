# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""
Tests for namespacebrowser.py
"""

# Standard library imports
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock # Python 2

# Third party imports
import pytest

# Local imports
from spyder.widgets.variableexplorer.namespacebrowser import NamespaceBrowser

def test_setup_sets_dataframe_format(qtbot):
    browser = NamespaceBrowser(None)
    browser.set_shellwidget(Mock())
    browser.setup(exclude_private=True, exclude_uppercase=True,
                  exclude_capitalized=True, exclude_unsupported=True,
                  minmax=False, dataframe_format='%10.5f')
    assert browser.editor.model.dataframe_format == '%10.5f'


if __name__ == "__main__":
    pytest.main()
