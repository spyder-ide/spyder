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
from unittest.mock import Mock

# Third party imports
import pytest

# Local imports
from spyder.plugins.projects.widgets.projectdialog import ProjectDialog
from spyder.plugins.projects.api import EmptyProject


@pytest.fixture
def projects_dialog(qtbot):
    """Set up ProjectDialog."""
    dlg = ProjectDialog(None, {'Empty project': EmptyProject})
    qtbot.addWidget(dlg)
    dlg.show()
    return dlg


@pytest.mark.skipif(os.name != 'nt', reason="Specific to Windows platform")
def test_projectdialog_location(monkeypatch):
    """Test that select_location normalizes delimiters and updates the path."""
    dlg = ProjectDialog(None, {'Empty project': EmptyProject})
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


def test_directory_validations(projects_dialog, monkeypatch, tmpdir):
    """
    Test that we perform appropiate validations before allowing users to
    create a project in a directory.
    """
    dlg = projects_dialog

    # Assert button_create is disabled by default
    assert not dlg.button_create.isEnabled()
    assert not dlg.button_create.isDefault()

    # Set location to tmpdir root
    dlg.location = str(tmpdir)
    dlg.text_location.setText(str(tmpdir))

    # Check that we don't allow to create projects in existing directories when
    # 'New directory' is selected.
    dlg.radio_new_dir.click()
    tmpdir.mkdir('foo')
    dlg.text_project_name.setText('foo')
    assert not dlg.button_create.isEnabled()
    assert not dlg.button_create.isDefault()
    assert dlg.label_information.text() == '\nThis directory already exists!'

    # Selecting 'Existing directory' should allow to create a project there
    dlg.radio_from_dir.click()
    assert dlg.button_create.isEnabled()
    assert dlg.button_create.isDefault()
    assert dlg.label_information.text() == ''

    # Create a Spyder project
    folder = tmpdir.mkdir('bar')
    folder.mkdir('.spyproject')

    # Mock selecting a directory
    mock_getexistingdirectory = Mock()
    monkeypatch.setattr('spyder.plugins.projects.widgets.projectdialog' +
                        '.getexistingdirectory', mock_getexistingdirectory)
    mock_getexistingdirectory.return_value = str(folder)

    # Check that we don't allow to create projects in existing directories when
    # 'Existing directory' is selected and there's already a Spyder project
    # there.
    dlg.select_location()
    assert not dlg.button_create.isEnabled()
    assert not dlg.button_create.isDefault()
    msg = '\nThis directory is already a Spyder project!'
    assert dlg.label_information.text() == msg


if __name__ == "__main__":
    pytest.main()
