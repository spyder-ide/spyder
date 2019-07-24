# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for projectdialog.py
"""

# Standard library imports
import os
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Third party imports
import pytest

# Local imports
from spyder.plugins.projects.widgets.projectdialog import ProjectDialog


@pytest.fixture
def projects_dialog(qtbot):
    """Set up ProjectDialog."""
    dlg = ProjectDialog(None)
    qtbot.addWidget(dlg)
    return dlg

def test_project_dialog(projects_dialog):
    """Run project dialog."""
    projects_dialog.show()
    assert projects_dialog


@pytest.mark.skipif(os.name != 'nt', reason="Specific to Windows platform")
def test_projectdialog_location(monkeypatch):
    """Test that select_location normalizes delimiters and updates the path."""
    dlg = ProjectDialog(None)
    mock_getexistingdirectory = Mock()
    monkeypatch.setattr('spyder.plugins.projects.widgets.projectdialog' +
                        '.getexistingdirectory', mock_getexistingdirectory)

    mock_getexistingdirectory.return_value = r"c:\a/b\\c/d"
    dlg.select_location()
    assert dlg.location == r"c:\a\b\c\d"

    mock_getexistingdirectory.return_value = r"c:\\a//b\\c//d"
    dlg.select_location()
    assert dlg.location == r"c:\a\b\c\d"

    mock_getexistingdirectory.return_value = r"c:\a\b\c/d"
    dlg.select_location()
    assert dlg.location == r"c:\a\b\c\d"

    mock_getexistingdirectory.return_value = r"c:/a/b/c\d"
    dlg.select_location()
    assert dlg.location == r"c:\a\b\c\d"

    mock_getexistingdirectory.return_value = r"c:\\a\\b\\c//d"
    dlg.select_location()
    assert dlg.location == r"c:\a\b\c\d"

    mock_getexistingdirectory.return_value = r"c:\AaA/bBB1\\c-C/d2D"
    dlg.select_location()
    assert dlg.location == r"c:\AaA\bBB1\c-C\d2D"

    mock_getexistingdirectory.return_value = r"c:\\a_a_1//Bbbb\2345//d-6D"
    dlg.select_location()
    assert dlg.location == r"c:\a_a_1\Bbbb\2345\d-6D"


if __name__ == "__main__":
    pytest.main()
