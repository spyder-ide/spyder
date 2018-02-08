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
        self._qpix_store = []
        self.fwidth, self.fheight = 200, 200

    def clear_canvas(self):
        """Clear the figure that was painted on the widget."""
        self.fig = None
        self.fmt = None
        self.qpix = None
        self._qpix_store = []
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
        self._qpix_store = []
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

        # Check/update the image buffer :

        qpix2paint = None
        for qpix in self._qpix_store:
            if qpix.size().width() == rect.width():
                qpix2paint = qpix
                break
        else:
            if self.qpix is not None:
                qpix2paint = self.qpix.scaledToWidth(
                    rect.width(), mode=Qt.SmoothTransformation)
                self._qpix_store.append(qpix2paint)

        if qpix2paint is not None:
            # Paint the image on the widget :
            qp = QPainter()
            qp.begin(self)
            qp.setRenderHint(QPainter.Antialiasing, True)
            qp.drawPixmap(rect, qpix2paint)
            qp.end()
