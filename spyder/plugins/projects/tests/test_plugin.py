# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for the Projects plugin.
"""

# Standard library imports
import configparser
import os
import os.path as osp
import shutil
import sys
from unittest.mock import MagicMock

# Third party imports
import pytest
from flaky import flaky

# Local imports
from spyder.app.cli_options import get_options
from spyder.config.manager import CONF
from spyder.plugins.preferences.tests.conftest import MainWindowMock
from spyder.plugins.projects.api import BaseProjectType
from spyder.plugins.projects.plugin import Projects
from spyder.plugins.projects.widgets.main_widget import QMessageBox
from spyder.plugins.projects.widgets.projectdialog import ProjectDialog


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def projects(qtbot, mocker, request, tmpdir):
    """Projects plugin fixture."""
    use_cli_project = request.node.get_closest_marker('use_cli_project')

    class EditorMock(MagicMock):
        def get_open_filenames(self):
            # Patch this with mocker to return a different value.
            # See test_set_project_filenames_in_close_project.
            return []

    class MainWindowProjectsMock(MainWindowMock):
        def __init__(self, parent):
            # This avoids using the cli options passed to pytest
            sys_argv = [sys.argv[0]]
            self._cli_options = get_options(sys_argv)[0]
            super().__init__(parent)

        def __getattr__(self, attr):
            if attr == 'ipyconsole':
                return None
            try:
                super().__getattr__(attr)
            except AttributeError:
                return MagicMock()

        def get_initial_working_directory(self):
            return str(tmpdir)

        def get_plugin(self, plugin_name, error=True):
            if plugin_name == 'editor':
                return EditorMock()
            else:
                return None

    # Main window mock
    main_window = MainWindowProjectsMock(None)
    if use_cli_project:
        tmpdir.mkdir('cli_project_dir')

        # This allows us to test relative paths passed on the command line
        main_window._cli_options.project = 'cli_project_dir'

    # Create plugin
    projects = Projects(parent=None, configuration=CONF)
    projects.initialize()

    projects.sig_switch_to_plugin_requested.connect(
        lambda x, y: projects.change_visibility(True))

    # This can only be done at this point
    projects._main = main_window

    yield projects

    projects.get_container().close()
    projects.on_close()


@pytest.fixture
def create_projects(projects, mocker):
    """Create a Projects plugin fixture"""
    def _create_projects(path, files):
        """
        Using the Projects plugin fixture, open a project at the
        specified path, and mock the opening of the specified files
        in the Editor.
        """
        # Open a project.
        projects.open_project(path=path)

        # Mock the opening of files in the Editor while the project is open.
        projects._get_open_filenames = lambda *args, **kwargs: files
        return projects

    return _create_projects


# =============================================================================
# ---- Tests
# =============================================================================
@pytest.mark.parametrize("test_directory", [u'測試', u'اختبار', u"test_dir"])
def test_open_project(projects, tmpdir, test_directory):
    """Test that we can create a project in a given directory."""
    # Create the directory
    path = str(tmpdir.mkdir(test_directory))

    # Open project in path
    projects.open_project(path=path)

    # Verify that we created a valid project
    assert projects.is_valid_project(path)

    # Close project
    projects.close_project()


@pytest.mark.parametrize("test_directory", [u'測試', u'اختبار', u"test_dir"])
def test_delete_project(projects, tmpdir, mocker, test_directory):
    """Test that we can delete a project."""
    # Create the directory
    path = str(tmpdir.mkdir(test_directory))

    # Open project in path
    projects.open_project(path=path)
    assert projects.is_valid_project(path)
    assert osp.exists(osp.join(path, '.spyproject'))

    # Delete project
    mocker.patch.object(QMessageBox, 'warning', return_value=QMessageBox.Yes)
    projects.delete_project()
    assert not projects.is_valid_project(path)
    assert not osp.exists(osp.join(path, '.spyproject'))


@pytest.mark.parametrize('value', [True, False])
def test_close_project_sets_visible_config(projects, tmpdir, value):
    """Test that when project is closed, the config option
    visible_if_project_open is set to the correct value."""
    # Set config to opposite value so that we can check that it's set correctly
    projects.set_conf('visible_if_project_open', not value)
    projects.open_project(path=str(tmpdir))
    if value:
        projects._show_main_widget()
    else:
        projects.get_widget().hide()
    projects.close_project()
    assert projects.get_conf('visible_if_project_open') == value


@pytest.mark.parametrize('value', [True, False])
def test_on_close_sets_visible_config(projects, tmpdir, value):
    """Test that on_close() sets config option visible_if_project_open
    if a project is open."""
    projects.set_conf('visible_if_project_open', not value)
    projects.on_close()

    # No project is open so config option should remain unchanged
    assert projects.get_conf('visible_if_project_open') == (not value)

    projects.open_project(path=str(tmpdir))
    if value:
        projects._show_main_widget()
    else:
        projects.get_widget().hide()
    projects.close_project()
    assert projects.get_conf('visible_if_project_open') == value


@pytest.mark.parametrize('value', [True, False])
def test_open_project_uses_visible_config(projects, tmpdir, value):
    """Test that when a project is opened, the project explorer is only opened
    if the config option visible_if_project_open is set."""
    projects.set_conf('visible_if_project_open', value)
    projects.open_project(path=str(tmpdir))
    assert projects.get_widget().isVisible() == value


@pytest.mark.parametrize('value', [False, True])
def test_switch_to_plugin(projects, tmpdir, value):
    """Test that switch_to_plugin always shows the plugin if a project is
    opened, regardless of the config option visible_if_project_open.
    Regression test for spyder-ide/spyder#12491."""
    projects.set_conf('visible_if_project_open', value)
    projects.open_project(path=str(tmpdir))
    projects.switch_to_plugin()
    assert projects.get_widget().isVisible()


def test_set_get_project_filenames_when_closing_no_files(create_projects,
                                                         tmpdir):
    """
    Test that the currently opened files in the Editor are saved and loaded
    correctly to and from the project config when the project is closed and
    then reopened.

    Regression test for spyder-ide/spyder#10045.
    """
    path = str(tmpdir.mkdir('project1'))
    # Create paths but no actual files
    opened_files = [os.path.join(path, file)
                    for file in ['file1', 'file2', 'file3']]

    # Create the projects plugin without creating files.
    projects = create_projects(path, opened_files)
    assert projects.get_project_filenames() == []

    # Close and reopen the project.
    projects.close_project()
    projects.open_project(path=path)

    # Check the original list isn't empty (was not changed)
    assert opened_files


def test_set_get_project_filenames_when_closing(create_projects, tmpdir):
    """
    Test that the currently opened files in the Editor are saved and loaded
    correctly to and from the project config when the project is closed and
    then reopened.

    Regression test for spyder-ide/spyder#8375.
    Updated for spyder-ide/spyder#10045.
    """
    # Setup tmp dir and files
    dir_object = tmpdir.mkdir('project1')
    path = str(dir_object)

    # Needed to actually create the files
    opened_files = []
    for file in ['file1', 'file2', 'file3']:
        file_object = dir_object.join(file)
        file_object.write(file)
        opened_files.append(str(file_object))

    # Create the projects plugin.
    projects = create_projects(path, opened_files)
    assert projects.get_project_filenames() == []

    # Close and reopen the project.
    projects.close_project()
    projects.open_project(path=path)
    assert projects.get_project_filenames() == opened_files


def test_set_get_project_filenames_when_switching(create_projects, tmpdir):
    """
    Test that files in the Editor are loaded and saved correctly when
    switching projects.

    Updated for spyder-ide/spyder#10045.
    """
    dir_object1 = tmpdir.mkdir('project1')
    path1 = str(dir_object1)
    path2 = str(tmpdir.mkdir('project2'))

    # Needed to actually create the files
    opened_files = []
    for file in ['file1', 'file2', 'file3']:
        file_object = dir_object1.join(file)
        file_object.write(file)
        opened_files.append(str(file_object))

    # Create the projects plugin.
    projects = create_projects(path1, opened_files)
    assert projects.get_project_filenames() == []

    # Switch to another project.
    projects.open_project(path=path2)
    assert projects.get_project_filenames() == []

    # Switch back to the first project.
    projects.close_project()
    projects.open_project(path=path1)
    assert projects.get_project_filenames() == opened_files


def test_recent_projects_menu_action(projects, tmpdir):
    """
    Test that the actions of the submenu 'Recent Projects' in the 'Projects'
    main menu are working as expected.

    Regression test for spyder-ide/spyder#8450.
    """
    # Create the directories.
    path0 = str(tmpdir.mkdir('project0'))
    path1 = str(tmpdir.mkdir('project1'))
    path2 = str(tmpdir.mkdir('project2'))

    # Open projects in path0, path1, and path2.
    projects.open_project(path=path0)
    projects.open_project(path=path1)
    projects.open_project(path=path2)
    actions = list(projects.get_widget().get_actions().keys())
    assert path0 in actions
    assert path1 in actions
    assert path2 in actions
    assert projects.get_active_project().root_path == path2

    # Trigger project1 in the list of Recent Projects actions.
    projects.get_widget().get_actions()[path1].trigger()
    assert projects.get_active_project().root_path == path1

    # Trigger project0 in the list of Recent Projects actions.
    projects.get_widget().get_actions()[path0].trigger()
    assert projects.get_active_project().root_path == path0


def test_project_explorer_tree_root(projects, tmpdir, qtbot):
    """
    Test that the root item of the project explorer tree widget is set
    correctly when switching projects.

    Regression test for spyder-ide/spyder#8455.
    """
    qtbot.addWidget(projects.get_widget())
    projects._show_main_widget()

    ppath1 = str(tmpdir.mkdir(u'測試'))
    ppath2 = str(tmpdir.mkdir(u'ïèô éàñ').mkdir(u'اختبار'))
    if os.name == 'nt':
        # For an explanation of why this part is necessary to make this test
        # pass for Python2 in Windows, see spyder-ide/spyder#8528.
        import win32file
        ppath1 = win32file.GetLongPathName(ppath1)
        ppath2 = win32file.GetLongPathName(ppath2)

    # Open the projects.
    for ppath in [ppath1, ppath2]:
        projects.open_project(path=ppath)
        projects.get_widget()._setup_project(ppath)

        # Check that the root path of the project explorer tree widget is
        # set correctly.
        assert projects.get_active_project_path() == ppath
        assert projects.get_widget().treewidget.root_path == osp.dirname(ppath)
        assert (projects.get_widget().treewidget.rootIndex().data() ==
                osp.basename(osp.dirname(ppath)))

        # Check that the first visible item in the project explorer
        # tree widget is the folder of the project.
        topleft_index = (projects.get_widget().treewidget.indexAt(
            projects.get_widget().treewidget.rect().topLeft()))
        assert topleft_index.data() == osp.basename(ppath)


@flaky(max_runs=5)
def test_filesystem_notifications(qtbot, projects, tmpdir):
    """
    Test that filesystem notifications are emitted when creating,
    deleting and moving files and directories.
    """
    # Create a directory for the project and some files.
    project_root = tmpdir.mkdir('project0')
    git_folder = project_root.mkdir('.git')
    folder0 = project_root.mkdir('folder0')
    folder1 = project_root.mkdir('folder1')
    file0 = project_root.join('file0.txt')
    file1 = folder0.join('file1.txt')
    file2 = folder0.join('file2.txt')
    file3 = folder1.join('file3.txt')
    file0.write('')
    file1.write('')
    file3.write('ab')

    # Open the project
    projects.open_project(path=str(project_root))

    # Get a reference to the filesystem event handler
    fs_handler = projects.get_widget().watcher.event_handler

    # Test file creation
    with qtbot.waitSignal(fs_handler.sig_file_created,
                          timeout=30000) as blocker:
        file2.write('')

    file_created, is_dir = blocker.args
    assert file_created == str(file2)
    assert not is_dir

    # Test folder creation
    with qtbot.waitSignal(fs_handler.sig_file_created,
                          timeout=3000) as blocker:
        folder2 = project_root.mkdir('folder2')

    folder_created, is_dir = blocker.args
    assert folder_created == osp.join(str(project_root), 'folder2')

    # Test file move/renaming
    new_file = osp.join(str(folder0), 'new_file.txt')
    with qtbot.waitSignal(fs_handler.sig_file_moved,
                          timeout=3000) as blocker:
        shutil.move(str(file1), new_file)

    original_file, file_moved, is_dir = blocker.args
    assert original_file == str(file1)
    assert file_moved == new_file
    assert not is_dir

    # Test folder move/renaming
    new_folder = osp.join(str(project_root), 'new_folder')
    with qtbot.waitSignal(fs_handler.sig_file_moved,
                          timeout=3000) as blocker:
        shutil.move(str(folder2), new_folder)

    original_folder, folder_moved, is_dir = blocker.args
    assert original_folder == str(folder2)
    assert folder_moved == new_folder
    assert is_dir

    # Test file deletion
    with qtbot.waitSignal(fs_handler.sig_file_deleted,
                          timeout=3000) as blocker:
        os.remove(str(file0))

    deleted_file, is_dir = blocker.args
    assert deleted_file == str(file0)
    assert not is_dir
    assert not osp.exists(str(file0))

    # Test folder deletion
    with qtbot.waitSignal(fs_handler.sig_file_deleted,
                          timeout=3000) as blocker:
        shutil.rmtree(str(folder0))

    deleted_folder, is_dir = blocker.args
    assert str(folder0) in deleted_folder

    # Test file/folder modification
    with qtbot.waitSignal(fs_handler.sig_file_modified,
                          timeout=3000) as blocker:
        file3.write('abc')

    modified_file, is_dir = blocker.args
    assert modified_file in str(file3)

    # Test events in hidden folders are not emitted
    with qtbot.assertNotEmitted(fs_handler.sig_file_created, wait=2000):
        git_file = git_folder.join('git_file.txt')
        git_file.write("Some data")

    # Test events in pycache folders are not emitted
    with qtbot.assertNotEmitted(fs_handler.sig_file_created, wait=2000):
        pycache_folder = project_root.mkdir('__pycache__')
        pycache_file = pycache_folder.join("foo.pyc")
        pycache_file.write("")

    # Test events for files with binary extensions are not emitted
    with qtbot.assertNotEmitted(fs_handler.sig_file_created, wait=2000):
        png_file = project_root.join("binary.png")
        png_file.write("")


def test_loaded_and_closed_signals(create_projects, tmpdir, mocker, qtbot):
    """
    Test that loaded and closed signals are emitted when switching
    projects.
    """
    dir_object1 = tmpdir.mkdir('project1')
    path1 = str(dir_object1)
    path2 = str(tmpdir.mkdir('project2'))

    mocker.patch.object(ProjectDialog, "exec_", return_value=True)

    # Needed to actually create the files
    opened_files = []
    for file in ['file1', 'file2', 'file3']:
        file_object = dir_object1.join(file)
        file_object.write(file)
        opened_files.append(str(file_object))

    # Create the projects plugin.
    projects = create_projects(path1, opened_files)
    projects._project_types = {}
    # Switch to another project.
    with qtbot.waitSignals(
        [projects.sig_project_loaded, projects.sig_project_closed]
    ):
        projects.open_project(path=path2)


@pytest.mark.use_cli_project
def test_project_cli(projects):
    """Test that we can open a project from the command line."""
    # Simulate opening a project when the main window is visible
    projects.on_mainwindow_visible()

    # Verify that we created the expected project
    active_project = projects.get_active_project_path()
    assert osp.split(active_project)[-1] == 'cli_project_dir'

    # Close project
    projects.close_project()


def test_reopen_project(projects, tmpdir):
    """Test that we can reopen a project from the last session."""
    # Create project
    last_project = tmpdir.mkdir('last_project_dir')
    last_project.mkdir('.spyproject')
    projects.set_conf('current_project_path', str(last_project))

    # Simulate opening a project when the main window is visible
    projects.on_mainwindow_visible()

    # Verify that we created the expected project
    active_project = projects.get_active_project_path()
    assert osp.split(active_project)[-1] == 'last_project_dir'

    # Close project
    projects.close_project()


def test_recreate_project_config(projects, tmpdir):
    """
    Test that the project's config files are recreated when there are errors
    reading them.

    Regression test for spyder-ide/spyder#17907.
    """
    # Create a new directory
    path = str(tmpdir.mkdir('error_reading_config'))

    # Open project in path to generate its config
    projects.open_project(path=path)

    # Get project's config path
    config_path = projects.get_widget().current_active_project.config._path

    # Close project
    projects.close_project()

    # Append the contents of a config file to it in order to give an error
    # while reading it
    config_file = osp.join(config_path, 'workspace.ini')

    with open(config_file, 'r') as f:
        file_contents = f.readlines()

    with open(config_file, 'a') as f:
        for line in file_contents:
            f.write(line)

    # Try to read config and check we get an error
    with pytest.raises(configparser.Error):
        BaseProjectType.create_config(config_path)

    # Reopen the project again and check we recreated the config file we
    # changed
    projects.open_project(path=path)
    projects.close_project()

    with open(config_file, 'r') as f:
        new_file_contents = f.readlines()

    assert file_contents == new_file_contents


if __name__ == "__main__":
    pytest.main()
