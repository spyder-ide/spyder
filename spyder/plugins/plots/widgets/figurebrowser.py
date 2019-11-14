# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Figure browser widget

This is the main widget used in the Plots plugin
"""

# ---- Standard library imports
from __future__ import division
import os.path as osp
import sys

# ---- Third library imports
from qtconsole.svg import svg_to_image, svg_to_clipboard
from qtpy.compat import getsavefilename, getexistingdirectory
from qtpy.QtCore import Qt, Signal, QRect, QEvent, QPoint, QSize, QTimer, Slot
from qtpy.QtGui import QPixmap, QPainter, QKeySequence
from qtpy.QtWidgets import (QApplication, QHBoxLayout, QMenu,
                            QVBoxLayout, QWidget, QGridLayout, QFrame,
                            QScrollArea, QPushButton, QScrollBar, QSpinBox,
                            QSplitter, QStyle)

# ---- Local library imports
from spyder.config.base import _
from spyder.py3compat import is_unicode, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton, create_plugin_layout,
                                    MENU_SEPARATOR)
from spyder.utils.misc import getcwd_or_home
from spyder.config.gui import config_shortcut, get_shortcut, is_dark_interface


def save_figure_tofile(fig, fmt, fname):
    """Save fig to fname in the format specified by fmt."""
    root, ext = osp.splitext(fname)
    if ext == '.png' and fmt == 'image/svg+xml':
        qimg = svg_to_image(fig)
        qimg.save(fname)
    else:
        if fmt == 'image/svg+xml' and is_unicode(fig):
            fig = fig.encode('utf-8')

        with open(fname, 'wb') as f:
            f.write(fig)


def get_unique_figname(dirname, root, ext):
    """
    Append a number to "root" to form a filename that does not already exist
    in "dirname".
    """
    i = 1
    figname = root + '_%d' % i + ext
    while True:
        if osp.exists(osp.join(dirname, figname)):
            i += 1
            figname = root + '_%d' % i + ext
        else:
            return osp.join(dirname, figname)


class FigureBrowser(QWidget):
    """
    Widget to browse the figures that were sent by the kernel to the IPython
    console to be plotted inline.
    """
    sig_option_changed = Signal(str, object)
    sig_collapse = Signal()

    def __init__(self, parent=None, options_button=None, plugin_actions=[],
                 background_color=None):
        super(FigureBrowser, self).__init__(parent)

        self.shellwidget = None
        self.is_visible = True
        self.figviewer = None
        self.setup_in_progress = False
        self.background_color = background_color

        # Options :
        self.mute_inline_plotting = None
        self.show_plot_outline = None
        self.auto_fit_plotting = None

        # Option actions :
        self.mute_inline_action = None
        self.show_plot_outline_action = None
        self.auto_fit_action = None

        self.options_button = options_button
        self.plugin_actions = plugin_actions
        self.shortcuts = self.create_shortcuts()

    def setup(self, mute_inline_plotting=None, show_plot_outline=None,
              auto_fit_plotting=None):
        """Setup the figure browser with provided settings."""
        assert self.shellwidget is not None

        self.mute_inline_plotting = mute_inline_plotting
        self.show_plot_outline = show_plot_outline
        self.auto_fit_plotting = auto_fit_plotting

        if self.figviewer is not None:
            self.mute_inline_action.setChecked(mute_inline_plotting)
            self.show_plot_outline_action.setChecked(show_plot_outline)
            self.auto_fit_action.setChecked(auto_fit_plotting)
            return

        self.figviewer = FigureViewer(background_color=self.background_color)
        self.figviewer.setStyleSheet("FigureViewer{"
                                     "border: 1px solid lightgrey;"
                                     "border-top-width: 0px;"
                                     "border-bottom-width: 0px;"
                                     "border-left-width: 0px;"
                                     "}")
        self.thumbnails_sb = ThumbnailScrollBar(
            self.figviewer, background_color=self.background_color)

        toolbar = self.setup_toolbar()
        self.setup_option_actions(mute_inline_plotting,
                                  show_plot_outline,
                                  auto_fit_plotting)

        # Create the layout.
        main_widget = QSplitter()
        main_widget.addWidget(self.figviewer)
        main_widget.addWidget(self.thumbnails_sb)
        main_widget.setFrameStyle(QScrollArea().frameStyle())

        self.tools_layout = QHBoxLayout()
        for widget in toolbar:
            self.tools_layout.addWidget(widget)
        self.tools_layout.addStretch()
        self.setup_options_button()

        layout = create_plugin_layout(self.tools_layout, main_widget)
        self.setLayout(layout)

    def setup_toolbar(self):
        """Setup the toolbar"""
        savefig_btn = create_toolbutton(
                self, icon=ima.icon('filesave'),
                tip=_("Save Image As..."),
                triggered=self.save_figure)

        saveall_btn = create_toolbutton(
                self, icon=ima.icon('save_all'),
                tip=_("Save All Images..."),
                triggered=self.save_all_figures)

        copyfig_btn = create_toolbutton(
            self, icon=ima.icon('editcopy'),
            tip=_("Copy plot to clipboard as image (%s)") %
                  get_shortcut('plots', 'copy'),
            triggered=self.copy_figure)

        closefig_btn = create_toolbutton(
                self, icon=ima.icon('editclear'),
                tip=_("Remove image"),
                triggered=self.close_figure)

        closeall_btn = create_toolbutton(
                self, icon=ima.icon('filecloseall'),
                tip=_("Remove all images from the explorer"),
                triggered=self.close_all_figures)

        vsep1 = QFrame()
        vsep1.setFrameStyle(53)

        goback_btn = create_toolbutton(
                self, icon=ima.icon('ArrowBack'),
                tip=_("Previous Figure ({})").format(
                      get_shortcut('plots', 'previous figure')),
                triggered=self.go_previous_thumbnail)

        gonext_btn = create_toolbutton(
                self, icon=ima.icon('ArrowForward'),
                tip=_("Next Figure ({})").format(
                      get_shortcut('plots', 'next figure')),
                triggered=self.go_next_thumbnail)

        vsep2 = QFrame()
        vsep2.setFrameStyle(53)

        self.zoom_out_btn = create_toolbutton(
                self, icon=ima.icon('zoom_out'),
                tip=_("Zoom out (Ctrl + mouse-wheel-down)"),
                triggered=self.zoom_out)

        self.zoom_in_btn = create_toolbutton(
                self, icon=ima.icon('zoom_in'),
                tip=_("Zoom in (Ctrl + mouse-wheel-up)"),
                triggered=self.zoom_in)

        self.zoom_disp = QSpinBox()
        self.zoom_disp.setAlignment(Qt.AlignCenter)
        self.zoom_disp.setButtonSymbols(QSpinBox.NoButtons)
        self.zoom_disp.setReadOnly(True)
        self.zoom_disp.setSuffix(' %')
        self.zoom_disp.setRange(0, 9999)
        self.zoom_disp.setValue(100)
        self.figviewer.sig_zoom_changed.connect(self.zoom_disp.setValue)

        zoom_pan = QWidget()
        layout = QHBoxLayout(zoom_pan)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.zoom_out_btn)
        layout.addWidget(self.zoom_in_btn)
        layout.addWidget(self.zoom_disp)

        return [savefig_btn, saveall_btn, copyfig_btn, closefig_btn,
                closeall_btn, vsep1, goback_btn, gonext_btn, vsep2, zoom_pan]

    def setup_option_actions(self, mute_inline_plotting, show_plot_outline,
                             auto_fit_plotting):
        """Setup the actions to show in the cog menu."""
        self.setup_in_progress = True
        self.mute_inline_action = create_action(
            self, _("Mute inline plotting"),
            tip=_("Mute inline plotting in the ipython console."),
            toggled=lambda state:
            self.option_changed('mute_inline_plotting', state)
            )
        self.mute_inline_action.setChecked(mute_inline_plotting)

        self.show_plot_outline_action = create_action(
            self, _("Show plot outline"),
            tip=_("Show the plot outline."),
            toggled=self.show_fig_outline_in_viewer
            )
        self.show_plot_outline_action.setChecked(show_plot_outline)

        self.auto_fit_action = create_action(
            self, _("Fit plots to window"),
            tip=_("Automatically fit plots to Plot pane size."),
            toggled=self.change_auto_fit_plotting
            )
        self.auto_fit_action.setChecked(auto_fit_plotting)

        self.actions = [self.mute_inline_action, self.show_plot_outline_action,
                        self.auto_fit_action]

        self.setup_in_progress = False

    def setup_options_button(self):
        """Add the cog menu button to the toolbar."""
        if not self.options_button:
            # When the FigureBowser widget is instatiated outside of the
            # plugin (for testing purpose for instance), we need to create
            # the options_button and set its menu.
            self.options_button = create_toolbutton(
                self, text=_('Options'), icon=ima.icon('tooloptions'))

            actions = self.actions + [MENU_SEPARATOR] + self.plugin_actions
            self.options_menu = QMenu(self)
            add_actions(self.options_menu, actions)
            self.options_button.setMenu(self.options_menu)

        if self.tools_layout.itemAt(self.tools_layout.count() - 1) is None:
            self.tools_layout.insertWidget(
                self.tools_layout.count() - 1, self.options_button)
        else:
            self.tools_layout.addWidget(self.options_button)

    def create_shortcuts(self):
        """Create shortcuts for this widget."""
        # Configurable
        copyfig = config_shortcut(self.copy_figure, context='plots',
                                  name='copy', parent=self)
        prevfig = config_shortcut(self.go_previous_thumbnail, context='plots',
                                  name='previous figure', parent=self)
        nextfig = config_shortcut(self.go_next_thumbnail, context='plots',
                                  name='next figure', parent=self)

        return [copyfig, prevfig, nextfig]

    def get_shortcut_data(self):
        """
        Return shortcut data, a list of tuples (shortcut, text, default).

        shortcut (QShortcut or QAction instance)
        text (string): action/shortcut description
        default (string): default key sequence
        """
        return [sc.data for sc in self.shortcuts]

    def option_changed(self, option, value):
        """Handle when the value of an option has changed"""
        setattr(self, to_text_string(option), value)
        self.shellwidget.set_namespace_view_settings()
        if self.setup_in_progress is False:
            self.sig_option_changed.emit(option, value)

    def show_fig_outline_in_viewer(self, state):
        """Draw a frame around the figure viewer if state is True."""
        if state is True:
            self.figviewer.figcanvas.setStyleSheet(
                    "FigureCanvas{border: 1px solid lightgrey;}")
        else:
            self.figviewer.figcanvas.setStyleSheet("FigureCanvas{}")
        self.option_changed('show_plot_outline', state)

    def change_auto_fit_plotting(self, state):
        """Change the auto_fit_plotting option and scale images."""
        self.option_changed('auto_fit_plotting', state)
        self.figviewer.auto_fit_plotting = state
        self.zoom_out_btn.setEnabled(not state)
        self.zoom_in_btn.setEnabled(not state)

    def set_shellwidget(self, shellwidget):
        """Bind the shellwidget instance to the figure browser"""
        self.shellwidget = shellwidget
        shellwidget.set_figurebrowser(self)
        shellwidget.sig_new_inline_figure.connect(self._handle_new_figure)

    def get_actions(self):
        """Get the actions of the widget."""
        return self.actions

    def _handle_new_figure(self, fig, fmt):
        """
        Handle when a new figure is sent to the IPython console by the
        kernel.
        """
        self.thumbnails_sb.add_thumbnail(fig, fmt)

    # ---- Toolbar Handlers
    def zoom_in(self):
        """Zoom the figure in by a single step in the figure viewer."""
        self.figviewer.zoom_in()

    def zoom_out(self):
        """Zoom the figure out by a single step in the figure viewer."""
        self.figviewer.zoom_out()

    def go_previous_thumbnail(self):
        """
        Select the thumbnail previous to the currently selected one in the
        thumbnail scrollbar.
        """
        self.thumbnails_sb.go_previous_thumbnail()

    def go_next_thumbnail(self):
        """
        Select the thumbnail next to the currently selected one in the
        thumbnail scrollbar.
        """
        self.thumbnails_sb.go_next_thumbnail()

    def save_figure(self):
        """Save the currently selected figure in the thumbnail scrollbar."""
        self.thumbnails_sb.save_current_figure_as()

    def save_all_figures(self):
        """Save all the figures in a selected directory."""
        return self.thumbnails_sb.save_all_figures_as()

    def close_figure(self):
        """Close the currently selected figure in the thumbnail scrollbar."""
        self.thumbnails_sb.remove_current_thumbnail()

    def close_all_figures(self):
        """Close all the figures in the thumbnail scrollbar."""
        self.thumbnails_sb.remove_all_thumbnails()

    def copy_figure(self):
        """Copy figure from figviewer to clipboard."""
        if self.figviewer and self.figviewer.figcanvas.fig:
            self.figviewer.figcanvas.copy_figure()


class FigureViewer(QScrollArea):
    """
    A scrollarea that displays a single FigureCanvas with zooming and panning
    capability with CTRL + Mouse_wheel and Left-press mouse button event.
    """

    sig_zoom_changed = Signal(int)

    def __init__(self, parent=None, background_color=None):
        super(FigureViewer, self).__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.viewport().setObjectName("figviewport")
        self.viewport().setStyleSheet(
            "#figviewport {background-color:" + str(background_color) + "}")
        self.setFrameStyle(0)

        self.background_color = background_color
        self._scalefactor = 0
        self._scalestep = 1.2
        self._sfmax = 10
        self._sfmin = -10

        self.setup_figcanvas()
        self.auto_fit_plotting = False

        # An internal flag that tracks when the figure is being panned.
        self._ispanning = False

    @property
    def auto_fit_plotting(self):
        """
        Return whether to automatically fit the plot to the scroll area size.
        """
        return self._auto_fit_plotting

    @auto_fit_plotting.setter
    def auto_fit_plotting(self, value):
        """
        Set whether to automatically fit the plot to the scroll area size.
        """
        self._auto_fit_plotting = value
        if value:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scale_image()

    def setup_figcanvas(self):
        """Setup the FigureCanvas."""
        self.figcanvas = FigureCanvas(background_color=self.background_color)
        self.figcanvas.installEventFilter(self)
        self.setWidget(self.figcanvas)

    def load_figure(self, fig, fmt):
        """Set a new figure in the figure canvas."""
        self.figcanvas.load_figure(fig, fmt)
        self.scale_image()
        self.figcanvas.repaint()

    def eventFilter(self, widget, event):
        """A filter to control the zooming and panning of the figure canvas."""

        # ---- Zooming
        if event.type() == QEvent.Wheel and not self.auto_fit_plotting:
            modifiers = QApplication.keyboardModifiers()
            if modifiers == Qt.ControlModifier:
                if event.angleDelta().y() > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
                return True
            else:
                return False

        # ---- Scaling
        elif event.type() == QEvent.Paint and self.auto_fit_plotting:
            self.scale_image()

        # ---- Panning
        # Set ClosedHandCursor:
        elif event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                QApplication.setOverrideCursor(Qt.ClosedHandCursor)
                self._ispanning = True
                self.xclick = event.globalX()
                self.yclick = event.globalY()

        # Reset Cursor:
        elif event.type() == QEvent.MouseButtonRelease:
            QApplication.restoreOverrideCursor()
            self._ispanning = False

        # Move  ScrollBar:
        elif event.type() == QEvent.MouseMove:
            if self._ispanning:
                dx = self.xclick - event.globalX()
                self.xclick = event.globalX()

                dy = self.yclick - event.globalY()
                self.yclick = event.globalY()

                scrollBarH = self.horizontalScrollBar()
                scrollBarH.setValue(scrollBarH.value() + dx)

                scrollBarV = self.verticalScrollBar()
                scrollBarV.setValue(scrollBarV.value() + dy)

        return QWidget.eventFilter(self, widget, event)

    # ---- Figure Scaling Handlers
    def zoom_in(self):
        """Scale the image up by one scale step."""
        if self._scalefactor <= self._sfmax:
            self._scalefactor += 1
            self.scale_image()
            self._adjust_scrollbar(self._scalestep)

    def zoom_out(self):
        """Scale the image down by one scale step."""
        if self._scalefactor >= self._sfmin:
            self._scalefactor -= 1
            self.scale_image()
            self._adjust_scrollbar(1/self._scalestep)

    def scale_image(self):
        """Scale the image size."""
        fwidth = self.figcanvas.fwidth
        fheight = self.figcanvas.fheight

        # Don't auto fit plotting
        if not self.auto_fit_plotting:
            new_width = int(fwidth * self._scalestep ** self._scalefactor)
            new_height = int(fheight * self._scalestep ** self._scalefactor)

        # Auto fit plotting
        # Scale the image to fit the figviewer size while respecting the ratio.
        else:
            size = self.size()
            style = self.style()
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

        if self.figcanvas.size() != QSize(new_width, new_height):
            self.figcanvas.setFixedSize(new_width, new_height)
            self.sig_zoom_changed.emit(self.get_scaling())

    def get_scaling(self):
        """Get the current scaling of the figure in percent."""
        return round(self.figcanvas.width() / self.figcanvas.fwidth * 100)

    def reset_original_image(self):
        """Reset the image to its original size."""
        self._scalefactor = 0
        self.scale_image()

    def _adjust_scrollbar(self, f):
        """
        Adjust the scrollbar position to take into account the zooming of
        the figure.
        """
        # Adjust horizontal scrollbar :
        hb = self.horizontalScrollBar()
        hb.setValue(int(f * hb.value() + ((f - 1) * hb.pageStep()/2)))

        # Adjust the vertical scrollbar :
        vb = self.verticalScrollBar()
        vb.setValue(int(f * vb.value() + ((f - 1) * vb.pageStep()/2)))


class ThumbnailScrollBar(QFrame):
    """
    A widget that manages the display of the FigureThumbnails that are
    created when a figure is sent to the IPython console by the kernel and
    that controls what is displayed in the FigureViewer.
    """
    redirect_stdio = Signal(bool)
    _min_scrollbar_width = 100

    def __init__(self, figure_viewer, parent=None, background_color=None):
        super(ThumbnailScrollBar, self).__init__(parent)
        self._thumbnails = []
        self.background_color = background_color
        self.current_thumbnail = None
        self.set_figureviewer(figure_viewer)
        self.setup_gui()

    def setup_gui(self):
        """Setup the main layout of the widget."""
        scrollarea = self.setup_scrollarea()
        up_btn, down_btn = self.setup_arrow_buttons()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(up_btn)
        layout.addWidget(scrollarea)
        layout.addWidget(down_btn)

    def setup_scrollarea(self):
        """Setup the scrollarea that will contain the FigureThumbnails."""
        self.view = QWidget()

        self.scene = QGridLayout(self.view)
        self.scene.setContentsMargins(0, 0, 0, 0)

        self.scrollarea = QScrollArea()
        self.scrollarea.setWidget(self.view)
        self.scrollarea.setWidgetResizable(True)
        self.scrollarea.setFrameStyle(0)
        self.scrollarea.setViewportMargins(2, 2, 2, 2)
        self.scrollarea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollarea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollarea.setMinimumWidth(self._min_scrollbar_width)

        # Set the vertical scrollbar explicitely.
        # This is required to avoid a "RuntimeError: no access to protected
        # functions or signals for objects not created from Python" in Linux.
        self.scrollarea.setVerticalScrollBar(QScrollBar())

        # Install an event filter on the scrollbar.
        self.scrollarea.installEventFilter(self)

        return self.scrollarea

    def setup_arrow_buttons(self):
        """
        Setup the up and down arrow buttons that are placed at the top and
        bottom of the scrollarea.
        """
        # Get the size hint height of the horizontal scrollbar.
        height = self.scrollarea.horizontalScrollBar().sizeHint().height()

        # Setup the up and down arrow button.
        up_btn = up_btn = QPushButton(icon=ima.icon('last_edit_location'))
        up_btn.setFlat(True)
        up_btn.setFixedHeight(height)
        up_btn.clicked.connect(self.go_up)

        down_btn = QPushButton(icon=ima.icon('folding.arrow_down_on'))
        down_btn.setFlat(True)
        down_btn.setFixedHeight(height)
        down_btn.clicked.connect(self.go_down)

        return up_btn, down_btn

    def set_figureviewer(self, figure_viewer):
        """Set the bamespace for the FigureViewer."""
        self.figure_viewer = figure_viewer

    def eventFilter(self, widget, event):
        """
        An event filter to trigger an update of the thumbnails size so that
        their width fit that of the scrollarea.
        """
        if event.type() == QEvent.Resize:
            self._update_thumbnail_size()
        return super(ThumbnailScrollBar, self).eventFilter(widget, event)

    # ---- Save Figure
    def save_all_figures_as(self):
        """Save all the figures to a file."""
        self.redirect_stdio.emit(False)
        dirname = getexistingdirectory(self, caption='Save all figures',
                                       basedir=getcwd_or_home())
        self.redirect_stdio.emit(True)
        if dirname:
            return self.save_all_figures_todir(dirname)

    def save_all_figures_todir(self, dirname):
        """Save all figure in dirname."""
        fignames = []
        for thumbnail in self._thumbnails:
            fig = thumbnail.canvas.fig
            fmt = thumbnail.canvas.fmt
            fext = {'image/png': '.png',
                    'image/jpeg': '.jpg',
                    'image/svg+xml': '.svg'}[fmt]

            figname = get_unique_figname(dirname, 'Figure', fext)
            save_figure_tofile(fig, fmt, figname)
            fignames.append(figname)
        return fignames

    def save_current_figure_as(self):
        """Save the currently selected figure."""
        if self.current_thumbnail is not None:
            self.save_figure_as(self.current_thumbnail.canvas.fig,
                                self.current_thumbnail.canvas.fmt)

    def save_figure_as(self, fig, fmt):
        """Save the figure to a file."""
        fext, ffilt = {
            'image/png': ('.png', 'PNG (*.png)'),
            'image/jpeg': ('.jpg', 'JPEG (*.jpg;*.jpeg;*.jpe;*.jfif)'),
            'image/svg+xml': ('.svg', 'SVG (*.svg);;PNG (*.png)')}[fmt]

        figname = get_unique_figname(getcwd_or_home(), 'Figure', fext)

        self.redirect_stdio.emit(False)
        fname, fext = getsavefilename(
            parent=self.parent(), caption='Save Figure',
            basedir=figname, filters=ffilt,
            selectedfilter='', options=None)
        self.redirect_stdio.emit(True)

        if fname:
            save_figure_tofile(fig, fmt, fname)

    # ---- Thumbails Handlers
    def _calculate_figure_canvas_width(self, thumbnail):
        """
        Calculate the witdh the thumbnail's figure canvas need to have for the
        thumbnail to fit the scrollarea.
        """
        extra_padding = 10 if sys.platform == 'darwin' else 0
        figure_canvas_width = (
            self.scrollarea.width() -
            2 * self.lineWidth() -
            self.scrollarea.viewportMargins().left() -
            self.scrollarea.viewportMargins().right() -
            thumbnail.savefig_btn.width() -
            thumbnail.layout().spacing() - extra_padding
            )
        if is_dark_interface():
            # This is required to take into account some hard-coded padding
            # and margin in qdarkstyle.
            figure_canvas_width = figure_canvas_width - 6
        return figure_canvas_width

    def _setup_thumbnail_size(self, thumbnail):
        """
        Scale the thumbnail's canvas size so that it fits the thumbnail
        scrollbar's width.
        """
        max_canvas_size = self._calculate_figure_canvas_width(thumbnail)
        thumbnail.scale_canvas_size(max_canvas_size)

    def _update_thumbnail_size(self):
        """
        Update the thumbnails size so that their width fit that of
        the scrollarea.
        """
        # NOTE: We hide temporarily the thumbnails to prevent a repaint of
        # each thumbnail as soon as their size is updated in the loop, which
        # causes some flickering of the thumbnail scrollbar resizing animation.
        # Once the size of all the thumbnails has been updated, we show them
        # back so that they are repainted all at once instead of one after the
        # other. This is just a trick to make the resizing animation of the
        # thumbnail scrollbar look smoother.
        self.view.hide()
        for thumbnail in self._thumbnails:
            self._setup_thumbnail_size(thumbnail)
        self.view.show()

    def add_thumbnail(self, fig, fmt):
        """
        Add a new thumbnail to that thumbnail scrollbar.
        """
        thumbnail = FigureThumbnail(
            parent=self, background_color=self.background_color)
        thumbnail.canvas.load_figure(fig, fmt)
        thumbnail.sig_canvas_clicked.connect(self.set_current_thumbnail)
        thumbnail.sig_remove_figure.connect(self.remove_thumbnail)
        thumbnail.sig_save_figure.connect(self.save_figure_as)
        self._thumbnails.append(thumbnail)

        self.scene.setRowStretch(self.scene.rowCount() - 1, 0)
        self.scene.addWidget(thumbnail, self.scene.rowCount() - 1, 0)
        self.scene.setRowStretch(self.scene.rowCount(), 100)
        self.set_current_thumbnail(thumbnail)

        thumbnail.show()
        self._setup_thumbnail_size(thumbnail)

    def remove_current_thumbnail(self):
        """Remove the currently selected thumbnail."""
        if self.current_thumbnail is not None:
            self.remove_thumbnail(self.current_thumbnail)

    def remove_all_thumbnails(self):
        """Remove all thumbnails."""
        for thumbnail in self._thumbnails:
            self.layout().removeWidget(thumbnail)
            thumbnail.sig_canvas_clicked.disconnect()
            thumbnail.sig_remove_figure.disconnect()
            thumbnail.sig_save_figure.disconnect()
            thumbnail.setParent(None)
        self._thumbnails = []
        self.current_thumbnail = None
        self.figure_viewer.figcanvas.clear_canvas()

    def remove_thumbnail(self, thumbnail):
        """Remove thumbnail."""
        if thumbnail in self._thumbnails:
            index = self._thumbnails.index(thumbnail)
            self._thumbnails.remove(thumbnail)
        self.layout().removeWidget(thumbnail)
        thumbnail.setParent(None)
        thumbnail.sig_canvas_clicked.disconnect()
        thumbnail.sig_remove_figure.disconnect()
        thumbnail.sig_save_figure.disconnect()

        # Select a new thumbnail if any :
        if thumbnail == self.current_thumbnail:
            if len(self._thumbnails) > 0:
                self.set_current_index(min(index, len(self._thumbnails)-1))
            else:
                self.current_thumbnail = None
                self.figure_viewer.figcanvas.clear_canvas()

    def set_current_index(self, index):
        """Set the currently selected thumbnail by its index."""
        self.set_current_thumbnail(self._thumbnails[index])

    def get_current_index(self):
        """Return the index of the currently selected thumbnail."""
        try:
            return self._thumbnails.index(self.current_thumbnail)
        except ValueError:
            return -1

    def set_current_thumbnail(self, thumbnail):
        """Set the currently selected thumbnail."""
        self.current_thumbnail = thumbnail
        self.figure_viewer.load_figure(
                thumbnail.canvas.fig, thumbnail.canvas.fmt)
        for thumbnail in self._thumbnails:
            thumbnail.highlight_canvas(thumbnail == self.current_thumbnail)

    def go_previous_thumbnail(self):
        """Select the thumbnail previous to the currently selected one."""
        if self.current_thumbnail is not None:
            index = self._thumbnails.index(self.current_thumbnail) - 1
            index = index if index >= 0 else len(self._thumbnails) - 1
            self.set_current_index(index)
            self.scroll_to_item(index)

    def go_next_thumbnail(self):
        """Select thumbnail next to the currently selected one."""
        if self.current_thumbnail is not None:
            index = self._thumbnails.index(self.current_thumbnail) + 1
            index = 0 if index >= len(self._thumbnails) else index
            self.set_current_index(index)
            self.scroll_to_item(index)

    def scroll_to_item(self, index):
        """Scroll to the selected item of ThumbnailScrollBar."""
        spacing_between_items = self.scene.verticalSpacing()
        height_view = self.scrollarea.viewport().height()
        height_item = self.scene.itemAt(index).sizeHint().height()
        height_view_excluding_item = max(0, height_view - height_item)

        height_of_top_items = spacing_between_items
        for i in range(index):
            item = self.scene.itemAt(i)
            height_of_top_items += item.sizeHint().height()
            height_of_top_items += spacing_between_items

        pos_scroll = height_of_top_items - height_view_excluding_item // 2

        vsb = self.scrollarea.verticalScrollBar()
        vsb.setValue(pos_scroll)

    # ---- ScrollBar Handlers
    def go_up(self):
        """Scroll the scrollbar of the scrollarea up by a single step."""
        vsb = self.scrollarea.verticalScrollBar()
        vsb.setValue(int(vsb.value() - vsb.singleStep()))

    def go_down(self):
        """Scroll the scrollbar of the scrollarea down by a single step."""
        vsb = self.scrollarea.verticalScrollBar()
        vsb.setValue(int(vsb.value() + vsb.singleStep()))


class FigureThumbnail(QWidget):
    """
    A widget that consists of a FigureCanvas, a side toolbar, and a context
    menu that is used to show preview of figures in the ThumbnailScrollBar.
    """
    sig_canvas_clicked = Signal(object)
    sig_remove_figure = Signal(object)
    sig_save_figure = Signal(object, str)

    def __init__(self, parent=None, background_color=None):
        super(FigureThumbnail, self).__init__(parent)
        self.canvas = FigureCanvas(self, background_color=background_color)
        self.canvas.installEventFilter(self)
        self.setup_gui()

    def setup_gui(self):
        """Setup the main layout of the widget."""
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas, 0, 0, Qt.AlignCenter)
        layout.addLayout(self.setup_toolbar(), 0, 1, 2, 1)
        layout.setRowStretch(1, 100)
        layout.setSizeConstraint(layout.SetFixedSize)

    def setup_toolbar(self):
        """Setup the toolbar."""
        self.savefig_btn = create_toolbutton(
            self, icon=ima.icon('filesave'),
            tip=_("Save Image As..."),
            triggered=self.emit_save_figure)
        self.delfig_btn = create_toolbutton(
            self, icon=ima.icon('editclear'),
            tip=_("Delete image"),
            triggered=self.emit_remove_figure)

        toolbar = QVBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(1)
        toolbar.addWidget(self.savefig_btn)
        toolbar.addWidget(self.delfig_btn)
        toolbar.addStretch(2)

        return toolbar

    def highlight_canvas(self, highlight):
        """
        Set a colored frame around the FigureCanvas if highlight is True.
        """
        colorname = self.canvas.palette().highlight().color().name()
        if highlight:
            # Highlighted figure is not clear in dark mode with blue color.
            # See spyder-ide/spyder#10255.
            if is_dark_interface():
                self.canvas.setStyleSheet(
                        "FigureCanvas{border: 2px solid %s;}" % "#148CD2")
            else:
                self.canvas.setStyleSheet(
                        "FigureCanvas{border: 2px solid %s;}" % colorname)
        else:
            self.canvas.setStyleSheet("FigureCanvas{}")

    def scale_canvas_size(self, max_canvas_size):
        """
        Scale this thumbnail canvas size, while respecting its associated
        figure dimension ratio.
        """
        fwidth = self.canvas.fwidth
        fheight = self.canvas.fheight
        if fwidth / fheight > 1:
            canvas_width = max_canvas_size
            canvas_height = canvas_width / fwidth * fheight
        else:
            canvas_height = max_canvas_size
            canvas_width = canvas_height / fheight * fwidth
        self.canvas.setFixedSize(int(canvas_width), int(canvas_height))
        self.layout().setColumnMinimumWidth(0, max_canvas_size)

    def eventFilter(self, widget, event):
        """
        A filter that is used to send a signal when the figure canvas is
        clicked.
        """
        if event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.sig_canvas_clicked.emit(self)
        return super(FigureThumbnail, self).eventFilter(widget, event)

    def emit_save_figure(self):
        """
        Emit a signal when the toolbutton to save the figure is clicked.
        """
        self.sig_save_figure.emit(self.canvas.fig, self.canvas.fmt)

    def emit_remove_figure(self):
        """
        Emit a signal when the toolbutton to close the figure is clicked.
        """
        self.sig_remove_figure.emit(self)


class FigureCanvas(QFrame):
    """
    A basic widget on which can be painted a custom png, jpg, or svg image.
    """

    def __init__(self, parent=None, background_color=None):
        super(FigureCanvas, self).__init__(parent)
        self.setLineWidth(2)
        self.setMidLineWidth(1)
        self.setObjectName("figcanvas")
        self.setStyleSheet(
            "#figcanvas {background-color:" + str(background_color) + "}")

        self.fig = None
        self.fmt = None
        self.fwidth, self.fheight = 200, 200
        self._blink_flag = False

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu_requested)

    def context_menu_requested(self, event):
        """Popup context menu."""
        if self.fig:
            pos = QPoint(event.x(), event.y())
            context_menu = QMenu(self)
            context_menu.addAction(ima.icon('editcopy'), "Copy Image",
                                   self.copy_figure,
                                   QKeySequence(
                                       get_shortcut('plots', 'copy')))
            context_menu.popup(self.mapToGlobal(pos))

    @Slot()
    def copy_figure(self):
        """Copy figure to clipboard."""
        if self.fmt in ['image/png', 'image/jpeg']:
            qpixmap = QPixmap()
            qpixmap.loadFromData(self.fig, self.fmt.upper())
            QApplication.clipboard().setImage(qpixmap.toImage())
        elif self.fmt == 'image/svg+xml':
            svg_to_clipboard(self.fig)
        else:
            return

        self.blink_figure()

    def blink_figure(self):
        """Blink figure once."""
        if self.fig:
            self._blink_flag = not self._blink_flag
            self.repaint()
            if self._blink_flag:
                timer = QTimer()
                timer.singleShot(40, self.blink_figure)

    def clear_canvas(self):
        """Clear the figure that was painted on the widget."""
        self.fig = None
        self.fmt = None
        self._qpix_scaled = None
        self.repaint()

    def load_figure(self, fig, fmt):
        """
        Load the figure from a png, jpg, or svg image, convert it in
        a QPixmap, and force a repaint of the widget.
        """
        self.fig = fig
        self.fmt = fmt

        if fmt in ['image/png', 'image/jpeg']:
            self._qpix_orig = QPixmap()
            self._qpix_orig.loadFromData(fig, fmt.upper())
        elif fmt == 'image/svg+xml':
            self._qpix_orig = QPixmap(svg_to_image(fig))

        self._qpix_scaled = self._qpix_orig
        self.fwidth = self._qpix_orig.width()
        self.fheight = self._qpix_orig.height()

    def paintEvent(self, event):
        """Qt method override to paint a custom image on the Widget."""
        super(FigureCanvas, self).paintEvent(event)
        # Prepare the rect on which the image is going to be painted.
        fw = self.frameWidth()
        rect = QRect(0 + fw, 0 + fw,
                     self.size().width() - 2 * fw,
                     self.size().height() - 2 * fw)

        if self.fig is None or self._blink_flag:
            return

        # Prepare the scaled qpixmap to paint on the widget.
        if (self._qpix_scaled is None or
                self._qpix_scaled.size().width() != rect.width()):
            if self.fmt in ['image/png', 'image/jpeg']:
                self._qpix_scaled = self._qpix_orig.scaledToWidth(
                    rect.width(), mode=Qt.SmoothTransformation)
            elif self.fmt == 'image/svg+xml':
                self._qpix_scaled = QPixmap(svg_to_image(
                    self.fig, rect.size()))

        if self._qpix_scaled is not None:
            # Paint the image on the widget.
            qp = QPainter()
            qp.begin(self)
            qp.drawPixmap(rect, self._qpix_scaled)
            qp.end()
