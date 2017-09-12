# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for explorer.py
"""

# Test library imports
import pytest

# Local imports
from spyder.widgets.projects.explorer import ProjectExplorerTest

@pytest.fixture
def setup_projects_explorer(qtbot):
    """Set up ProjectExplorerWidgetTest."""
    project_explorer = ProjectExplorerTest()
    qtbot.addWidget(project_explorer)
    return project_explorer

def test_project_explorer(qtbot):
    """Run project explorer."""
    project_explorer = setup_projects_explorer(qtbot)
    project_explorer.resize(250, 480)
    project_explorer.show()
    assert project_explorer


if __name__ == "__main__":
    pytest.main()
