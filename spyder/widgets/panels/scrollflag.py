# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
This module contains the Scroll Flag panel
"""

from qtpy.QtCore import QSize, Qt, QRect
from qtpy.QtGui import QPainter, QBrush, QColor, QCursor
from qtpy.QtWidgets import (QScrollBar, QCommonStyle, QStyle,
                            QWidget, QStyleOptionSlider, QApplication)

from spyder.api.panel import Panel


class ScrollFlagArea(Panel):
    """Source code editor's scroll flag area"""
    WIDTH = 12
    FLAGS_DX = 4
    FLAGS_DY = 2

    def __init__(self, editor):
        Panel.__init__(self, editor)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.scrollable = True

        style = self.style()
        opt = QStyleOptionSlider()
        QScrollBar().initStyleOption(opt)
        addline_rect = style.subControlRect(QStyle.CC_ScrollBar, opt,
                                            QStyle.SC_ScrollBarAddLine, self)
        self.__addline_height = addline_rect.height()

        self.__altmodif = False
        self.setMouseTracking(True)

    @property
    def slider(self):
        return self.editor.verticalScrollBar().isVisible()

    def sizeHint(self):
        """Override Qt method"""
        return QSize(self.WIDTH, 0)

    def paintEvent(self, event):
        """
        Override Qt method.
        Painting the scroll flag area
        """
        make_flag = self.make_flag_qrect

        # Filling the whole painting area
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.editor.sideareas_color)
        block = self.editor.document().firstBlock()

        # Painting warnings and todos
        for line_number in range(1, self.editor.document().blockCount()+1):
            data = block.userData()
            if data:
                position = self.value_to_position(line_number)
                if data.code_analysis:
                    # Warnings
                    color = self.editor.warning_color
                    for _message, error in data.code_analysis:
                        if error:
                            color = self.editor.error_color
                            break
                    self.set_painter(painter, color)
                    painter.drawRect(make_flag(position))
                if data.todo:
                    # TODOs
                    self.set_painter(painter, self.editor.todo_color)
                    painter.drawRect(make_flag(position))
                if data.breakpoint:
                    # Breakpoints
                    self.set_painter(painter, self.editor.breakpoint_color)
                    painter.drawRect(make_flag(position))
            block = block.next()

        # Occurrences
        if self.editor.occurrences:
            self.set_painter(painter, self.editor.occurrence_color)
            for line_number in self.editor.occurrences:
                position = self.value_to_position(line_number)
                painter.drawRect(make_flag(position))

        # Found results
        if self.editor.found_results:
            self.set_painter(painter, self.editor.found_results_color)
            for line_number in self.editor.found_results:
                position = self.value_to_position(line_number)
                painter.drawRect(make_flag(position))

        # Painting the slider range
        cursor_pos = self.mapFromGlobal(QCursor().pos())
        if self.rect().contains(cursor_pos) or self.__altmodif:
            pen_color = QColor(Qt.gray)
            pen_color.setAlphaF(.85)
            painter.setPen(pen_color)
            brush_color = QColor(Qt.gray)
            brush_color.setAlphaF(.5)
            painter.setBrush(QBrush(brush_color))

            
            vsb = self.editor.verticalScrollBar()
            cursor_y = self.position_to_value(cursor_pos.y())
            max_val= self.position_to_value(self.height()-self.__addline_height)-vsb.pageStep()/2
            min_val = self.position_to_value(self.__addline_height)+vsb.pageStep()/2     
            cursor_y = max(min_val, min(max_val, cursor_y))
            
            pos1 = self.value_to_position(cursor_y-vsb.pageStep()/2)
            pos2 = self.value_to_position(cursor_y+vsb.pageStep()/2)
            painter.drawRect(QRect(1, pos1, self.WIDTH-2, pos2-pos1+1))

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()
        
    def altPressEvent(self, event):
        self.__altmodif = True
        self.update()
        
    def altReleaseEvent(self, event):
        self.__altmodif = False
        self.update()

    def mouseMoveEvent(self, event):
        self.update()

    def mousePressEvent(self, event):
        """Override Qt method"""
        vsb = self.editor.verticalScrollBar()
        value = self.position_to_value(event.pos().y()-1)
        vsb.setValue(value-.5*vsb.pageStep())

    def get_scale_factor(self):
        """Return scrollbar's scale factor:
        ratio between pixel span height and value span height"""
        delta = self.__addline_height if self.slider else 1
        vsb = self.editor.verticalScrollBar()
        position_height = vsb.height()-2*delta-1-2
        value_height = vsb.maximum()-vsb.minimum()+vsb.pageStep()
        return float(position_height)/value_height

    def value_to_position(self, y):
        """Convert value to position"""
        offset = self.__addline_height if self.slider else 1
        vsb = self.editor.verticalScrollBar()
        return (y-vsb.minimum())*self.get_scale_factor()+offset

    def position_to_value(self, y):
        """Convert position to value"""
        offset = self.__addline_height if self.slider else 1
        vsb = self.editor.verticalScrollBar()
        return vsb.minimum()+max([0, (y-offset)/self.get_scale_factor()])

    def make_flag_qrect(self, position):
        """Make flag QRect"""
        return QRect(self.FLAGS_DX/2, position-self.FLAGS_DY/2,
                     self.WIDTH-self.FLAGS_DX, self.FLAGS_DY)

    def make_slider_range(self, value):
        """Make slider range QRect"""
        vsb = self.editor.verticalScrollBar()
        pos1 = self.value_to_position(value)
        pos2 = self.value_to_position(value + vsb.pageStep())
        return QRect(1, pos1, self.WIDTH-2, pos2-pos1+1)

    def wheelEvent(self, event):
        """Override Qt method"""
        self.editor.wheelEvent(event)

    def set_painter(self, painter, light_color):
        """Set scroll flag area painter pen and brush colors"""
        painter.setPen(QColor(light_color).darker(120))
        painter.setBrush(QBrush(QColor(light_color)))

    def set_enabled(self, state):
        """Toggle scroll flag area visibility"""
        self.enabled = state
        self.setVisible(state)
