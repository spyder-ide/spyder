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
from __future__ import division
import os.path as osp
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Third party imports
import pytest
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np
from qtpy.QtWidgets import QApplication, QStyle
from qtpy.QtGui import QPixmap
from qtpy.QtCore import Qt

# Local imports
from spyder.plugins.plots.widgets.figurebrowser import (FigureBrowser,
                                                        FigureThumbnail)
from spyder.py3compat import to_text_string


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def figbrowser(qtbot):
    """An empty figure browser widget fixture."""
    figbrowser = FigureBrowser()
    figbrowser.set_shellwidget(Mock())
    figbrowser.setup(mute_inline_plotting=True, show_plot_outline=False,
                     auto_fit_plotting=False)
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
    fig = Figure()
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_axes([0.15, 0.15, 0.7, 0.7])
    fig.set_size_inches(6, 4)
    ax.plot(np.random.rand(10), '.', color='red')
    fig.savefig(figname)

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
                         [('image/png', '.png'),
                          ('image/svg+xml', '.svg'),
                          ('image/svg+xml', '.png')])
def test_save_figure_to_file(figbrowser, tmpdir, mocker, fmt, fext):
    """
    Test saving png and svg figures to file with the figure browser.
    """
    fig = add_figures_to_browser(figbrowser, 1, tmpdir, fmt)[0]
    expected_qpix = QPixmap()
    expected_qpix.loadFromData(fig, fmt.upper())

    # Save the figure to disk with the figure browser.
    saved_figname = osp.join(to_text_string(tmpdir), 'spyfig' + fext)
    mocker.patch('spyder.plugins.plots.widgets.figurebrowser.getsavefilename',
                 return_value=(saved_figname, fext))

    figbrowser.save_figure()
    saved_qpix = QPixmap()
    saved_qpix.load(saved_figname)

    assert osp.exists(saved_figname)
    assert expected_qpix.toImage() == saved_qpix.toImage()


@pytest.mark.parametrize("fmt", ['image/png', 'image/svg+xml'])
def test_save_all_figures(figbrowser, tmpdir, mocker, fmt):
    """
    Test saving all figures contained in the thumbnail scrollbar in batch
    into a single directory.
    """
    figs = add_figures_to_browser(figbrowser, 3, tmpdir, fmt)

    # Save all figures, but cancel the dialog to get a directory.
    mocker.patch(
        'spyder.plugins.plots.widgets.figurebrowser.getexistingdirectory',
        return_value=None)
    fignames = figbrowser.save_all_figures()
    assert fignames is None

    # Save all figures.
    mocker.patch(
        'spyder.plugins.plots.widgets.figurebrowser.getexistingdirectory',
        return_value=to_text_string(tmpdir.mkdir('all_saved_figures')))
    fignames = figbrowser.save_all_figures()
    assert len(fignames) == len(figs)
    for fig, figname in zip(figs, fignames):
        expected_qpix = QPixmap()
        expected_qpix.loadFromData(fig, fmt.upper())
        saved_qpix = QPixmap()
        saved_qpix.load(figname)

        assert osp.exists(figname)
        assert expected_qpix.toImage() == saved_qpix.toImage()


@pytest.mark.parametrize("fmt", ['image/png', 'image/svg+xml'])
def test_close_current_figure(figbrowser, tmpdir, fmt):
    """
    Test that clearing the current figure works as expected.
    """
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
def test_close_all_figures(figbrowser, tmpdir, fmt):
    """
    Test that clearing all figures displayed in the thumbnails scrollbar
    works as expected.
    """
    add_figures_to_browser(figbrowser, 3, tmpdir, fmt)

    # Close all previously opened figures.
    figbrowser.close_all_figures()
    assert len(figbrowser.thumbnails_sb._thumbnails) == 0
    assert figbrowser.thumbnails_sb.get_current_index() == -1
    assert figbrowser.thumbnails_sb.current_thumbnail is None
    assert figbrowser.figviewer.figcanvas.fig is None
    assert len(figbrowser.thumbnails_sb.findChildren(FigureThumbnail)) == 0


@pytest.mark.parametrize("fmt", ['image/png', 'image/svg+xml'])
def test_close_one_thumbnail(figbrowser, tmpdir, fmt):
    """
    Test the thumbnail is removed from the GUI.
    """
    # Add two figures to the browser
    add_figures_to_browser(figbrowser, 2, tmpdir, fmt)
    assert len(figbrowser.thumbnails_sb.findChildren(FigureThumbnail)) == 2

    # Remove the first figure
    figures = figbrowser.thumbnails_sb.findChildren(FigureThumbnail)
    figbrowser.thumbnails_sb.remove_thumbnail(figures[0])

    assert len(figbrowser.thumbnails_sb.findChildren(FigureThumbnail)) == 1


@pytest.mark.parametrize("fmt", ['image/png', 'image/svg+xml'])
def test_go_prev_next_thumbnail(figbrowser, tmpdir, fmt):
    """
    Test go to previous and next thumbnail actions.
    """
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


def test_scroll_to_item(figbrowser, tmpdir, qtbot):
    """Test scroll to the item of ThumbnailScrollBar."""
    nfig = 10
    add_figures_to_browser(figbrowser, nfig, tmpdir, 'image/png')
    figbrowser.setFixedSize(500, 500)

    for __ in range(nfig // 2):
        figbrowser.go_next_thumbnail()
        qtbot.wait(500)

    scene = figbrowser.thumbnails_sb.scene

    spacing = scene.verticalSpacing()
    height = scene.itemAt(0).sizeHint().height()
    height_view = figbrowser.thumbnails_sb.scrollarea.viewport().height()

    expected = (spacing * (nfig // 2)) + (height * (nfig // 2 - 1)) - \
               ((height_view - height) // 2)

    vsb = figbrowser.thumbnails_sb.scrollarea.verticalScrollBar()
    assert vsb.value() == expected


@pytest.mark.parametrize("fmt", ['image/png', 'image/svg+xml'])
def test_mouse_clicking_thumbnails(figbrowser, tmpdir, qtbot, fmt):
    """
    Test mouse clicking on thumbnails.
    """
    figs = add_figures_to_browser(figbrowser, 3, tmpdir, fmt)
    for i in [1, 0, 2]:
        qtbot.mouseClick(
            figbrowser.thumbnails_sb._thumbnails[i].canvas, Qt.LeftButton)
        assert figbrowser.thumbnails_sb.get_current_index() == i
        assert figbrowser.thumbnails_sb.current_thumbnail.canvas.fig == figs[i]
        assert figbrowser.figviewer.figcanvas.fig == figs[i]


@pytest.mark.parametrize("fmt", ['image/png', 'image/svg+xml'])
def test_save_thumbnails(figbrowser, tmpdir, qtbot, mocker, fmt):
    """
    Test saving figures by clicking on the thumbnail icon.
    """
    figs = add_figures_to_browser(figbrowser, 3, tmpdir, fmt)
    fext = '.svg' if fmt == 'image/svg+xml' else '.png'

    # Save the second thumbnail of the scrollbar.
    figname = osp.join(to_text_string(tmpdir), 'figname' + fext)
    mocker.patch('spyder.plugins.plots.widgets.figurebrowser.getsavefilename',
                 return_value=(figname, fext))
    qtbot.mouseClick(
        figbrowser.thumbnails_sb._thumbnails[1].savefig_btn, Qt.LeftButton)

    expected_qpix = QPixmap()
    expected_qpix.loadFromData(figs[1], fmt.upper())
    saved_qpix = QPixmap()
    saved_qpix.load(figname)

    assert osp.exists(figname)
    assert expected_qpix.toImage() == saved_qpix.toImage()


@pytest.mark.parametrize("fmt", ['image/png', 'image/svg+xml'])
def test_close_thumbnails(figbrowser, tmpdir, qtbot, mocker, fmt):
    """
    Test closing figures by clicking on the thumbnail icon.
    """
    figs = add_figures_to_browser(figbrowser, 3, tmpdir, fmt)

    # Close the second thumbnail of the scrollbar.
    qtbot.mouseClick(
        figbrowser.thumbnails_sb._thumbnails[1].delfig_btn, Qt.LeftButton)
    del figs[1]

    assert len(figbrowser.thumbnails_sb._thumbnails) == len(figs)
    assert figbrowser.thumbnails_sb._thumbnails[0].canvas.fig == figs[0]
    assert figbrowser.thumbnails_sb._thumbnails[1].canvas.fig == figs[1]


def test_copy_png_to_clipboard(figbrowser, tmpdir):
    """
    Test copying png figures to the clipboard.
    """
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
    figs = add_figures_to_browser(figbrowser, 3, tmpdir, 'image/svg+xml')
    clipboard = QApplication.clipboard()

    # Copy the current figure (last thumbnail) to the clipboard.
    figbrowser.copy_figure()
    assert clipboard.mimeData().data('image/svg+xml') == figs[-1]

    # Copy the first thumbnail to the clipboard.
    figbrowser.go_next_thumbnail()
    figbrowser.copy_figure()
    assert clipboard.mimeData().data('image/svg+xml') == figs[0]


@pytest.mark.parametrize("fmt", ['image/png', 'image/svg+xml'])
def test_zoom_figure_viewer(figbrowser, tmpdir, fmt):
    """
    Test zooming in and out the figure diplayed in the figure viewer.
    """
    fig = add_figures_to_browser(figbrowser, 1, tmpdir, fmt)[0]
    figcanvas = figbrowser.figviewer.figcanvas

    # Set `Fit plots to windows` to False before the test.
    figbrowser.change_auto_fit_plotting(False)

    # Calculate original figure size in pixels.
    qpix = QPixmap()
    qpix.loadFromData(fig, fmt.upper())
    fwidth, fheight = qpix.width(), qpix.height()

    assert figbrowser.zoom_disp.value() == 100
    assert figcanvas.width() == fwidth
    assert figcanvas.height() == fheight

    # Zoom in and out the figure in the figure viewer.
    scaling_factor = 0
    scaling_step = figbrowser.figviewer._scalestep
    for zoom_step in [1, 1, -1, -1, -1]:
        if zoom_step == 1:
            figbrowser.zoom_in()
        elif zoom_step == -1:
            figbrowser.zoom_out()
        scaling_factor += zoom_step
        scale = scaling_step**scaling_factor

        assert (figbrowser.zoom_disp.value() ==
                np.round(int(fwidth * scale) / fwidth * 100))
        assert figcanvas.width() == int(fwidth * scale)
        assert figcanvas.height() == int(fheight * scale)


@pytest.mark.parametrize("fmt", ['image/png', 'image/svg+xml'])
def test_autofit_figure_viewer(figbrowser, tmpdir, fmt):
    """
    Test figure diplayed when `Fit plots to window` is True.
    """
    fig = add_figures_to_browser(figbrowser, 1, tmpdir, fmt)[0]
    figviewer = figbrowser.figviewer
    figcanvas = figviewer.figcanvas

    # Calculate original figure size in pixels.
    qpix = QPixmap()
    qpix.loadFromData(fig, fmt.upper())
    fwidth, fheight = qpix.width(), qpix.height()

    # Test when `Fit plots to window` is set to True.
    # Otherwise, test should fall into `test_zoom_figure_viewer`
    figbrowser.change_auto_fit_plotting(True)

    size = figviewer.size()
    style = figviewer.style()
    width = (size.width() -
             style.pixelMetric(QStyle.PM_LayoutLeftMargin) -
             style.pixelMetric(QStyle.PM_LayoutRightMargin))
    height = (size.height() -
              style.pixelMetric(QStyle.PM_LayoutTopMargin) -
              style.pixelMetric(QStyle.PM_LayoutBottomMargin))
    if (fwidth / fheight) > (width / height):
        new_width = int(width)
        new_height = int(width / fwidth * fheight)
    else:
        new_height = int(height)
        new_width = int(height / fheight * fwidth)

    assert figcanvas.width() == new_width
    assert figcanvas.height() == new_height
    assert (figbrowser.zoom_disp.value() ==
            round(figcanvas.width() / fwidth * 100))


if __name__ == "__main__":
    pytest.main()
