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
from spyder.utils import encoding
from spyder.plugins.projects import Projects


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def projects(qtbot):
    """Projects plugin fixture"""
    projects = Projects(parent=None, testing=True)
    qtbot.addWidget(projects)
    return projects


# =============================================================================
# Tests
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


if __name__ == "__main__":
    pytest.main()
