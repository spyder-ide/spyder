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

# Third party imports
import pytest

# Local imports
from spyder.plugins.projects.widgets.projectdialog import ProjectDialog


@pytest.fixture
def projects_dialog(qtbot):
    """Set up ProjectDialog."""
    dlg = ProjectDialog(None)
    qtbot.addWidget(dlg)
    dlg.show()
    return dlg


@pytest.mark.skipif(os.name != 'nt', reason="Specific to Windows platform")
def test_projectdialog_location(projects_dialog):
    """Test that the dialog normalizes delimiters."""
    dlg = projects_dialog
    dlg.set_current_index(1)
    page = dlg.get_page()

    page._location.textbox.setText(r"c:\a/b\\c/d")
    assert page.project_location == r"c:\a\b\c\d"

    page._location.textbox.setText(r"c:\\a//b\\c//d")
    assert page.project_location == r"c:\a\b\c\d"

    page._location.textbox.setText(r"c:\a\b\c/d")
    assert page.project_location == r"c:\a\b\c\d"

    page._location.textbox.setText(r"c:/a/b/c\d")
    assert page.project_location == r"c:\a\b\c\d"

    page._location.textbox.setText(r"c:\\a\\b\\c//d")
    assert page.project_location == r"c:\a\b\c\d"

    page._location.textbox.setText(r"c:\AaA/bBB1\\c-C/d2D")
    assert page.project_location == r"c:\AaA\bBB1\c-C\d2D"

    page._location.textbox.setText(r"c:\\a_a_1//Bbbb\2345//d-6D")
    assert page.project_location == r"c:\a_a_1\Bbbb\2345\d-6D"


def test_directory_validations(projects_dialog, tmp_path, qtbot):
    """
    Test that we perform appropiate validations before allowing users to
    create a project in a directory.
    """
    dlg = projects_dialog

    # Check that we don't allow to create projects in existing directories when
    # 'New directory' is selected.
    (tmp_path / 'foo').mkdir()
    page = dlg.get_page()
    page._name.textbox.setText("foo")
    page._location.textbox.setText(str(tmp_path))
    dlg.button_create.animateClick()
    qtbot.wait(200)

    assert page._validation_label.isVisible()
    assert (
        page._validation_label.text()
        == "The directory you selected for this project already exists."
    )

    # Create another directoty and a Spyder project in it
    folder = tmp_path / 'bar'
    (folder / '.spyproject').mkdir(parents=True)

    # Check that we don't allow to create projects in existing directories when
    # 'Existing directory' is selected and there's already a Spyder project
    # there.
    dlg.set_current_index(1)
    page = dlg.get_page()
    page._location.textbox.setText(str(folder))
    dlg.button_create.animateClick()
    qtbot.wait(200)

    assert page._validation_label.isVisible()
    assert (
        page._validation_label.text()
        == "This directory is already a Spyder project."
    )


if __name__ == "__main__":
    pytest.main()
