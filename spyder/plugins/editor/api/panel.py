# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
API for editor panels.
"""

# Standard library imports
from __future__ import annotations
from enum import Enum
from math import ceil
import logging
from typing import TYPE_CHECKING

# Third party imports
from qtpy.QtCore import Qt, QRect, QSize
from qtpy.QtGui import QBrush, QColor, QPen, QPainter
from qtpy.QtWidgets import QWidget, QApplication

# Local imports
from spyder.plugins.editor.api.editorextension import EditorExtension
from spyder.plugins.outlineexplorer.api import is_cell_header


if TYPE_CHECKING:
    from spyder.plugins.editor.widgets.codeeditor import CodeEditor


logger = logging.getLogger(__name__)


class PanelPosition(Enum):
    """Enumerates the possible panel positions"""
    TOP = 0
    """Top margin"""

    LEFT = 1
    """Left margin"""

    RIGHT = 2
    """Right margin"""

    BOTTOM = 3
    """Bottom margin"""

    FLOATING = 4
    """Floating panel"""


class Panel(QWidget, EditorExtension):
    """
    Base class for editor panels.

    A panel is an editor extension and a QWidget.
    """

    def __init__(self):
        EditorExtension.__init__(self)
        QWidget.__init__(self)

        self.position: PanelPosition | None = None
        """Position in the editor (top, left, right, bottom)."""

        self.order_in_zone: int = -1
        """Panel order into the zone it is installed into."""

        self.scrollable: bool = False
        """
        A scrollable panel will follow the editor's scroll-bars.

        Left and right panels follow the vertical scrollbar. Top and bottom
        panels follow the horizontal scrollbar.
        """

        # Private attributes
        self._background_brush = None
        self._linecell_color = QColor(Qt.darkGray)  # TODO: Use theme color
        self._foreground_pen = None

    def on_install(self, editor: "CodeEditor") -> None:
        """
        Install the panel in the editor.

        Parameters
        ----------
        editor: CodeEditor
            The editor instance.

        Notes
        -----
        This method is called when the panel is added to the editor. You should
        never call it yourself, even in a subclasss.
        """
        EditorExtension.on_install(self, editor)

        self.setParent(editor)
        self.setPalette(QApplication.instance().palette())
        self.setFont(QApplication.instance().font())
        self.editor.panels.refresh()
        self._background_brush = QBrush(QColor(
            self.palette().window().color())
        )
        self._foreground_pen = QPen(QColor(
            self.palette().windowText().color())
        )

        if self.position == PanelPosition.FLOATING:
            self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event) -> None:
        """
        Fill the panel's background.

        You need to extend this method in the child class to paint the panel's
        desired information.
        """
        if self.isVisible() and self.position != PanelPosition.FLOATING:
            # fill background
            self._background_brush = QBrush(QColor(
                self.editor.sideareas_color))
            self._foreground_pen = QPen(QColor(
                self.palette().windowText().color()))
            painter = QPainter(self)
            painter.fillRect(event.rect(), self._background_brush)
        else:
            logger.debug(f'paintEvent method must be defined in {self}')

    def paint_cell(self, painter) -> None:
        """Paint cell dividers in the visible region if needed."""
        for top_position, line_number, block in self.editor.visible_blocks:
            if is_cell_header(block) and self.position in [
                PanelPosition.LEFT,
                PanelPosition.RIGHT,
            ]:
                pen = painter.pen()
                pen.setStyle(Qt.SolidLine)
                pen.setBrush(self._linecell_color)
                painter.setPen(pen)
                painter.drawLine(
                    0, top_position, self.width(), top_position
                )

    def sizeHint(self) -> QSize:
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
        if self.position != PanelPosition.FLOATING:
            raise NotImplementedError(
                f'sizeHint method must be implemented in {self}'
            )

    def setVisible(self, visible: bool) -> None:
        """
        Show/hide the panel.

        This calls automatically PanelsManager.refresh_panels.

        Paramaters
        ----------
        visible: bool
            The visibility state.
        """
        logger.debug('%s visibility changed', self.name)
        super().setVisible(visible)
        if self.editor:
            self.editor.panels.refresh()

    def geometry(self) -> tuple:
        """
        Return the geometry dimensions for floating panels.

        If None is returned for width or height, the editor contentsRect
        dimensions will be used for them.

        Returns
        -------
        geometry: tuple
            (x0, y0, height, width).
        """
        return 0, 0, None, None

    def set_geometry(self, crect: QRect) -> None:
        """
        Set geometry for floating panels.

        Normally you don't need to override this method, you should override
        :meth:`geometry` instead.

        Paramaters
        ----------
        crect: QRect
            The editor's contentsRect.
        """
        x0, y0, width, height = self.geometry()

        if width is None:
            width = crect.width()
        if height is None:
            height = crect.height()

        # Calculate editor coordinates with their offsets
        offset = self.editor.contentOffset()
        x = (
            self.editor.blockBoundingGeometry(self.editor.firstVisibleBlock())
            .translated(offset.x(), offset.y()).left()
            + self.editor.document().documentMargin()
            + self.editor.panels.margin_size(PanelPosition.LEFT)
        )
        y = crect.top() + self.editor.panels.margin_size(PanelPosition.TOP)

        self.setGeometry(
            QRect(ceil(x + x0), ceil(y + y0), ceil(width), ceil(height))
        )
