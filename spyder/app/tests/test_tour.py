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

# Local imports
from spyder.app.tour import TourTestWindow


@pytest.fixture
def tour(qtbot):
    "Setup the QMainWindow for the tour."
    tour = TourTestWindow()
    qtbot.addWidget(tour)
    return tour


def test_tour(tour, qtbot):
    """Test tour."""
    tour.show()
    assert tour


if __name__ == "__main__":
    pytest.main()
