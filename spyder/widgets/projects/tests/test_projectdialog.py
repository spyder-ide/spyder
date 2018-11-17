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
from spyder.widgets.projects.projectdialog import ProjectDialog


@pytest.fixture
def projects_dialog(qtbot):
    """Set up ProjectDialog."""
    dlg = ProjectDialog(None)
    qtbot.addWidget(dlg)
    return dlg


def test_project_dialog(projects_dialog):
    """Run project dialog."""
    projects_dialog.show()
    assert projects_dialog


if __name__ == "__main__":
    pytest.main()
