# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
This module contains the Bookmarks panel
"""
from qtpy.QtCore import QSize, QRect
from qtpy.QtGui import QPainter, QFontMetrics

from spyder.utils import icon_manager as ima
from spyder.api.panel import Panel
from spyder.config.base import debug_print


class BookmarksPanel(Panel):
    """Bookmarks panel for show information about the debugging in process."""

    def __init__(self):
        """Initialize panel."""
        Panel.__init__(self)

        self.setMouseTracking(True)
        self.scrollable = True

        self.line_number_hint = None
        self._current_line_arrow = None
        self.stop = False

        # Diccionary of QIcons to draw in the panel
        self.icons = {'bookmark': ima.icon('bookmark'),
                      'transparent': ima.icon('bookmark_transparent'),
                      'multiple': ima.icon('bookmark_multiple')}

    def set_current_line_arrow(self, n):
        self._current_line_arrow = n

    def sizeHint(self):
        """Override Qt method.

        Returns the widget size hint (based on the editor font size).
        """
        fm = QFontMetrics(self.editor.font())
        size_hint = QSize(fm.height(), fm.height())
        if size_hint.width() > 16:
            size_hint.setWidth(16)
        return size_hint

    def _draw_bookmark_icon(self, top, painter, icon_name):
        """Draw the given bookmark pixmap.

        Args:
            top (int): top of the line to draw the breakpoint icon.
            painter (QPainter)
            icon_name (srt): key of icon to draw (see: self.icons)
        """
        rect = QRect(0, top, self.sizeHint().width(),
                     self.sizeHint().height())
        try:
            icon = self.icons[icon_name]
        except KeyError as e:
            debug_print("Bookmark icon doen't exist, {}".format(e))
        else:
            icon.paint(painter, rect)

    def paintEvent(self, event):
        """Override Qt method.

        Paint breakpoints icons.
        """
        super(BookmarksPanel, self).paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.editor.sideareas_color)

        for top, line_number, block in self.editor.visible_blocks:
            if self.line_number_hint == line_number:
                self._draw_bookmark_icon(top, painter, 'transparent')

            data = block.userData()
            if data is None or not data.bookmarks:
                continue

            if data.bookmarks is None:
                self._draw_bookmark_icon(top, painter, 'transparent')
            elif len(data.bookmarks) > 1:
                self._draw_bookmark_icon(top, painter, 'multiple')
            else:
                self._draw_bookmark_icon(top, painter, 'bookmark')

    def mousePressEvent(self, event):
        """Override Qt method

        Add/remove breakpoints by single click.
        """
        line_number = self.editor.get_linenumber_from_mouse_event(event)
        self.editor.add_next_bookmark(line_number-1)

    def mouseMoveEvent(self, event):
        """Override Qt method.

        Draw semitransparent bookmark hint.
        """
        self.line_number_hint = self.editor.get_linenumber_from_mouse_event(
            event)
        self.update()

    def leaveEvent(self, event):
        """Override Qt method.

        Remove semitransparent breakpoint hint
        """
        self.line_number_hint = None
        self.update()

    def wheelEvent(self, event):
        """Override Qt method.

        Needed for scroll down the editor when scrolling over the panel.
        """
        self.editor.wheelEvent(event)

    def on_state_changed(self, state):
        """Change visibility and connect/disconnect signal.

        Args:
            state (bool): Activate/deactivate.
        """
        if state:
            self.editor.sig_bookmarks_changed.connect(self.repaint)
        else:
            self.editor.sig_bookmarks_changed.disconnect(self.repaint)
