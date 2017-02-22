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
from spyder.widgets.explorer import FileExplorerTest, ProjectExplorerTest
from spyder.utils.qthelpers import qapplication

def test_file_explorer():
    """Run FileExplorerTest."""
    app = qapplication()
    test = FileExplorerTest()
    test.resize(640, 480)
    test.show()
    app.exec_()

def test_project_explorer():
    """Run ProjectExplorerTest."""
    app = qapplication()
    test = ProjectExplorerTest()
    test.resize(640, 480)
    test.show()
    app.exec_()

if __name__ == "__main__":
    pytest.main()
    