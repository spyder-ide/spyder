# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for configdialog.py
"""

# Standard librery imports
import os.path as osp
import tempfile

# Test library imports
import pytest

# Local imports
from spyder.plugins.projects.confpage import (EmptyProject,
                                                  ProjectPreferences)

@pytest.fixture
def projects_preferences(qtbot):
    """Set up ProjectPreferences."""
    project_dir = tempfile.mkdtemp() + osp.sep + '.spyproject'
    project = EmptyProject(project_dir)
    project_preferences = ProjectPreferences(None, project)
    qtbot.addWidget(project_preferences)
    return (project, project_preferences)


def test_projects_preferences(projects_preferences):
    """Run Project Preferences."""
    project, preferences = projects_preferences
    preferences.resize(250, 480)
    preferences.show()
    assert preferences


if __name__ == "__main__":
    pytest.main()
