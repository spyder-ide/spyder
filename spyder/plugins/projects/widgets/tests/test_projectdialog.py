# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for projectdialog.py
"""

# Test library imports
import pytest

# Local imports
from spyder.plugins.projects.widgets.projectdialog import ProjectDialog

@pytest.fixture
def setup_projects_dialog(qtbot):
    """Set up ProjectDialog."""
    dlg = ProjectDialog(None)
    qtbot.addWidget(dlg)
    return dlg

def test_project_dialog(qtbot):
    """Run project dialog."""
    dlg = setup_projects_dialog(qtbot)
    dlg.show()
    assert dlg


if __name__ == "__main__":
    pytest.main()
