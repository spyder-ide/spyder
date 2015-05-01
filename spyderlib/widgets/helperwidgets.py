# -*- coding: utf-8 -*-
#
# Copyright © 2013-2015 The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)


from spyderlib.qt.QtCore import QPoint
from spyderlib.qt.QtGui import QToolButton, QToolTip

class HelperToolButton(QToolButton):
    """Subclasses QToolButton, to provide a simple tooltip on mousedown.
    """
    def setToolTip(self, text):
        self._tip_text = text

    def toolTip(self):
        return self._tip_text

    def mousePressEvent(self, event):
        QToolTip.hideText()

    def mouseReleaseEvent(self, event):
        QToolTip.showText(self.mapToGlobal(QPoint(0, 0)), self._tip_text)
