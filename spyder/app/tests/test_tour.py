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
def setup_tour(qtbot):
    "Setup the QMainWindow for the tour."
    tour = TourTestWindow()
    qtbot.addWidget(tour)
    return tour

def test_tour(qtbot):
    """Test tour."""
    tour = setup_tour(qtbot)
    tour.show()
    assert tour


if __name__ == "__main__":
    pytest.main()
