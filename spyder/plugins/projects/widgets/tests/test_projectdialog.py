# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for projectdialog.py
"""

# Standard library imports
from contextlib import contextmanager
import os
import subprocess

# Third party imports
import pytest

# Local imports
from spyder.config.base import running_in_ci
from spyder.plugins.projects.widgets.projectdialog import (
    is_writable,
    ProjectDialog,
)


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


def test_directory_is_writable(tmp_path):
    """Test if we can correctly detect of a directory is writable."""
    read_only_dir = tmp_path / "read_only_dir"
    read_only_dir.mkdir()

    # Make the directory read-only.
    if os.name == "nt":
        # From https://stackoverflow.com/a/66130551
        @contextmanager
        def set_access_right(path, access):
            def cmd(access_right):
                return [
                    "icacls",
                    str(path),
                    "/inheritance:r",
                    "/grant:r",
                    f"Everyone:{access_right}",
                ]

            try:
                subprocess.check_output(cmd(access))
                yield path
            finally:
                subprocess.check_output(cmd("F")) # F -> full access again

        # This doesn't work on CIs but passes locally
        if not running_in_ci():
            with set_access_right(read_only_dir, "R") as path: # R -> Read-only
                assert not is_writable(str(path))

        # Also check that is_writable can deal with UNC paths.
        assert not is_writable("\\Users")
    else:
        # From https://stackoverflow.com/a/70933772
        read_only_dir.chmod(0o444)
        assert not is_writable(str(read_only_dir))

        # Make it read-write again to delete it
        read_only_dir.chmod(0o644)



def _make_interpreter(folder):
    """Create a fake .venv interpreter in folder."""
    bin_dir = folder / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    bin_dir.mkdir(parents=True)
    interpreter = bin_dir / ("python.exe" if os.name == "nt" else "python")
    interpreter.touch()
    return str(interpreter)


def test_interpreter_is_detected_in_existing_directory(
    projects_dialog, tmp_path
):
    """The interpreter field is filled when the directory has an env."""
    dlg = projects_dialog
    dlg.set_current_index(1)
    page = dlg.get_page()

    interpreter = _make_interpreter(tmp_path)
    page._location.textbox.setText(str(tmp_path))
    assert page.interpreter == os.path.normpath(interpreter)

    # It's cleared again if the user selects a directory without one
    other = tmp_path / "other"
    other.mkdir()
    page._location.textbox.setText(str(other))
    assert page.interpreter == ""


def test_detected_interpreter_keeps_user_choice(projects_dialog, tmp_path):
    """A user-selected interpreter is never replaced by a detected one."""
    dlg = projects_dialog
    dlg.set_current_index(1)
    page = dlg.get_page()

    chosen = tmp_path / "my_python"
    chosen.touch()
    page._interpreter.textbox.setText(str(chosen))

    _make_interpreter(tmp_path)
    page._location.textbox.setText(str(tmp_path))
    assert page.interpreter == os.path.normpath(str(chosen))


def test_interpreter_is_validated(projects_dialog, tmp_path, qtbot):
    """The interpreter is optional, but it must exist when it's set."""
    dlg = projects_dialog
    dlg.set_current_index(1)
    page = dlg.get_page()
    page._location.textbox.setText(str(tmp_path))

    # Empty is fine
    assert page.validate_page()

    # A file that doesn't exist is not
    page._interpreter.textbox.setText(str(tmp_path / "missing" / "python"))
    assert not page.validate_page()
    assert page._validation_label.text() == (
        "The Python interpreter you selected doesn't exist."
    )

    # An existing file is
    existing = tmp_path / "python"
    existing.touch()
    page._interpreter.textbox.setText(str(existing))
    assert page.validate_page()


def test_interpreter_is_part_of_project_data(projects_dialog, tmp_path):
    """The selected interpreter is passed on to create the project."""
    dlg = projects_dialog
    dlg.set_current_index(1)
    page = dlg.get_page()

    interpreter = _make_interpreter(tmp_path)
    page._location.textbox.setText(str(tmp_path))
    dlg.create_project()

    assert dlg.project_data["interpreter"] == os.path.normpath(interpreter)

    
if __name__ == "__main__":
    pytest.main()
