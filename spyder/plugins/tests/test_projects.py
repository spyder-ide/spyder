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

# Third party imports
import pytest

# Local imports
import spyder.plugins
from spyder.plugins.projects import Projects
from spyder.py3compat import to_text_string


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def projects(qtbot):
    """Projects plugin fixture"""
    projects = Projects(parent=None, testing=True)
    qtbot.addWidget(projects)
    return projects


@pytest.fixture
def projects_with_dockwindow(projects, mocker):
    """Fixture for Projects plugin with a dockwindow"""
    projects.shortcut = None
    mocker.patch.object(spyder.plugins.SpyderDockWidget,
                        'install_tab_event_filter')
    mocker.patch.object(projects, 'toggle_view_action')
    projects.create_dockwidget()
    return projects


# =============================================================================
# Tests
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
def test_close_project_sets_visible_config(projects_with_dockwindow, tmpdir,
                                           value):
    """Test that when project is closed, the config option
    visible_if_project_open is set to the correct value."""
    projects = projects_with_dockwindow

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
def test_closing_plugin_sets_visible_config(
        projects_with_dockwindow, tmpdir, value):
    """Test that closing_plugin() sets config option visible_if_project_open
    if a project is open."""
    projects = projects_with_dockwindow
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
def test_open_project_uses_visible_config(
        projects_with_dockwindow, tmpdir, value):
    """Test that when a project is opened, the project explorer is only opened
    if the config option visible_if_project_open is set."""
    projects = projects_with_dockwindow
    projects.set_option('visible_if_project_open', value)
    projects.open_project(path=to_text_string(tmpdir))
    assert projects.dockwidget.isVisible() == value


if __name__ == "__main__":
    pytest.main()
