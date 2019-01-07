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
from qtpy.QtWidgets import QApplication
from qtpy.QtGui import QPixmap
from qtpy.QtCore import Qt

# Local imports
from spyder.plugins.plots.widgets.figurebrowser import FigureBrowser
from spyder.py3compat import to_text_string


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def figbrowser(qtbot):
    """An empty figure browser widget fixture."""
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
    plt.close('all')

    # Read back and return the binary data from the file.
    with open(figname, "rb") as img:
        fig = img.read()
    return fig


def add_figures_to_browser(figbrowser, nfig, tmpdir, fmt='image/png'):
    """
    Create and add bitmap figures to the figure browser. Also return a list
    of the created figures data.
    """
    fext = '.svg' if fmt == 'image/svg+xml' else '.png'
    figs = []
    for i in range(nfig):
        figname = osp.join(to_text_string(tmpdir), 'mplfig' + str(i) + fext)
        figs.append(create_figure(figname))
        figbrowser._handle_new_figure(figs[-1], fmt)

    assert len(figbrowser.thumbnails_sb._thumbnails) == nfig
    assert figbrowser.thumbnails_sb.get_current_index() == nfig - 1
    assert figbrowser.thumbnails_sb.current_thumbnail.canvas.fig == figs[-1]
    assert figbrowser.figviewer.figcanvas.fig == figs[-1]

    return figs


def png_to_qimage(png):
    """Return a QImage from the raw data of a png image."""
    qpix = QPixmap()
    qpix.loadFromData(png, 'image/png'.upper())
    return qpix.toImage()


# =============================================================================
# ---- Tests
# =============================================================================
@pytest.mark.parametrize("fmt, fext",
                         [('image/png', '.png'), ('image/svg+xml', '.svg')])
def test_handle_new_figures(figbrowser, tmpdir, fmt, fext):
    """
    Test that the figure browser widget display correctly new figures in
    its viewer and thumbnails scrollbar.
    """
    assert len(figbrowser.thumbnails_sb._thumbnails) == 0
    assert figbrowser.thumbnails_sb.current_thumbnail is None
    assert figbrowser.figviewer.figcanvas.fig is None

    for i in range(3):
        figname = osp.join(to_text_string(tmpdir), 'mplfig' + str(i) + fext)
        fig = create_figure(figname)
        figbrowser._handle_new_figure(fig, fmt)
        assert len(figbrowser.thumbnails_sb._thumbnails) == i + 1
        assert figbrowser.thumbnails_sb.get_current_index() == i
        assert figbrowser.thumbnails_sb.current_thumbnail.canvas.fig == fig
        assert figbrowser.figviewer.figcanvas.fig == fig


@pytest.mark.parametrize("fmt, fext",
                         [('image/png', '.png'), ('image/svg+xml', '.svg')])
def test_save_figure_to_file(figbrowser, tmpdir, mocker, fmt, fext):
    """
    Test saving png and svg figures to file with the figure browser.
    """
    # Create a figure with matplotlib and load it in the figure browser.
    mpl_figname = osp.join(to_text_string(tmpdir), 'mplfig' + fext)
    mplfig = create_figure(mpl_figname)
    figbrowser._handle_new_figure(mplfig, fmt)

    # Save the figure back to disk with the figure browser.
    spy_figname = osp.join(to_text_string(tmpdir), 'spyfig' + fext)
    mocker.patch('spyder.plugins.plots.widgets.figurebrowser.getsavefilename',
                 return_value=(spy_figname, fext))
    figbrowser.thumbnails_sb.save_current_figure_as()
    assert osp.exists(spy_figname)

    # Compare the figure created with matplotlib with the one created with our
    # figure browser.
    with open(spy_figname, "rb") as figfile:
        spyfig = figfile.read()
    assert mplfig == spyfig


@pytest.mark.parametrize("fmt", ['image/png', 'image/svg+xml'])
def test_clear_current_figure(figbrowser, tmpdir, fmt):
    """
    Test that clearing the current figure works as expected.
    """
    # Open some figures in the figure browser.
    figs = add_figures_to_browser(figbrowser, 2, tmpdir, fmt)

    # Remove the first figure.
    figbrowser.close_figure()
    assert len(figbrowser.thumbnails_sb._thumbnails) == 1
    assert figbrowser.thumbnails_sb.get_current_index() == 0
    assert figbrowser.thumbnails_sb.current_thumbnail.canvas.fig == figs[0]
    assert figbrowser.figviewer.figcanvas.fig == figs[0]

    # Remove the last figure.
    figbrowser.close_figure()
    assert len(figbrowser.thumbnails_sb._thumbnails) == 0
    assert figbrowser.thumbnails_sb.get_current_index() == -1
    assert figbrowser.thumbnails_sb.current_thumbnail is None
    assert figbrowser.figviewer.figcanvas.fig is None


@pytest.mark.parametrize("fmt", ['image/png', 'image/svg+xml'])
def test_clear_all_figures(figbrowser, tmpdir, fmt):
    """
    Test that clearing all figures displayed in the thumbnails scrollbar
    works as expected.
    """
    # Open some figures in the figure browser.
    add_figures_to_browser(figbrowser, 3, tmpdir, fmt)

    # Close all previously opened figures.
    figbrowser.close_all_figures()
    assert len(figbrowser.thumbnails_sb._thumbnails) == 0
    assert figbrowser.thumbnails_sb.get_current_index() == -1
    assert figbrowser.thumbnails_sb.current_thumbnail is None
    assert figbrowser.figviewer.figcanvas.fig is None


@pytest.mark.parametrize("fmt", ['image/png', 'image/svg+xml'])
def test_go_prev_next_thumbnail(figbrowser, tmpdir, fmt):
    """
    Test go to previous and next thumbnail actions.
    """
    # Open some figures in the figure browser.
    figs = add_figures_to_browser(figbrowser, 3, tmpdir, fmt)

    # Circle through the open figures with go_next_thumbnail and
    # go_previous_thumbnail.
    figbrowser.go_next_thumbnail()
    assert figbrowser.thumbnails_sb.get_current_index() == 0
    assert figbrowser.thumbnails_sb.current_thumbnail.canvas.fig == figs[0]
    assert figbrowser.figviewer.figcanvas.fig == figs[0]

    figbrowser.go_previous_thumbnail()
    assert figbrowser.thumbnails_sb.get_current_index() == 2
    assert figbrowser.thumbnails_sb.current_thumbnail.canvas.fig == figs[2]
    assert figbrowser.figviewer.figcanvas.fig == figs[2]

    figbrowser.go_previous_thumbnail()
    assert figbrowser.thumbnails_sb.get_current_index() == 1
    assert figbrowser.thumbnails_sb.current_thumbnail.canvas.fig == figs[1]
    assert figbrowser.figviewer.figcanvas.fig == figs[1]


@pytest.mark.parametrize("fmt", ['image/png', 'image/svg+xml'])
def test_mouse_clicking_thumbnails(figbrowser, tmpdir, qtbot, fmt):
    """
    Test mouse clicking on thumbnails.
    """
    # Open some figures in the figure browser.
    figs = add_figures_to_browser(figbrowser, 3, tmpdir, fmt)

    for i in [1, 0, 2]:
        qtbot.mouseClick(
            figbrowser.thumbnails_sb._thumbnails[i].canvas, Qt.LeftButton)
        assert figbrowser.thumbnails_sb.get_current_index() == i
        assert figbrowser.thumbnails_sb.current_thumbnail.canvas.fig == figs[i]
        assert figbrowser.figviewer.figcanvas.fig == figs[i]


def test_copy_png_to_clipboard(figbrowser, tmpdir):
    """
    Test copying png figures to the clipboard.
    """
    # Open some figures in the figure browser.
    figs = add_figures_to_browser(figbrowser, 3, tmpdir, 'image/png')
    clipboard = QApplication.clipboard()

    # Copy the current figure (last thumbnail) to the clipboard.
    figbrowser.copy_figure()
    assert clipboard.image() == png_to_qimage(figs[-1])

    # Copy the first thumbnail to the clipboard.
    figbrowser.go_next_thumbnail()
    figbrowser.copy_figure()
    assert clipboard.image() == png_to_qimage(figs[0])


def test_copy_svg_to_clipboard(figbrowser, tmpdir):
    """
    Test copying svg figures to the clipboard.
    """
    # Open some figures in the figure browser.
    figs = add_figures_to_browser(figbrowser, 3, tmpdir, 'image/svg+xml')
    clipboard = QApplication.clipboard()

    # Copy the current figure (last thumbnail) to the clipboard.
    figbrowser.copy_figure()
    assert clipboard.mimeData().data('image/svg+xml') == figs[-1]

    # Copy the first thumbnail to the clipboard.
    figbrowser.go_next_thumbnail()
    figbrowser.copy_figure()
    assert clipboard.mimeData().data('image/svg+xml') == figs[0]


if __name__ == "__main__":
    import os
    pytest.main([os.path.basename(__file__), '-vv', '-rw'])
