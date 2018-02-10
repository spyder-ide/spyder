# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Figure browser widget

This is the main widget used in the Figure Explorer plugin
"""


# ---- Standard library imports

import os.path as osp


# ---- Third library imports

from qtpy.compat import getsavefilename, getopenfilenames
from qtpy.QtCore import Qt, Signal, Slot, QRect, QEvent
from qtpy.QtGui import QCursor, QImage, QPixmap, QPainter
from qtpy.QtWidgets import (QApplication, QHBoxLayout, QInputDialog, QMenu,
                            QMessageBox, QToolButton, QVBoxLayout, QWidget,
                            QLabel, QGridLayout, QFrame, QScrollArea,
                            QGraphicsScene, QGraphicsView, QSplitter,
                            QSizePolicy, QSpinBox,QPushButton,
                            QStyleOptionSlider, QStyle, QScrollBar,
                            QCheckBox)


# ---- Local library imports

from spyder.config.base import _
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton, create_plugin_layout)



class ThumbnailScrollBar(QFrame):
    """
    A widget that manages the display of the FigureThumbnails that are
    created when a figure is sent to the IPython console by the kernel and
    that controls what is displayed in the FigureViewer.
    """

    def __init__(self, figure_viewer, parent=None):
        super(ThumbnailScrollBar, self).__init__(parent)
        self._thumbnails = []
        self.set_figureviewer(figure_viewer)
        self.setup_gui()

    def setup_gui(self):
        """Setups the main layout of the widget."""
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
        """Setups the scrollarea that will contain the FigureThumbnails."""
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

        return self.scrollarea

    def setup_arrow_buttons(self):
        """
        Setups the up and down arrow buttons that are placed at the top and
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
        """Sets the bamespace for the FigureViewer."""
        self.figure_viewer = figure_viewer

    # ---- Thumbails Handlers

    def add_thumbnail(self, fig, fmt):
        fig_manager = FigureThumbnail()
        fig_manager.canvas.setFixedSize(100, 75)
        fig_manager.canvas.load_figure(fig, fmt)
        fig_manager.sig_canvas_clicked.connect(self.set_current_thumbnail)
        fig_manager.sig_remove_figure.connect(self.remove_thumbnail)
        self._thumbnails.append(fig_manager)

        self.scene.setRowStretch(self.scene.rowCount()-1, 0)
        self.scene.addWidget(fig_manager, self.scene.rowCount()-1, 1)
        self.scene.setRowStretch(self.scene.rowCount(), 100)
        self.set_current_thumbnail(fig_manager)

    def remove_current_thumbnail(self):
        """Removes the currently selected thumbnail."""
        if self.current_thumbnail is not None:
            self.remove_thumbnail(self.current_thumbnail)

    def remove_all_thumbnails(self):
        """Removes all thumbnails."""
        for thumbnail in self._thumbnails:
            self.layout().removeWidget(thumbnail)
            thumbnail.deleteLater()
        self._thumbnails = []
        self.current_thumbnail = None
        self.figure_viewer.imageCanvas.clear_canvas()

    def remove_thumbnail(self, thumbnail):
        """Removes thumbnail."""
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
                self.figure_viewer.imageCanvas.clear_canvas()

    def set_current_index(self, index):
        """Sets the currently selected thumbnail by its index."""
        self.set_current_thumbnail(self._thumbnails[index])

    def set_current_thumbnail(self, thumbnail):
        """Sets the currently selected thumbnail."""
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
        """Scrolls the scrollbar of the scrollarea up by a single step."""
        vsb = self.scrollarea.verticalScrollBar()
        vsb.setValue(int(vsb.value() - vsb.singleStep()))

    def go_down(self):
        """Scrolls the scrollbar of the scrollarea down by a single step."""
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
        """Setups the main layout of the widget."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.addWidget(self.canvas)
        layout.addLayout(self.setup_toolbar())

    def setup_toolbar(self):
        """Setups the toolbar."""
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
        toolbar.addWidget(savefig_btn)
        toolbar.addWidget(delfig_btn)
        toolbar.addStretch(2)

        return toolbar

    def highlight_canvas(self, highlight):
        """
        Sets a colored frame around the FigureCanvas if highlight is True.
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
        Emits a signal when the toolbutton to save the figure is clicked.
        """
        self.sig_save_figure.emit(self.canvas.fig, self.canvas.fmt)

    def emit_remove_figure(self):
        """
        Emits a signal when the toolbutton to close the figure is clicked.
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
        self.qpix = None
        self._qpix_buffer = []
        self.fwidth, self.fheight = 200, 200

    def clear_canvas(self):
        """Clear the figure that was painted on the widget."""
        self.fig = None
        self.fmt = None
        self.qpix = None
        self._qpix_buffer = []
        self.repaint()

    def load_figure(self, fig, fmt):
        """
        Loads the figure from a png, jpg, or svg image, converts it in
        a QPixmap, and forces a repaint of the widget.
        """
        self.fig = fig
        self.fmt = fmt

        if fmt in ['image/png', 'image/jpeg']:
            qimg = QImage()
            qimg.loadFromData(fig, fmt.upper())
        elif fmt == 'image/svg+xml':
            raise NotImplementedError

        self.qpix = QPixmap(qimg)
        self.fwidth = self.qpix.width()
        self.fheight = self.qpix.height()
        self._qpix_buffer = []
        self.repaint()

    def save_figure_tofile(self, filename):
        raise NotImplementedError

    def paintEvent(self, event):
        """Qt method override to paint a custom image on the Widget."""
        super(FigureCanvas, self).paintEvent(event)
        # Prepare the rect on which the image is going to be painted :

        fw = self.frameWidth()
        rect = QRect(0 + fw, 0 + fw,
                     self.size().width() - 2 * fw,
                     self.size().height() - 2 * fw)

        # Check/update the qpixmap buffer :

        qpix2paint = None
        for qpix in self._qpix_buffer:
            if qpix.size().width() == rect.width():
                qpix2paint = qpix
                break
        else:
            if self.qpix is not None:
                qpix2paint = self.qpix.scaledToWidth(
                    rect.width(), mode=Qt.SmoothTransformation)
                self._qpix_buffer.append(qpix2paint)

        if qpix2paint is not None:
            # Paint the image on the widget :
            qp = QPainter()
            qp.begin(self)
            qp.setRenderHint(QPainter.Antialiasing, True)
            qp.drawPixmap(rect, qpix2paint)
            qp.end()
