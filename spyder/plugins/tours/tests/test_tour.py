# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for tour.py
"""

# Test library imports
import pytest

# Third party imports
from qtpy import PYSIDE6

# Local imports
from spyder.plugins.tours.widgets import TourTestWindow


@pytest.fixture
def tour(qtbot):
    "Setup the QMainWindow for the tour."
    tour = TourTestWindow()
    qtbot.addWidget(tour)
    return tour


@pytest.mark.skipif(PYSIDE6, reason="Segfaults with PySide6")
def test_tour(tour, qtbot):
    """Test tour."""
    tour.show()
    assert tour


if __name__ == "__main__":
    pytest.main()
