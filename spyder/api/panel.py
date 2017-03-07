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

from spyder.api.mode import Mode
from spyder.config.base import debug_print


class Panel(QWidget, Mode):
    """
    Base class for editor panels.

    A panel is a mode and a QWidget.

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
        Mode.__init__(self)
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
        Extends :meth:`spyder.api.Mode.on_install` method to set the
        editor instance as the parent widget.

        .. warning:: Don't forget to call **super** if you override this
            method!

        :param editor: editor instance
        :type editor: spyder.widgets.sourcecode.CodeEditor
        """
        Mode.on_install(self, editor)
        self.setParent(editor)
        self.setPalette(QApplication.instance().palette())
        self.setFont(QApplication.instance().font())
        self.editor.panels.refresh()
        self._background_brush = QBrush(QColor(
            self.palette().window().color()))
        self._foreground_pen = QPen(QColor(
            self.palette().windowText().color()))

    def paintEvent(self, event):
        """Fills the panel background using QPalette."""
        if self.isVisible():
            # fill background
            self._background_brush = QBrush(QColor(
                self.palette().window().color()))
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
