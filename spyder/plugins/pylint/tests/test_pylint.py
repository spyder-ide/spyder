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
from unittest.mock import Mock, MagicMock

# Third party imports
from flaky import flaky
import pytest
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QApplication, QMainWindow

# This is necessary to run these tests independently from the rest in our
# test suite.
# NOTE: Don't move it to another place; it needs to be before importing the
# Pylint plugin below.
# Fixes spyder-ide/spyder#17071
if QApplication.instance() is None:
    app = QApplication([])

# Local imports
from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.config.base import running_in_ci
from spyder.config.manager import CONF
from spyder.config.utils import is_anaconda
from spyder.plugins.pylint.plugin import Pylint
from spyder.plugins.pylint.utils import get_pylintrc_path
from spyder.utils.conda import get_list_conda_envs
from spyder.utils.misc import get_python_executable

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

PYLINT_TEST_SCRIPT = "import math\nimport os\nimport sys\n" + "\n".join(
    [dir_name + " = " + str(idx) for idx, dir_name in enumerate(DIR_LIST_ALL)])
PYLINT_TEST_SCRIPT = "\"\"\"Docstring.\"\"\"\n" + PYLINT_TEST_SCRIPT + "\n"

PYLINTRC_TEST_CONTENTS = """
[MESSAGES CONTROL]
enable=blacklisted-name

[BASIC]
bad-names={bad_names}
good-names=e
"""

class MainWindowMock(QMainWindow):
    sig_editor_focus_changed = Signal(str)

    def __init__(self):
        super().__init__(None)
        self.editor = Mock()
        self.editor.sig_editor_focus_changed = self.sig_editor_focus_changed
        self.projects = MagicMock()

        PLUGIN_REGISTRY.plugin_registry = {
            'editor': self.editor,
            'projects': self.projects
        }

    def get_plugin(self, plugin_name, error=True):
        return PLUGIN_REGISTRY.get_plugin(plugin_name)


@pytest.fixture
def pylint_plugin(mocker, qtbot):
    main_window = MainWindowMock()
    qtbot.addWidget(main_window)
    main_window.resize(640, 480)
    main_window.projects.get_active_project_path = mocker.MagicMock(
        return_value=None)
    main_window.show()

    plugin = Pylint(parent=main_window, configuration=CONF)
    plugin._register()
    plugin.set_conf("history_filenames", [])

    # This avoids possible errors in our tests for not being available while
    # running them.
    plugin.set_conf('executable', get_python_executable(),
                    section='main_interpreter')

    widget = plugin.get_widget()
    widget.resize(640, 480)
    widget.filecombo.clear()
    widget.show()

    yield plugin

    widget.close()
    plugin.on_close()


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


@pytest.fixture
def pylint_test_scripts(pylintrc_search_paths):
    def _pylint_test_scripts(filenames):
        """Write scripts for testing Pylint to a temporary directory."""
        script_paths = []
        for filename in filenames:
            script_path = osp.join(
                pylintrc_search_paths[SCRIPT_DIR], filename)

            with open(script_path, mode="w",
                      encoding="utf-8", newline="\n") as script_file:
                script_file.write(PYLINT_TEST_SCRIPT)

            script_paths.append(script_path)

        return script_paths

    return _pylint_test_scripts


@pytest.fixture(
    params=[
        [],
        [SCRIPT_DIR],
        [WORKING_DIR],
        [PROJECT_DIR],
        [HOME_DIR],
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

    print(search_paths)
    print(expected_path)
    print(bad_names)

    return search_paths, expected_path, bad_names


def test_get_pylintrc_path(pylintrc_files, mocker):
    """Test that get_pylintrc_path finds the expected one in the hierarchy."""
    search_paths, expected_path, __ = pylintrc_files
    mocker.patch("os.path.expanduser",
                 return_value=search_paths[HOME_DIR])
    actual_path = get_pylintrc_path(
        search_paths=list(search_paths.values()),
        home_path=search_paths[HOME_DIR],
        )
    assert actual_path == expected_path


def test_pylint_widget_noproject(pylint_plugin, pylint_test_script, mocker,
                                 qtbot):
    """Test that pylint works without errors with no project open."""
    pylint_plugin.start_code_analysis(filename=pylint_test_script)
    pylint_widget = pylint_plugin.get_widget()

    qtbot.waitUntil(
        lambda: pylint_widget.get_data(pylint_test_script)[1] is not None,
        timeout=10000)
    pylint_data = pylint_widget.get_data(filename=pylint_test_script)

    print(pylint_data)

    assert pylint_data
    assert pylint_data[0] is not None
    assert pylint_data[1] is not None


@flaky(max_runs=3)
def test_pylint_widget_pylintrc(
        pylint_plugin, pylint_test_script, pylintrc_files, mocker, qtbot):
    """Test that entire pylint widget gets results depending on pylintrc."""
    search_paths, __, bad_names = pylintrc_files
    mocker.patch("os.path.expanduser",
                 return_value=search_paths[HOME_DIR])
    mocker.patch("spyder.plugins.pylint.main_widget.getcwd_or_home",
                 return_value=search_paths[WORKING_DIR])
    mocker.patch("spyder.plugins.pylint.main_widget.osp.expanduser",
                 return_value=search_paths[HOME_DIR])
    pylint_plugin.set_conf("project_dir", search_paths[PROJECT_DIR])

    pylint_widget = pylint_plugin.get_widget()
    pylint_plugin.start_code_analysis(filename=pylint_test_script)
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


def test_pylint_max_history_conf(pylint_plugin, pylint_test_scripts):
    """Regression test for checking max_entries configuration.

    For further information see spyder-ide/spyder#12884
    """
    pylint_widget = pylint_plugin.get_widget()
    script_0, script_1, script_2 = pylint_test_scripts(
        ["test_script_{}.py".format(n) for n in range(3)])

    # Change the max_entry to 2
    assert pylint_widget.filecombo.count() == 0
    pylint_plugin.change_history_depth(2)
    assert pylint_plugin.get_conf('max_entries') == 2
    assert pylint_widget.get_conf('max_entries') == 2

    # Call to set_filename
    pylint_widget.set_filename(filename=script_0)
    assert pylint_widget.filecombo.count() == 1

    # Add to more filenames
    pylint_widget.set_filename(filename=script_1)
    pylint_widget.set_filename(filename=script_2)

    assert pylint_widget.filecombo.count() == 2

    assert 'test_script_2.py' in pylint_widget.curr_filenames[0]
    assert 'test_script_1.py' in pylint_widget.curr_filenames[1]

    # Change the max entry to 1
    pylint_plugin.change_history_depth(1)

    assert pylint_widget.filecombo.count() == 1
    assert 'test_script_2.py' in pylint_widget.curr_filenames[0]


@flaky(max_runs=3)
@pytest.mark.parametrize("custom_interpreter", [True, False])
@pytest.mark.skipif(not is_anaconda(), reason='Only works with Anaconda')
@pytest.mark.skipif(not running_in_ci(), reason='Only works on CIs')
def test_custom_interpreter(pylint_plugin, tmp_path, qtbot,
                            custom_interpreter):
    """Test that the plugin works as expected with custom interpreters."""
    # Get conda env to use
    conda_env = get_list_conda_envs()['conda: jedi-test-env'][0]

    # Set custom interpreter
    if custom_interpreter:
        pylint_plugin.set_conf('default', False, section='main_interpreter')
        pylint_plugin.set_conf('executable', conda_env,
                               section='main_interpreter')
    else:
        pylint_plugin.set_conf('default', True, section='main_interpreter')
        pylint_plugin.set_conf('executable', get_python_executable(),
                               section='main_interpreter')

    # Write test code to file
    file_path = tmp_path / 'test_custom_interpreter.py'
    file_path.write_text('import flask')

    # Run analysis and get its data
    pylint_widget = pylint_plugin.get_widget()
    pylint_plugin.start_code_analysis(filename=str(file_path))
    qtbot.waitUntil(
        lambda: pylint_widget.get_data(file_path)[1] is not None,
        timeout=5000)
    pylint_data = pylint_widget.get_data(filename=str(file_path))

    # Assert no import errors are reported for custom interpreters
    errors = pylint_data[1][3]["E:"]
    if custom_interpreter:
        assert not errors
    else:
        assert errors


if __name__ == "__main__":
    pytest.main([osp.basename(__file__), '-vv', '-rw'])
