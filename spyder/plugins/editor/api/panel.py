# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
This module contains the panel API.

Adapted from pyqode/core/api/panel.py of the
`PyQode project <https://github.com/pyQode/pyQode>`_.
Original file:
<https://github.com/pyQode/pyqode.core/blob/master/pyqode/core/api/panel.py>
"""

# Standard library imports
from math import ceil
import logging

# Third party imports
from qtpy.QtWidgets import QWidget, QApplication
from qtpy.QtGui import QBrush, QColor, QPen, QPainter
from qtpy.QtCore import Qt, QRect

# Local imports
from spyder.plugins.editor.api.editorextension import EditorExtension
from spyder.plugins.outlineexplorer.api import is_cell_header

logger = logging.getLogger(__name__)


class Panel(QWidget, EditorExtension):
    """
    Base class for editor panels.

    A panel is a editor extension and a QWidget.

    .. note:: Use enabled to disable panel actions and setVisible to change the
        visibility of the panel.
    """
    class Position(object):
        """Enumerates the possible panel positions"""
        # Top margin
        TOP = 0
        # Left margin
        LEFT = 1
        # Right margin
        RIGHT = 2
        # Bottom margin
        BOTTOM = 3
        # Floating panel
        FLOATING = 4

        @classmethod
        def iterable(cls):
            """ Returns possible positions as an iterable (list) """
            return [cls.TOP, cls.LEFT, cls.RIGHT, cls.BOTTOM]

    @property
    def scrollable(self):
        """
        A scrollable panel will follow the editor's scroll-bars.

        Left and right panels follow the vertical scrollbar. Top and bottom
        panels follow the horizontal scrollbar.

        :type: bool
        """
        return self._scrollable

    @scrollable.setter
    def scrollable(self, value):
        self._scrollable = value

    def __init__(self, dynamic=False):
        EditorExtension.__init__(self)
        QWidget.__init__(self)
        # Specifies whether the panel is dynamic. A dynamic panel is a panel
        # that will be shown/hidden depending on the context.
        # Dynamic panel should not appear in any GUI menu
        self.dynamic = dynamic
        # Panel order into the zone it is installed to. This value is
        # automatically set when installing the panel but it can be changed
        # later (negative values can also be used).
        self.order_in_zone = -1
        self._scrollable = False
        self._background_brush = None
        self.linecell_color = QColor(Qt.darkGray)
        self._foreground_pen = None
        # Position in the editor (top, left, right, bottom)
        self.position = -1

    def on_install(self, editor):
        """
        Extends :meth:`spyder.api.EditorExtension.on_install` method to set the
        editor instance as the parent widget.

        .. warning:: Don't forget to call **super** if you override this
            method!

        :param editor: editor instance
        :type editor: spyder.plugins.editor.widgets.codeeditor.CodeEditor
        """
        EditorExtension.on_install(self, editor)
        self.setParent(editor)
        self.setPalette(QApplication.instance().palette())
        self.setFont(QApplication.instance().font())
        self.editor.panels.refresh()
        self._background_brush = QBrush(QColor(
            self.palette().window().color()))
        self._foreground_pen = QPen(QColor(
            self.palette().windowText().color()))

        if self.position == self.Position.FLOATING:
            self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        """
        Fill the panel background using QPalette.

        Notes
        -----
        Please remember to extend this method in the child class to
        paint the panel's desired information.
        """
        if self.isVisible() and self.position != self.Position.FLOATING:
            # fill background
            self._background_brush = QBrush(QColor(
                self.editor.sideareas_color))
            self._foreground_pen = QPen(QColor(
                self.palette().windowText().color()))
            painter = QPainter(self)
            painter.fillRect(event.rect(), self._background_brush)
        else:
            logger.debug(f'paintEvent method must be defined in {self}')

    def paint_cell(self, painter):
        """Paint cell dividers in the visible region if needed."""
        for top_position, line_number, block in self.editor.visible_blocks:
            if (
                is_cell_header(block)
                and (self.position in [self.Position.LEFT, self.Position.RIGHT])
            ):
                pen = painter.pen()
                pen.setStyle(Qt.SolidLine)
                pen.setBrush(self.linecell_color)
                painter.setPen(pen)
                painter.drawLine(0, top_position, self.width(),
                                 top_position)


    def sizeHint(self):
        """
        Return the widget size hint, overriding the Qt method.

        Notes
        -----
        * This size hint will define the QSize of the panel, i.e. it is
          where its width and height are defined.
        * If the size of your panel depends on displayed text, please
          use the LineNumberArea one as reference on how to implement
          this method.
        * If the size is not dependent on displayed text, please use
          the debugger panel as reference.
        * If your panel is in a floating position, please use the
          IndentationGuide one as reference.
        """
        if self.position != self.Position.FLOATING:
            raise NotImplementedError(
                f'sizeHint method must be implemented in {self}')

    def setVisible(self, visible):
        """
        Shows/Hides the panel.

        Automatically call PanelsManager.refresh_panels.

        :param visible: Visible state
        """
        logger.debug('%s visibility changed', self.name)
        super(Panel, self).setVisible(visible)
        if self.editor:
            self.editor.panels.refresh()

    def geometry(self):
        """Return geometry dimensions for floating Panels.

        Note: If None is returned It'll use editor contentsRect dimensions.

        returns: x0, y0, height width.
        """
        return 0, 0, None, None

    def set_geometry(self, crect):
        """Set geometry for floating panels.

        Normally you don't need to override this method, you should override
        `geometry` instead.
        """
        x0, y0, width, height = self.geometry()

        if width is None:
            width = crect.width()
        if height is None:
            height = crect.height()

        # Calculate editor coordinates with their offsets
        offset = self.editor.contentOffset()
        x = self.editor.blockBoundingGeometry(self.editor.firstVisibleBlock())\
            .translated(offset.x(), offset.y()).left() \
            + self.editor.document().documentMargin() \
            + self.editor.panels.margin_size(Panel.Position.LEFT)
        y = crect.top() + self.editor.panels.margin_size(Panel.Position.TOP)

        self.setGeometry(QRect(ceil(x+x0), ceil(y+y0),
                               ceil(width), ceil(height)))
