# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
This module contains the Scroll Flag panel
"""

from qtpy.QtCore import QSize, Qt, QRect

from spyder.api.panel import Panel


class ScrollFlagArea(Panel):
    """Source code editor's scroll flag area"""
    WIDTH = 12
    FLAGS_DX = 4
    FLAGS_DY = 2

    def __init__(self, editor):
        Panel.__init__(self, editor)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        editor.verticalScrollBar().valueChanged.connect(
                                                  lambda value: self.repaint())

    def sizeHint(self):
        """Override Qt method"""
        return QSize(self.WIDTH, 0)

    def paintEvent(self, event):
        """Override Qt method"""
        self.editor.scrollflagarea_paint_event(event)

    def mousePressEvent(self, event):
        """Override Qt method"""
        vsb = self.editor.verticalScrollBar()
        value = self.position_to_value(event.pos().y()-1)
        vsb.setValue(value-.5*vsb.pageStep())

    def get_scale_factor(self, slider=False):
        """Return scrollbar's scale factor:
        ratio between pixel span height and value span height"""
        delta = 0 if slider else 2
        vsb = self.editor.verticalScrollBar()
        position_height = vsb.height()-delta-1
        value_height = vsb.maximum()-vsb.minimum()+vsb.pageStep()
        return float(position_height)/value_height

    def value_to_position(self, y, slider=False):
        """Convert value to position"""
        offset = 0 if slider else 1
        vsb = self.editor.verticalScrollBar()
        return (y-vsb.minimum())*self.get_scale_factor(slider)+offset

    def position_to_value(self, y, slider=False):
        """Convert position to value"""
        offset = 0 if slider else 1
        vsb = self.editor.verticalScrollBar()
        return vsb.minimum()+max([0, (y-offset)/self.get_scale_factor(slider)])

    def make_flag_qrect(self, position):
        """Make flag QRect"""
        return QRect(self.FLAGS_DX/2, position-self.FLAGS_DY/2,
                     self.WIDTH-self.FLAGS_DX, self.FLAGS_DY)

    def make_slider_range(self, value):
        """Make slider range QRect"""
        vsb = self.editor.verticalScrollBar()
        pos1 = self.value_to_position(value, slider=True)
        pos2 = self.value_to_position(value + vsb.pageStep(), slider=True)
        return QRect(1, pos1, self.WIDTH-2, pos2-pos1+1)

    def wheelEvent(self, event):
        """Override Qt method"""
        self.editor.wheelEvent(event)