# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for the widgets used in the Plots plugin.
"""

# Standard library imports
import os.path as osp
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Third party imports
import pytest
import matplotlib.pyplot as plt
import numpy as np

# Local imports
from spyder.plugins.plots.widgets.figurebrowser import FigureBrowser


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def figbrowser(qtbot, mocker):
    """Plots plugin fixture."""
    figbrowser = FigureBrowser()
    figbrowser.set_shellwidget(Mock())
    figbrowser.setup(mute_inline_plotting=True, show_plot_outline=False)
    qtbot.addWidget(figbrowser)
    figbrowser.show()
    figbrowser.setMinimumSize(700, 500)
    return figbrowser

