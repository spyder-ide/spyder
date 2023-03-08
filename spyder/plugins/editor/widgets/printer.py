# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import time

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QToolBar
from qtpy.QtPrintSupport import QPrinter, QPrintPreviewDialog

from spyder.api.translations import _
from spyder.utils.icon_manager import ima
from spyder.utils.stylesheet import PANES_TOOLBAR_STYLESHEET


# TODO: Implement header and footer support
class SpyderPrinter(QPrinter):
    def __init__(self, mode=QPrinter.ScreenResolution, header_font=None):
        QPrinter.__init__(self, mode)
        self.setColorMode(QPrinter.Color)
        self.setPageOrder(QPrinter.FirstPageFirst)
        self.date = time.ctime()
        if header_font is not None:
            self.header_font = header_font

    # <!> The following method is simply ignored by QPlainTextEdit
    #     (this is a copy from QsciEditor's Printer)
    def formatPage(self, painter, drawing, area, pagenr):
        header = '%s - %s - Page %s' % (self.docName(), self.date, pagenr)
        painter.save()
        painter.setFont(self.header_font)
        painter.setPen(QColor(Qt.black))
        if drawing:
            painter.drawText(area.right()-painter.fontMetrics().width(header),
                             area.top()+painter.fontMetrics().ascent(), header)
        area.setTop(area.top()+painter.fontMetrics().height()+5)
        painter.restore()


class SpyderPrintPreviewDialog(QPrintPreviewDialog):
    """
    Subclass to make the default Qt dialog conform to the style and icons used
    in Spyder.
    """

    def __init__(self, printer, parent=None):
        super().__init__(printer, parent)
        self.toolbar = self.findChildren(QToolBar)[0]

        self.adjust_toolbar_style()
        self.make_tooltips_translatable()

    def adjust_toolbar_style(self):
        """Make toolbar to follow Spyder style."""
        self.toolbar.setStyleSheet(str(PANES_TOOLBAR_STYLESHEET))
        self.toolbar.setMovable(False)

        actions = self.toolbar.actions()

        actions[0].setIcon(ima.icon('print.fit_width'))
        actions[1].setIcon(ima.icon('print.fit_page'))
        actions[2].setVisible(False)  # Separator

        actions[4].setIcon(ima.icon('zoom_out'))
        actions[5].setIcon(ima.icon('zoom_in'))
        actions[6].setVisible(False)  # Separator

        actions[7].setIcon(ima.icon('portrait'))
        actions[8].setIcon(ima.icon('landscape'))
        actions[9].setVisible(False)  # Separator

        actions[10].setIcon(ima.icon('first_page'))
        actions[11].setIcon(ima.icon('previous_page'))
        actions[13].setIcon(ima.icon('next_page'))
        actions[14].setIcon(ima.icon('last_page'))
        actions[15].setVisible(False)  # Separator

        actions[16].setIcon(ima.icon('print.single_page'))
        actions[17].setVisible(False)  # No icon in Material design for this
        actions[18].setIcon(ima.icon('print.all_pages'))
        actions[19].setVisible(False)  # Separator

        actions[20].setIcon(ima.icon('print.page_setup'))
        actions[21].setIcon(ima.icon('print'))

    def make_tooltips_translatable(self):
        """Make toolbar button tooltips translatable."""
        # These are the tooltips shown by default by Qt. The number on the left
        # is the corresponding action index in the toolbar.
        translatable_tooltips = [
            (0, _('Fit width')),
            (1, _('Fit page')),
            (4, _('Zoom out')),
            (5, _('Zoom in')),
            (7, _('Portrait')),
            (8, _('Landscape')),
            (10, _('First page')),
            (11, _('Previous page')),
            (13, _('Next page')),
            (14, _('Last page')),
            (16, _('Show single page')),
            (18, _('Show overview of all pages')),
            (20, _('Page setup')),
            (21, _('Print')),
        ]

        actions = self.toolbar.actions()
        for idx, tooltip in translatable_tooltips:
            actions[idx].setText(tooltip)
            actions[idx].setToolTip(tooltip)

    def showEvent(self, event):
        """
        Give focus to the toolbar to avoid giving focus to the combobox that
        shows the page percentage size, which is odd.
        """
        super().showEvent(event)
        self.toolbar.setFocus()
