# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2020- Spyder Project Contributors
#
# Released under the terms of the MIT License
# ----------------------------------------------------------------------------

"""Tests for the execution of pylint."""

# Standard library imports
from io import open
import os.path as osp

# Third party imports
import pytest

# Local imports
from spyder.plugins.pylint.widgets.pylintgui import PylintWidget
from spyder.plugins.pylint.utils import get_pylintrc_path

# pylint: disable=redefined-outer-name

PYLINTRC_FILENAME = ".pylintrc"

# Constants for dir name keys
# In Python 3 and Spyder 5, replace with enum
NO_DIR = "e"
SCRIPT_DIR = "SCRIPT_DIR"
WORKING_DIR = "WORKING_DIR"
PROJECT_DIR = "PROJECT_DIR"
HOME_DIR = "HOME_DIR"
ALL_DIR = "ALL_DIR"

DIR_LIST = [SCRIPT_DIR, WORKING_DIR, PROJECT_DIR, HOME_DIR]
DIR_LIST_ALL = [NO_DIR] + DIR_LIST + [ALL_DIR]

PYLINT_TEST_SCRIPT = "\n".join(
    [dir_name + " = " + str(idx) for idx, dir_name in enumerate(DIR_LIST_ALL)])
PYLINT_TEST_SCRIPT = "\"\"\"Docstring.\"\"\"\n" + PYLINT_TEST_SCRIPT + "\n"

PYLINTRC_TEST_CONTENTS = """
[MESSAGES CONTROL]
enable=blacklisted-name

[BASIC]
bad-names={bad_names}
good-names=e
"""


@pytest.fixture
def pylintrc_search_paths(tmp_path_factory):
    """Construct temporary .pylintrc search paths."""
    search_paths = {dir_name: str(tmp_path_factory.mktemp(dir_name))
                    for dir_name in DIR_LIST}
    return search_paths


@pytest.fixture
def pylint_test_script(pylintrc_search_paths):
    """Write a script for testing Pylint to a temporary directory."""
    script_path = osp.join(
        pylintrc_search_paths[SCRIPT_DIR], "test_script.py")
    with open(script_path, mode="w",
              encoding="utf-8", newline="\n") as script_file:
        script_file.write(PYLINT_TEST_SCRIPT)
    return script_path


@pytest.fixture(
    params=[
        [], [SCRIPT_DIR], [WORKING_DIR], [PROJECT_DIR], [HOME_DIR],
        [SCRIPT_DIR, HOME_DIR], [WORKING_DIR, PROJECT_DIR],
        [SCRIPT_DIR, PROJECT_DIR], [PROJECT_DIR, HOME_DIR],
        [SCRIPT_DIR, WORKING_DIR, PROJECT_DIR, HOME_DIR]],
    ids=["None", "Script", "Working", "Project", "Home", "Script & Home",
         "Working & Project", "Script & Working", "Project & Home", "All"])
def pylintrc_files(pylintrc_search_paths, request):
    """Store test .pylintrc files at the paths and determine the result."""
    search_paths = pylintrc_search_paths

    # Determine the bad names that should be reported
    pylintrc_locations = request.param
    bad_names = [ALL_DIR]
    for search_path_name, search_path in search_paths.items():
        if search_path_name in pylintrc_locations:
            expected_path = osp.join(search_path, PYLINTRC_FILENAME)
            bad_names += [search_path_name]
            break
    else:
        expected_path = None
        bad_names = [NO_DIR]

    # Store the selected pylintrc files at the designated paths
    for location in pylintrc_locations:
        pylintrc_test_contents = PYLINTRC_TEST_CONTENTS.format(
            bad_names=", ".join([location, ALL_DIR]))
        pylintrc_path = osp.join(search_paths[location], PYLINTRC_FILENAME)
        with open(pylintrc_path, mode="w",
                  encoding="utf-8", newline="\n") as rc_file:
            rc_file.write(pylintrc_test_contents)
    return search_paths, expected_path, bad_names


def test_get_pylintrc_path(pylintrc_files, mocker):
    """Test that get_pylintrc_path finds the expected one in the hiearchy."""
    search_paths, expected_path, __ = pylintrc_files
    mocker.patch("pylint.config.os.path.expanduser",
                 return_value=search_paths[HOME_DIR])
    actual_path = get_pylintrc_path(
        search_paths=list(search_paths.values()),
        home_path=search_paths[HOME_DIR],
        )
    assert actual_path == expected_path


def test_pylint_widget_noproject(pylint_test_script, qtbot):
    """Test that pylint works without errors with no project open."""
    pylint_widget = PylintWidget(parent=None)
    pylint_widget.analyze(filename=pylint_test_script)
    qtbot.waitUntil(
        lambda: pylint_widget.get_data(pylint_test_script)[1] is not None,
        timeout=5000)
    pylint_data = pylint_widget.get_data(filename=pylint_test_script)
    print(pylint_data)
    assert pylint_data
    assert pylint_data[0] is not None
    assert pylint_data[1] is not None


def test_pylint_widget_pylintrc(
        pylint_test_script, pylintrc_files, mocker, qtbot):
    """Test that entire pylint widget gets results depending on pylintrc."""
    search_paths, __, bad_names = pylintrc_files
    mocker.patch("pylint.config.os.path.expanduser",
                 return_value=search_paths[HOME_DIR])
    mocker.patch("spyder.plugins.pylint.widgets.pylintgui.getcwd_or_home",
                 return_value=search_paths[WORKING_DIR])
    mock_parent = mocker.Mock()
    mock_parent.main.projects.get_active_project_path = mocker.MagicMock(
        return_value=search_paths[PROJECT_DIR])
    mocker.patch(
        "spyder.plugins.pylint.widgets.pylintgui.PylintWidget.parentWidget",
        return_value=mock_parent)
    mocker.patch("spyder.plugins.pylint.widgets.pylintgui.osp.expanduser",
                 return_value=search_paths[HOME_DIR])

    pylint_widget = PylintWidget(parent=None)
    pylint_widget.analyze(filename=pylint_test_script)
    qtbot.waitUntil(
        lambda: pylint_widget.get_data(pylint_test_script)[1] is not None,
        timeout=5000)
    pylint_data = pylint_widget.get_data(filename=pylint_test_script)
    print(pylint_data)
    assert pylint_data
    conventions = pylint_data[1][3]["C:"]
    assert conventions
    assert len(conventions) == len(bad_names)
    assert all([sum([bad_name in message[2] for message in conventions]) == 1
                for bad_name in bad_names])


if __name__ == "__main__":
    pytest.main([osp.basename(__file__), '-vv', '-rw'])
