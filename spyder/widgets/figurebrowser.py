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
import os.path as osp

# ---- Third library imports
from qtconsole.svg import svg_to_image
from qtpy.compat import getsavefilename, getexistingdirectory
from qtpy.QtCore import Qt, Signal, QRect, QEvent
from qtpy.QtGui import QPixmap, QPainter
from qtpy.QtWidgets import (QApplication, QHBoxLayout, QMenu,
                            QVBoxLayout, QWidget, QGridLayout, QFrame,
                            QScrollArea, QPushButton, QScrollBar, QSizePolicy,
                            QSpinBox, QSplitter, QStyleOptionSlider, QStyle)

# ---- Local library imports
from spyder.config.base import _
from spyder.py3compat import is_unicode, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton, create_plugin_layout,
                                    MENU_SEPARATOR)
from spyder.utils.misc import getcwd_or_home


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

    def __init__(self, parent, options_button=None, plugin_actions=[]):
        super(FigureBrowser, self).__init__(parent)

        self.shellwidget = None
        self.is_visible = True
        self.figviewer = None
        self.setup_in_progress = False

        # Options :
        self.mute_inline_plotting = None
        self.show_plot_outline = None

        # Option actions :
        self.mute_inline_action = None
        self.show_plot_outline_action = None

        self.options_button = options_button
        self.plugin_actions = plugin_actions

    def setup(self, mute_inline_plotting=None, show_plot_outline=None):
        """Setup the figure browser with provided settings."""
        assert self.shellwidget is not None

        self.mute_inline_plotting = mute_inline_plotting
        self.show_plot_outline = show_plot_outline

        if self.figviewer is not None:
            self.mute_inline_action.setChecked(mute_inline_plotting)
            self.show_plot_outline_action.setChecked(show_plot_outline)
            return

        self.figviewer = FigureViewer()
        self.figviewer.setStyleSheet("FigureViewer{"
                                     "border: 1px solid lightgrey;"
                                     "border-top-width: 0px;"
                                     "border-bottom-width: 0px;"
                                     "border-left-width: 0px;"
                                     "}")
        self.thumbnails_sb = ThumbnailScrollBar(self.figviewer)

        # Option actions :
        self.setup_option_actions(mute_inline_plotting, show_plot_outline)

        # Create the layout :
        main_widget = QSplitter()
        main_widget.addWidget(self.figviewer)
        main_widget.addWidget(self.thumbnails_sb)
        main_widget.setFrameStyle(QScrollArea().frameStyle())

        self.tools_layout = QHBoxLayout()
        toolbar = self.setup_toolbar()
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
                triggered=self.thumbnails_sb.save_current_figure_as)

        saveall_btn = create_toolbutton(
                self, icon=ima.icon('save_all'),
                tip=_("Save All Images..."),
                triggered=self.thumbnails_sb.save_all_figures_as)

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
                tip=_("Previous Figure"),
                triggered=self.go_previous_thumbnail)

        gonext_btn = create_toolbutton(
                self, icon=ima.icon('ArrowForward'),
                tip=_("Next Figure"),
                triggered=self.go_next_thumbnail)

        vsep2 = QFrame()
        vsep2.setFrameStyle(53)

        zoom_out_btn = create_toolbutton(
                self, icon=ima.icon('zoom_out'),
                tip=_("Zoom out (Ctrl + mouse-wheel-down)"),
                triggered=self.zoom_out)

        zoom_in_btn = create_toolbutton(
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
        layout.addWidget(zoom_out_btn)
        layout.addWidget(zoom_in_btn)
        layout.addWidget(self.zoom_disp)

        return [savefig_btn, saveall_btn, closefig_btn, closeall_btn, vsep1,
                goback_btn, gonext_btn, vsep2, zoom_pan]

    def setup_option_actions(self, mute_inline_plotting, show_plot_outline):
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

        self.actions = [self.mute_inline_action, self.show_plot_outline_action]
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
        """
        Zoom the figure in by a single step in the figure viewer.
        """
        self.figviewer.zoom_in()

    def zoom_out(self):
        """
        Zoom the figure out by a single step in the figure viewer.
        """
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

    def close_figure(self):
        """Close the currently selected figure in the thumbnail scrollbar."""
        self.thumbnails_sb.remove_current_thumbnail()

    def close_all_figures(self):
        """Close all the figures in the thumbnail scrollbar."""
        self.thumbnails_sb.remove_all_thumbnails()


class FigureViewer(QScrollArea):
    """
    A scrollarea that displays a single FigureCanvas with zooming and panning
    capability with CTRL + Mouse_wheel and Left-press mouse button event.
    """

    sig_zoom_changed = Signal(float)

    def __init__(self, parent=None):
        super(FigureViewer, self).__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.viewport().setStyleSheet("background-color: white")
        self.setFrameStyle(0)

        self._scalefactor = 0
        self._scalestep = 1.2
        self._sfmax = 10
        self._sfmin = -10

        # An internal flag that tracks when the figure is being panned.
        self._ispanning = False

        self.setup_figcanvas()

    def setup_figcanvas(self):
        """Setup the FigureCanvas."""
        self.figcanvas = FigureCanvas()
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
        if event.type() == QEvent.Wheel:
            modifiers = QApplication.keyboardModifiers()
            if modifiers == Qt.ControlModifier:
                if event.angleDelta().y() > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
                return True
            else:
                return False

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
            self.sig_zoom_changed.emit(self.get_scaling())

    def zoom_out(self):
        """Scale the image down by one scale step."""
        if self._scalefactor >= self._sfmin:
            self._scalefactor -= 1
            self.scale_image()
            self._adjust_scrollbar(1/self._scalestep)
            self.sig_zoom_changed.emit(self.get_scaling())

    def scale_image(self):
        """Scale the image size."""
        new_width = int(self.figcanvas.fwidth *
                        self._scalestep ** self._scalefactor)
        new_height = int(self.figcanvas.fheight *
                         self._scalestep ** self._scalefactor)
        self.figcanvas.setFixedSize(new_width, new_height)

    def get_scaling(self):
        """Get the current scaling of the figure in percent."""
        return self._scalestep**self._scalefactor*100

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

    def __init__(self, figure_viewer, parent=None):
        super(ThumbnailScrollBar, self).__init__(parent)
        self._thumbnails = []
        self.current_thumbnail = None
        self.set_figureviewer(figure_viewer)
        self.setup_gui()

    def setup_gui(self):
        """Setup the main layout of the widget."""
        scrollarea = self.setup_scrollarea()
        up_btn, down_btn = self.setup_arrow_buttons()

        self.setFixedWidth(135)
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
        self.scene.setColumnStretch(0, 100)
        self.scene.setColumnStretch(2, 100)

        self.scrollarea = QScrollArea()
        self.scrollarea.setWidget(self.view)
        self.scrollarea.setWidgetResizable(True)
        self.scrollarea.setFrameStyle(0)
        self.scrollarea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollarea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollarea.setSizePolicy(QSizePolicy(QSizePolicy.Ignored,
                                                  QSizePolicy.Preferred))

        # Set the vertical scrollbar explicitely :
        # This is required to avoid a "RuntimeError: no access to protected
        # functions or signals for objects not created from Python" in Linux.
        self.scrollarea.setVerticalScrollBar(QScrollBar())

        return self.scrollarea

    def setup_arrow_buttons(self):
        """
        Setup the up and down arrow buttons that are placed at the top and
        bottom of the scrollarea.
        """
        # Get the height of the up/down arrow of the default vertical
        # scrollbar :
        vsb = self.scrollarea.verticalScrollBar()
        style = vsb.style()
        opt = QStyleOptionSlider()
        vsb.initStyleOption(opt)
        vsb_up_arrow = style.subControlRect(
                QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarAddLine, self)

        # Setup the up and down arrow button :
        up_btn = up_btn = QPushButton(icon=ima.icon('last_edit_location'))
        up_btn.setFlat(True)
        up_btn.setFixedHeight(vsb_up_arrow.size().height())
        up_btn.clicked.connect(self.go_up)

        down_btn = QPushButton(icon=ima.icon('folding.arrow_down_on'))
        down_btn.setFlat(True)
        down_btn.setFixedHeight(vsb_up_arrow.size().height())
        down_btn.clicked.connect(self.go_down)

        return up_btn, down_btn

    def set_figureviewer(self, figure_viewer):
        """Set the bamespace for the FigureViewer."""
        self.figure_viewer = figure_viewer

    # ---- Save Figure
    def save_all_figures_as(self):
        """Save all the figures to a file."""
        self.redirect_stdio.emit(False)
        dirname = getexistingdirectory(self, caption='Save all figures',
                                       basedir=getcwd_or_home())
        self.redirect_stdio.emit(True)
        if dirname:
            self.save_all_figures_todir(dirname)

    def save_all_figures_todir(self, dirname):
        """Save all figure in dirname."""
        for thumbnail in self._thumbnails:
            fig = thumbnail.canvas.fig
            fmt = thumbnail.canvas.fmt
            fext = {'image/png': '.png',
                    'image/jpeg': '.jpg',
                    'image/svg+xml': '.svg'}[fmt]

            figname = get_unique_figname(dirname, 'Figure', fext)
            save_figure_tofile(fig, fmt, figname)

    def save_current_figure_as(self):
        """Save the currently selected figure."""
        if self.current_thumbnail is None:
            return

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
    def add_thumbnail(self, fig, fmt):
        thumbnail = FigureThumbnail()
        thumbnail.canvas.load_figure(fig, fmt)

        # Scale the thumbnail size, while respecting the figure
        # dimension ratio.
        fwidth = thumbnail.canvas.fwidth
        fheight = thumbnail.canvas.fheight

        max_length = 100
        if fwidth/fheight > 1:
            canvas_width = max_length
            canvas_height = canvas_width / fwidth * fheight
        else:
            canvas_height = max_length
            canvas_width = canvas_height / fheight * fwidth
        thumbnail.canvas.setFixedSize(canvas_width, canvas_height)

        thumbnail.sig_canvas_clicked.connect(self.set_current_thumbnail)
        thumbnail.sig_remove_figure.connect(self.remove_thumbnail)
        thumbnail.sig_save_figure.connect(self.save_figure_as)
        self._thumbnails.append(thumbnail)

        self.scene.setRowStretch(self.scene.rowCount()-1, 0)
        self.scene.addWidget(thumbnail, self.scene.rowCount()-1, 1)
        self.scene.setRowStretch(self.scene.rowCount(), 100)
        self.set_current_thumbnail(thumbnail)

    def remove_current_thumbnail(self):
        """Remove the currently selected thumbnail."""
        if self.current_thumbnail is not None:
            self.remove_thumbnail(self.current_thumbnail)

    def remove_all_thumbnails(self):
        """Remove all thumbnails."""
        for thumbnail in self._thumbnails:
            self.layout().removeWidget(thumbnail)
            thumbnail.deleteLater()
        self._thumbnails = []
        self.current_thumbnail = None
        self.figure_viewer.figcanvas.clear_canvas()

    def remove_thumbnail(self, thumbnail):
        """Remove thumbnail."""
        if thumbnail in self._thumbnails:
            index = self._thumbnails.index(thumbnail)
            self._thumbnails.remove(thumbnail)
        self.layout().removeWidget(thumbnail)
        thumbnail.deleteLater()

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

    def go_next_thumbnail(self):
        """Select thumbnail next to the currently selected one."""
        if self.current_thumbnail is not None:
            index = self._thumbnails.index(self.current_thumbnail) + 1
            index = 0 if index >= len(self._thumbnails) else index
            self.set_current_index(index)

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

    def __init__(self, parent=None):
        super(FigureThumbnail, self).__init__(parent)
        self.canvas = FigureCanvas(self)
        self.canvas.installEventFilter(self)
        self.setup_gui()

    def setup_gui(self):
        """Setup the main layout of the widget."""
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas, 0, 1)
        layout.addLayout(self.setup_toolbar(), 0, 3, 2, 1)

        layout.setColumnStretch(0, 100)
        layout.setColumnStretch(2, 100)
        layout.setRowStretch(1, 100)

    def setup_toolbar(self):
        """Setup the toolbar."""
        savefig_btn = create_toolbutton(
                self, icon=ima.icon('filesave'),
                tip=_("Save Image As..."),
                triggered=self.emit_save_figure)
        delfig_btn = create_toolbutton(
                self, icon=ima.icon('editclear'),
                tip=_("Delete image"),
                triggered=self.emit_remove_figure)

        toolbar = QVBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(1)
        toolbar.addWidget(savefig_btn)
        toolbar.addWidget(delfig_btn)
        toolbar.addStretch(2)

        return toolbar

    def highlight_canvas(self, highlight):
        """
        Set a colored frame around the FigureCanvas if highlight is True.
        """
        colorname = self.canvas.palette().highlight().color().name()
        if highlight:
            self.canvas.setStyleSheet(
                    "FigureCanvas{border: 1px solid %s;}" % colorname)
        else:
            self.canvas.setStyleSheet("FigureCanvas{}")

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

    def __init__(self, parent=None):
        super(FigureCanvas, self).__init__(parent)
        self.setLineWidth(2)
        self.setMidLineWidth(1)
        self.setStyleSheet("background-color: white")

        self.fig = None
        self.fmt = None
        self.fwidth, self.fheight = 200, 200

    def clear_canvas(self):
        """Clear the figure that was painted on the widget."""
        self.fig = None
        self.fmt = None
        self._qpix_buffer = []
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

        self._qpix_buffer = [self._qpix_orig]
        self.fwidth = self._qpix_orig.width()
        self.fheight = self._qpix_orig.height()

    def paintEvent(self, event):
        """Qt method override to paint a custom image on the Widget."""
        super(FigureCanvas, self).paintEvent(event)
        # Prepare the rect on which the image is going to be painted :
        fw = self.frameWidth()
        rect = QRect(0 + fw, 0 + fw,
                     self.size().width() - 2 * fw,
                     self.size().height() - 2 * fw)

        if self.fig is None:
            return

        # Check/update the qpixmap buffer :
        qpix2paint = None
        for qpix in self._qpix_buffer:
            if qpix.size().width() == rect.width():
                qpix2paint = qpix
                break
        else:
            if self.fmt in ['image/png', 'image/jpeg']:
                qpix2paint = self._qpix_orig.scaledToWidth(
                    rect.width(), mode=Qt.SmoothTransformation)
            elif self.fmt == 'image/svg+xml':
                qpix2paint = QPixmap(svg_to_image(self.fig, rect.size()))
            self._qpix_buffer.append(qpix2paint)

        if qpix2paint is not None:
            # Paint the image on the widget :
            qp = QPainter()
            qp.begin(self)
            qp.drawPixmap(rect, qpix2paint)
            qp.end()
