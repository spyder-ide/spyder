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
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Third party imports
import pytest

# Local imports
import spyder.plugins.base
from spyder.plugins.projects.plugin import Projects
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

    # Patching necessary to test visible_if_project_open
    projects.shortcut = None
    mocker.patch.object(spyder.plugins.base.SpyderDockWidget,
                        'install_tab_event_filter')
    mocker.patch.object(projects, 'toggle_view_action')
    projects.create_dockwidget()

    # This can only be done at this point
    projects.main = MainWindowMock()

    qtbot.addWidget(projects)
    projects.show()
    return projects


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


def test_set_get_project_filenames_when_closing(projects, tmpdir, mocker):
    """
    Test that the currently opened files in the Editor are saved and loaded
    correctly to and from the project config when the project is closed and
    then reopened.

    Regression test for Issue #8375
    """
    # Create a project.
    path = to_text_string(tmpdir.mkdir('project1'))
    projects.open_project(path=path)
    assert projects.get_project_filenames() == []

    # Then we do some mocking to simulate the case where files were
    # opened in the Editor while the project was open.
    opened_files = ['file1', 'file2', 'file3']
    mocker.patch.object(
        projects.main.editor, 'get_open_filenames', return_value=opened_files)
    # We mock os.path.isfile so that we do not have to
    # actually create the files on the disk.
    mocker.patch(
        'spyder.plugins.projects.api.os.path.isfile', return_value=True)

    # Close and reopen the project.
    projects.close_project()
    projects.open_project(path=path)
    assert projects.get_project_filenames() == opened_files


def test_set_get_project_filenames_when_switching(projects, tmpdir, mocker):
    """
    Test that files in the Editor are loaded and saved correctly when
    switching projects.
    """
    # Create a project.
    path1 = to_text_string(tmpdir.mkdir('project1'))
    projects.open_project(path=path1)
    assert projects.get_project_filenames() == []

    # Then we do some mocking to simulate the case where files were
    # opened in the Editor while the project was open.
    opened_files = ['file1', 'file2', 'file3']
    mocker.patch.object(
        projects.main.editor, 'get_open_filenames', return_value=opened_files)
    # Mock os.path.isfile so that we do not have to actually save the files
    # and save them to on the disk.
    mocker.patch(
        'spyder.plugins.projects.api.os.path.isfile', return_value=True)

    # Switch to another project.
    path2 = to_text_string(tmpdir.mkdir('project2'))
    projects.open_project(path=path2)
    assert projects.get_project_filenames() == []

    # Switch back to the first project.
    projects.close_project()
    projects.open_project(path=path1)
    assert projects.get_project_filenames() == opened_files


if __name__ == "__main__":
    pytest.main()
