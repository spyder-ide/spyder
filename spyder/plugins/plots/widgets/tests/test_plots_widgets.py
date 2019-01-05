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


# =============================================================================
# ---- Helper functions
# =============================================================================
def create_figure(figname):
    """Create a matplotlib figure, save it to disk and return its data."""
    # Create and save to disk a figure with matplotlib.
    fig, ax = plt.subplots()
    fig.set_size_inches(6, 4)
    ax.plot(np.random.rand(10), '.', color='red')
    fig.savefig(figname)

    # Read back and return the binary data from the file.
    with open(figname, "rb") as img:
        fig = img.read()
    return fig

