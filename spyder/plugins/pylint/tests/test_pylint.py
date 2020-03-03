# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""Tests for the execution of pylint."""

# Standard library imports
from io import open
import os.path as osp

# Third party imports
import pytest

# Local imports
from spyder.plugins.pylint.widgets.pylintgui import get_pylintrc_path

# pylint: disable=redefined-outer-name

PYLINTRC_FILENAME = ".pylintrc"

# Constants for dir name keys
# TODO in Python 3 : Replace with enum
NO_DIR = "e"
SCRIPT_DIR = "script_dir"
WORKING_DIR = "working_dir"
PROJECT_DIR = "project_dir"
HOME_DIR = "home_dir"
ALL_DIR = "all_dir"

DIR_LIST = [SCRIPT_DIR, WORKING_DIR, PROJECT_DIR, HOME_DIR]
DIR_LIST_ALL = [NO_DIR] + DIR_LIST + [ALL_DIR]

PYLINT_TEST_SCRIPT = "\n".join(
    [dir_name + "=" + str(idx) for idx, dir_name in enumerate(DIR_LIST_ALL)])

PYLINTRC_TEST_CONTENTS = """
[MESSAGES CONTROL]
disable=all
enable=bad-names

[BASIC]
bad-names={bad_names}
"""


@pytest.fixture
def pylint_test_script(tmp_path_factory):
    """Write a script for testing Pylint to a temporary directory."""
    script_path = osp.join(
        str(tmp_path_factory.mktemp("script_dir")), "test_script.py")
    with open(script_path, mode="w",
              encoding="utf-8", newline="\n") as script_file:
        script_file.write(PYLINT_TEST_SCRIPT + "\n")
    return script_path


@pytest.fixture
def pylintrc_search_paths(tmp_path_factory):
    """Construct temporary .pylintrc search paths."""
    search_paths = {dir_name: str(tmp_path_factory.mktemp(dir_name))
                    for dir_name in DIR_LIST}
    return search_paths


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
            bad_names=bad_names)
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


if __name__ == "__main__":
    pytest.main([osp.basename(__file__), '-vv', '-rw'])
