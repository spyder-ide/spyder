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
import os
import shutil
import os.path as osp
import sys
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Third party imports
import pytest
from flaky import flaky

# Local imports
import spyder.plugins.base
from spyder.plugins.projects.plugin import Projects, QMessageBox
from spyder.py3compat import to_text_string


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def projects(qtbot, mocker):
    """Projects plugin fixture."""

    class EditorMock(object):
        def get_open_filenames(self):
            # Patch this with mocker to return a different value.
            # See test_set_project_filenames_in_close_project.
            return []

        def __getattr__(self, attr):
            return Mock()

    class MainWindowMock(object):
        editor = EditorMock()

        def __getattr__(self, attr):
            if attr == 'ipyconsole':
                return None
            else:
                return Mock()

    # Create plugin
    projects = Projects(parent=None)
    projects._setup()

    # Patching necessary to test visible_if_project_open
    projects.shortcut = None
    mocker.patch.object(spyder.plugins.base.SpyderDockWidget,
                        'install_tab_event_filter')
    mocker.patch.object(projects, '_toggle_view_action')
    projects._create_dockwidget()

    # This can only be done at this point
    projects.main = MainWindowMock()

    qtbot.addWidget(projects)
    projects.show()
    return projects


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
        mocker.patch.object(
            projects.main.editor, 'get_open_filenames', return_value=files)

        return projects
    return _create_projects


# =============================================================================
# ---- Tests
# =============================================================================
@pytest.mark.parametrize("test_directory", [u'測試', u'اختبار', u"test_dir"])
def test_open_project(projects, tmpdir, test_directory):
    """Test that we can create a project in a given directory."""
    # Create the directory
    path = to_text_string(tmpdir.mkdir(test_directory))

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
    path = to_text_string(tmpdir.mkdir(test_directory))

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
    projects.set_option('visible_if_project_open', not value)

    projects.open_project(path=to_text_string(tmpdir))
    if value:
        projects.show_explorer()
    else:
        projects.dockwidget.close()
    projects.close_project()
    assert projects.get_option('visible_if_project_open') == value


@pytest.mark.parametrize('value', [True, False])
def test_closing_plugin_sets_visible_config(projects, tmpdir, value):
    """Test that closing_plugin() sets config option visible_if_project_open
    if a project is open."""
    projects.set_option('visible_if_project_open', not value)
    projects.closing_plugin()

    # No project is open so config option should remain unchanged
    assert projects.get_option('visible_if_project_open') == (not value)

    projects.open_project(path=to_text_string(tmpdir))
    if value:
        projects.show_explorer()
    else:
        projects.dockwidget.close()
    projects.close_project()
    assert projects.get_option('visible_if_project_open') == value


@pytest.mark.parametrize('value', [True, False])
def test_open_project_uses_visible_config(projects, tmpdir, value):
    """Test that when a project is opened, the project explorer is only opened
    if the config option visible_if_project_open is set."""
    projects.set_option('visible_if_project_open', value)
    projects.open_project(path=to_text_string(tmpdir))
    assert projects.dockwidget.isVisible() == value


def test_set_get_project_filenames_when_closing_no_files(create_projects,
                                                         tmpdir):
    """
    Test that the currently opened files in the Editor are saved and loaded
    correctly to and from the project config when the project is closed and
    then reopened.

    Regression test for spyder-ide/spyder#10045.
    """
    path = to_text_string(tmpdir.mkdir('project1'))
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
    path = to_text_string(dir_object)

    # Needed to actually create the files
    opened_files = []
    for file in ['file1', 'file2', 'file3']:
        file_object = dir_object.join(file)
        file_object.write(file)
        opened_files.append(to_text_string(file_object))

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
    path1 = to_text_string(dir_object1)
    path2 = to_text_string(tmpdir.mkdir('project2'))

    # Needed to actually create the files
    opened_files = []
    for file in ['file1', 'file2', 'file3']:
        file_object = dir_object1.join(file)
        file_object.write(file)
        opened_files.append(to_text_string(file_object))

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
    recent_projects_len = len(projects.recent_projects)

    # Create the directories.
    path0 = to_text_string(tmpdir.mkdir('project0'))
    path1 = to_text_string(tmpdir.mkdir('project1'))
    path2 = to_text_string(tmpdir.mkdir('project2'))

    # Open projects in path0, path1, and path2.
    projects.open_project(path=path0)
    projects.open_project(path=path1)
    projects.open_project(path=path2)
    assert (len(projects.recent_projects_actions) ==
            recent_projects_len + 3 + 2)
    assert projects.get_active_project().root_path == path2

    # Trigger project1 in the list of Recent Projects actions.
    projects.recent_projects_actions[1].trigger()
    assert projects.get_active_project().root_path == path1

    # Trigger project0 in the list of Recent Projects actions.
    projects.recent_projects_actions[2].trigger()
    assert projects.get_active_project().root_path == path0


def test_project_explorer_tree_root(projects, tmpdir, qtbot):
    """
    Test that the root item of the project explorer tree widget is set
    correctly when switching projects.

    Regression test for spyder-ide/spyder#8455.
    """
    qtbot.addWidget(projects.explorer)
    projects.show_explorer()

    ppath1 = to_text_string(tmpdir.mkdir(u'測試'))
    ppath2 = to_text_string(tmpdir.mkdir(u'ïèô éàñ').mkdir(u'اختبار'))
    if os.name == 'nt':
        # For an explanation of why this part is necessary to make this test
        # pass for Python2 in Windows, see spyder-ide/spyder#8528.
        import win32file
        ppath1 = win32file.GetLongPathName(ppath1)
        ppath2 = win32file.GetLongPathName(ppath2)

    # Open the projects.
    for ppath in [ppath1, ppath2]:
        projects.open_project(path=ppath)
        projects.update_explorer()

        # Check that the root path of the project explorer tree widget is
        # set correctly.
        assert projects.get_active_project_path() == ppath
        assert projects.explorer.treewidget.root_path == osp.dirname(ppath)
        assert (projects.explorer.treewidget.rootIndex().data() ==
                osp.basename(osp.dirname(ppath)))

        # Check that the first visible item in the project explorer
        # tree widget is the folder of the project.
        topleft_index = (projects.explorer.treewidget.indexAt(
            projects.explorer.treewidget.rect().topLeft()))
        assert topleft_index.data() == osp.basename(ppath)


@flaky(max_runs=5)
def test_filesystem_notifications(qtbot, projects, tmpdir):
    """
    Test that filesystem notifications are emitted when creating,
    deleting and moving files and directories.
    """
    # Create a directory for the project and some files.
    project_root = tmpdir.mkdir('project0')
    folder0 = project_root.mkdir('folder0')
    folder1 = project_root.mkdir('folder1')
    file0 = project_root.join('file0')
    file1 = folder0.join('file1')
    file2 = folder0.join('file2')
    file3 = folder1.join('file3')
    file0.write('')
    file1.write('')
    file3.write('ab')

    # Open the project
    projects.open_project(path=to_text_string(project_root))

    # Get a reference to the filesystem event handler
    fs_handler = projects.watcher.event_handler

    # Test file creation
    with qtbot.waitSignal(fs_handler.sig_file_created,
                          timeout=30000) as blocker:
        file2.write('')

    file_created, is_dir = blocker.args
    assert file_created == to_text_string(file2)
    assert not is_dir

    # Test folder creation
    with qtbot.waitSignal(fs_handler.sig_file_created,
                          timeout=3000) as blocker:
        folder2 = project_root.mkdir('folder2')

    folder_created, is_dir = blocker.args
    assert folder_created == osp.join(to_text_string(project_root), 'folder2')

    # Test file move/renaming
    new_file = osp.join(to_text_string(folder0), 'new_file')
    with qtbot.waitSignal(fs_handler.sig_file_moved,
                          timeout=3000) as blocker:
        shutil.move(to_text_string(file1), new_file)

    original_file, file_moved, is_dir = blocker.args
    assert original_file == to_text_string(file1)
    assert file_moved == new_file
    assert not is_dir

    # Test folder move/renaming
    new_folder = osp.join(to_text_string(project_root), 'new_folder')
    with qtbot.waitSignal(fs_handler.sig_file_moved,
                          timeout=3000) as blocker:
        shutil.move(to_text_string(folder2), new_folder)

    original_folder, folder_moved, is_dir = blocker.args
    assert original_folder == to_text_string(folder2)
    assert folder_moved == new_folder
    assert is_dir

    # Test file deletion
    with qtbot.waitSignal(fs_handler.sig_file_deleted,
                          timeout=3000) as blocker:
        os.remove(to_text_string(file0))

    deleted_file, is_dir = blocker.args
    assert deleted_file == to_text_string(file0)
    assert not is_dir
    assert not osp.exists(to_text_string(file0))

    # Test folder deletion
    with qtbot.waitSignal(fs_handler.sig_file_deleted,
                          timeout=3000) as blocker:
        shutil.rmtree(to_text_string(folder0))

    deleted_folder, is_dir = blocker.args
    assert to_text_string(folder0) in deleted_folder

    # For some reason this fails in macOS
    if not sys.platform == 'darwin':
        # Test file/folder modification
        with qtbot.waitSignal(fs_handler.sig_file_modified,
                              timeout=3000) as blocker:
            file3.write('abc')

        modified_file, is_dir = blocker.args
        assert modified_file in to_text_string(file3)


if __name__ == "__main__":
    pytest.main()
