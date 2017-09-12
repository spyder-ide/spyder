# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for workingdirectory plugin."""

# Test library imports
import pytest

# Local imports
from spyder.plugins.workingdirectory.plugin import WorkingDirectory


@pytest.fixture
def setup_workingdirectory(qtbot):
    """Setupp working directory plugin."""
    workingdirectory = WorkingDirectory(None)
    qtbot.addWidget(workingdirectory)
    workingdirectory.show()

    return workingdirectory, qtbot


def test_basic_initialization(setup_workingdirectory):
    """Test Working Directory plugin initialization."""
    workingdirectory, qtbot = setup_workingdirectory

    # Assert that workingdirectory exists
    assert workingdirectory is not None


if __name__ == "__main__":
    pytest.main()
