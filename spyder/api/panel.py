# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Copyright © <2013-2016> <Colin Duquesnoy and others, see pyqode/AUTHORS.rst>
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
This module contains the panel API.
Adapted from https://github.com/pyQode/pyqode.core/blob/master/pyqode/core/api/panel.py
"""
from qtpy.QtWidgets import QWidget, QApplication
from qtpy.QtGui import QBrush, QColor, QPen, QPainter
from qtpy.QtCore import Qt, QPoint, QRect

from spyder.api.editorextension import EditorExtension
from spyder.config.base import debug_print


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
        :type editor: spyder.widgets.sourcecode.CodeEditor
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
        """Fills the panel background using QPalette."""
        if self.isVisible() and self.position != self.Position.FLOATING:
            # fill background
            self._background_brush = QBrush(QColor(
                self.editor.sideareas_color))
            self._foreground_pen = QPen(QColor(
                self.palette().windowText().color()))
            painter = QPainter(self)
            painter.fillRect(event.rect(), self._background_brush)

    def setVisible(self, visible):
        """
        Shows/Hides the panel.

        Automatically call PanelsManager.refresh_panels.

        :param visible: Visible state
        """
        debug_print('{} visibility changed'.format(self.name))
        super(Panel, self).setVisible(visible)
        if self.editor:
            self.editor.panels.refresh()

    def geometry(self):
        """Return geometry dimentions for floating Panels.

        Note: If None is returned It'll use editor contentsRect dimentions.

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

        self.setGeometry(QRect(x+x0, y+y0, width, height))
