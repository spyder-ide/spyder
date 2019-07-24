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
from spyder.plugins.variableexplorer.widgets.importwizard import ImportWizard


@pytest.fixture
def importwizard(qtbot):
    """Set up ImportWizard."""
    text = u"17/11/1976\t1.34\n14/05/09\t3.14"
    importwizard = ImportWizard(None, text)
    qtbot.addWidget(importwizard)
    return importwizard


def test_importwizard(importwizard):
    """Run ImportWizard dialog."""
    importwizard.show()
    assert importwizard


if __name__ == "__main__":
    pytest.main()
