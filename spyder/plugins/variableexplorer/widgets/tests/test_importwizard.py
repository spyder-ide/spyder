# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for importwizard.py
"""

# Test library imports
import pytest

# Local imports
from spyder.widgets.variableexplorer.importwizard import ImportWizard

@pytest.fixture
def setup_importwizard(qtbot, text):
    """Set up ImportWizard."""
    importwizard = ImportWizard(None, text)
    qtbot.addWidget(importwizard)
    return importwizard

def test_importwizard(qtbot):
    """Run ImportWizard dialog."""
    text = u"17/11/1976\t1.34\n14/05/09\t3.14"
    importwizard = setup_importwizard(qtbot, text)
    importwizard.show()
    assert importwizard


if __name__ == "__main__":
    pytest.main()
