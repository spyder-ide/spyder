# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2020- Spyder Project Contributors
#
# Released under the terms of the MIT License
# ----------------------------------------------------------------------------

"""Tests for the execution of pylint."""

import os.path as osp
# Standard library imports
from io import open
import os.path as osp
from unittest.mock import Mock, MagicMock

# Third party imports
import pytest
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMainWindow

# Local imports
from spyder.config.manager import CONF
from spyder.plugins.editor.plugin import Editor
from spyder.plugins.pylint.plugin import Pylint
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
    register_shortcut = Mock()
    file_menu_actions = []
    file_toolbar_actions = []
    edit_menu_actions = []
    edit_toolbar_actions = []
    run_menu_actions = []
    run_toolbar_actions = []
    debug_menu_actions = []
    debug_toolbar_actions = []
    source_menu_actions = []
    source_toolbar_actions = []
    all_actions_defined = Mock()
    sig_pythonpath_changed = Mock()
    plugin_focus_changed = Mock()
    file_menu = Mock()
    edit_menu = Mock()
    search_menu = Mock()
    source_menu = Mock()
    run_menu = Mock()
    debug_menu = Mock()
    consoles_menu = Mock()
    projects_menu = Mock()
    tools_menu = Mock()
    view_menu = Mock()
    help_menu = Mock()
    consoles_menu_actions = Mock()
    projects_menu_actions = Mock()
    tools_menu_actions = Mock()
    view_menu_actions = Mock()
    help_menu_actions = Mock()
    ipyconsole = MagicMock()
    get_spyder_pythonpath = Mock()
    completions = Mock()

    _PLUGINS = {}

    def __init__(self):
        super(MainWindowMock, self).__init__(None)
        self.editor = Mock()
        self.editor.sig_editor_focus_changed = self.sig_editor_focus_changed
        self.projects = MagicMock()
        self.project_explorer = Mock()

        self._PLUGINS['editor'] = self.editor
        self._PLUGINS['projects'] = self.projects
        self._PLUGINS['project_explorer'] = self.project_explorer


@pytest.fixture
def pylint_plugin(mocker, qtbot):
    main_window = MainWindowMock()
    main_window.projects.get_active_project_path = mocker.MagicMock(
        return_value=None)
    plugin = Pylint(parent=main_window, configuration=CONF)
    plugin._register()
    plugin.set_conf_option("history_filenames", [])
    widget = plugin.get_widget()
    widget.filecombo.clear()
    qtbot.addWidget(widget)
    yield plugin


@pytest.fixture
def pylint_plugin_with_real_editor(qtbot):
    main_window = MainWindowMock()
    main_window.editor = Editor(main_window)
    plugin = Pylint(parent=main_window, configuration=CONF)
    plugin.register()
    widget = plugin.get_widget()
    qtbot.addWidget(widget)
    yield plugin


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


class IgnoreRulesTestHelper(object):
    bad_function_name = "C0103"

    def __init__(self, file_path):
        self.python_file_path = file_path

    def add_function_with_bad_name(self):
        with open(self.python_file_path, mode="a", encoding="utf-8",
                  newline="\n") as file:
            file.write("def a():\n    pass\n")

    def ignore_first_item_that_matches_with(self, rule_to_find, pylint_widget):
        item = \
            [item for item in pylint_widget.get_focus_widget().get_items() if
             rule_to_find in item.text(0)][0]
        pylint_widget.get_focus_widget().ignore_lint_rule(item)
        return rule_to_find

    def assert_that_rule_is_being_ignored(self, ignored_rule, pylint_widget):
        assert ignored_rule not in \
               [item.text(0) for item in
                pylint_widget.get_focus_widget().get_items()]


@pytest.fixture
def ignore_rules_test_helper(pylintrc_search_paths):
    script_path = osp.join(pylintrc_search_paths[SCRIPT_DIR], "test_script.py")
    return IgnoreRulesTestHelper(script_path)


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
    """Test that get_pylintrc_path finds the expected one in the hiearchy."""
    search_paths, expected_path, __ = pylintrc_files
    mocker.patch("pylint.config.os.path.expanduser",
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
        timeout=5000)
    pylint_data = pylint_widget.get_data(filename=pylint_test_script)

    print(pylint_data)

    assert pylint_data
    assert pylint_data[0] is not None
    assert pylint_data[1] is not None


def test_pylint_widget_pylintrc(
        pylint_plugin, pylint_test_script, pylintrc_files, mocker, qtbot):
    """Test that entire pylint widget gets results depending on pylintrc."""
    search_paths, __, bad_names = pylintrc_files
    mocker.patch("pylint.config.os.path.expanduser",
                 return_value=search_paths[HOME_DIR])
    mocker.patch("spyder.plugins.pylint.main_widget.getcwd_or_home",
                 return_value=search_paths[WORKING_DIR])
    mocker.patch("spyder.plugins.pylint.main_widget.osp.expanduser",
                 return_value=search_paths[HOME_DIR])
    pylint_plugin.set_conf_option("project_dir", search_paths[PROJECT_DIR])

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
    assert pylint_plugin.get_conf_option('max_entries') == 2
    assert pylint_widget.get_option('max_entries') == 2

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


def test_pylint_ignore_issue_in_a_function_definition(
        ignore_rules_test_helper, qtbot, pylint_plugin_with_real_editor):
    ignore_rules_test_helper.add_function_with_bad_name()
    pylint_widget = pylint_plugin_with_real_editor.get_widget()
    pylint_widget.set_filename(ignore_rules_test_helper.python_file_path)

    pylint_plugin_with_real_editor.start_code_analysis(
        filename=ignore_rules_test_helper.python_file_path)
    wait_until_code_analysis_finish(pylint_widget, qtbot)

    ignored_rule = ignore_rules_test_helper.\
        ignore_first_item_that_matches_with(
            ignore_rules_test_helper.bad_function_name, pylint_widget
        )

    wait_until_code_analysis_finish(pylint_widget, qtbot)

    with open(ignore_rules_test_helper.python_file_path, mode="r") as file:
        print(file.read(100))

    ignore_rules_test_helper. \
        assert_that_rule_is_being_ignored(ignored_rule, pylint_widget)


def wait_until_code_analysis_finish(widget, qtbot):
    qtbot.waitUntil(
        lambda: not widget._is_running(),
        timeout=5000)


if __name__ == "__main__":
    pytest.main([osp.basename(__file__), '-vv', '-rw'])
