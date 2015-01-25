# -*- coding: utf-8 -*-
#
# Copyright © 2015 Gonzalo Peña
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Numpy Matrix/Array Edit Helper Widget"""

# TODO: 
# -Set font based on caller? editor console? and adjust size of widget
# -Fix positioning
# -Use the same font as editor/console?
# -Move this widget to a general location as another widget and generalize it?


from __future__ import division

import re

from spyderlib.qt.QtGui import (QToolTip, QLineEdit, QHBoxLayout,
                                QDialog, QToolButton, QIcon, QTableWidget,
                                QTableWidgetItem, QWidget)
from spyderlib.qt.QtCore import (Qt, QPoint, QEvent)
from spyderlib.utils.qthelpers import get_std_icon
from spyderlib.baseconfig import _, get_image_path


# Global shortcuts
SHORTCUT_INLINE = "Shift+Ctrl+*"
SHORTCUT_TABLE = "Ctrl+*"


class NumpyMatrixInline(QLineEdit):
    """ """
    def __init__(self, parent):
        QLineEdit.__init__(self, parent)
        self._parent = parent

    # to catch the Tab key event
    def event(self, event):
        if event.type() == QEvent.KeyPress:
            if (event.key() == Qt.Key_Tab or event.key() == Qt.Key_Space):
                text = self.text()
                cursor = self.cursorPosition()
                # fix to include in "undo/redo" history
                if cursor != 0 and text[cursor - 1] == ' ':
                    text = text[:cursor] + '; ' + text[cursor:]
                else:
                    text = text[:cursor] + ' ' + text[cursor:]
                self.setCursorPosition(cursor)
                self.setText(text)
                return False
        return QWidget.event(self, event)


class NumpyMatrixTable(QTableWidget):
    """ """
    def __init__(self, parent):
        QTableWidget.__init__(self, parent)
        self._parent = parent
        self.setRowCount(2)
        self.setColumnCount(2)
        self.reset_headers()
        # signals
        self.cellChanged.connect(self.cell_changed)

    def keyPressEvent(self, event):
        """ """
        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            QTableWidget.keyPressEvent(self, event)
            self._parent.keyPressEvent(event)
        else:
            QTableWidget.keyPressEvent(self, event)

    def cell_changed(self, row, col):
        """ """
        value = self.item(row, col).text()
        rows = self.rowCount()
        cols = self.columnCount()

        if value:
            if row == rows - 1:
                self.setRowCount(rows + 1)
            if col == cols - 1:
                self.setColumnCount(cols + 1)
        self.reset_headers()

    def reset_headers(self):
        """ """
        rows = self.rowCount()
        cols = self.columnCount()

        for r in range(rows):
            self.setVerticalHeaderItem(r, QTableWidgetItem(str(r)))
        for c in range(cols):
            self.setHorizontalHeaderItem(c, QTableWidgetItem(str(c)))
            self.setColumnWidth(c, 40)

    def text(self):
        """ """
        text = []
        rows = self.rowCount()
        cols = self.columnCount()

        for r in range(rows - 1):
            for c in range(cols - 1):
                item = self.item(r, c)
                if item is not None:
                    value = item.text()
                else:
                    value = '0'

                if value == '':
                    value = '0'
                text.append(' ')
                text.append(value)
            text.append(';')

        return ''.join(text[:-1])  # to remove the final uneeded ;


class NumpyMatrixDialog(QDialog):
    """ """
    def __init__(self, parent, inline=True):
        QDialog.__init__(self, parent)
        self._parent = parent
        self._text = None

        self._help_inline = _("""
           <b>Numpy Array/Matrix Helper</b><br>
           Type an array in Matlab    : <code>[1 2;3 4]</code><br>
           or Spyder simplified syntax : <code>1 2;3 4</code>
           <br><br>
           Hit 'Enter' for array or 'Ctrl+Enter' for matrix
           <br><br>
           <b>Hint:</b><br>
           - <i>Use two spaces or two tabs to generate a ';'</i>
           <br>
           """)

        self._help_table = _("""
           <b>Numpy Array/Matrix Helper</b><br>
           Enter an array in the table. <br>
           Use Tab to move between cells
           <br><br>
           Hit 'Enter' for array or 'Ctrl+Enter' for matrix
           <br><br>
           <b>Hint:</b><br>
           - <i>Use two tabs at then end of a line to move to the next</i>
           <br>
           """)

        # widgets
        self._button_help = HelperToolButton()
        self._button_help.setIcon(get_std_icon('MessageBoxInformation'))
        self._button_help.setStyleSheet("QToolButton {border: 0px solid grey; \
            padding:0px;}")

        if inline:
            self._button_help.setToolTip(self._help_inline)
            self._text = NumpyMatrixInline(self)
            self._widget = self._text
        else:
            self._button_help.setToolTip(self._help_table)
            self._table = NumpyMatrixTable(self)
            self._widget = self._table

        style = """
            QDialog {
              margin:0px;
              border: 1px solid grey;
              padding:0px;
              border-radius: 2px;
            }"""
        self.setStyleSheet(style)
        self.setWindowFlags(Qt.Window | Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)

        # layout
        self._layout = QHBoxLayout()
        self._layout.addWidget(self._widget)
        self._layout.addWidget(self._button_help)
        self.setLayout(self._layout)

        self._widget.setFocus()

    def keyPressEvent(self, event):
        """Override Qt method"""
        ctrl = event.modifiers() & Qt.ControlModifier

        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            if ctrl:
                self.process_text(array=False)
            else:
                self.process_text(array=True)
            self.accept()
        else:
            QDialog.keyPressEvent(self, event)

    def event(self, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Tab:
            return False
        return QWidget.event(self, event)

    def process_text(self, array=True):
        """ """
        if array:
            prefix = 'np.array([['
        else:
            prefix = 'np.matrix([['

        suffix = ']])'
        value = self._widget.text().strip()

        if value != '':
            # cleans repeated spaces
            exp = r'(\s*);(\s*)'
            value = re.sub(exp, ";", value)
            value = re.sub("\s+", " ", value)
            value = re.sub("]$", "", value)
            value = re.sub("^\[", "", value)

            # replaces spaces by commas
            value = value.replace(' ',  ', ')

            # replaces not defined values
            nan_values = ['nan', 'NAN', 'NaN', 'Na', 'NA', 'na']
            for nan_value in nan_values:
                value = value.replace(nan_value,  'np.nan')

            # replaces colon by braces
            value = value.replace(';',  '], [')

            text = "{0}{1}{2}".format(prefix, value, suffix)

            self._text = text

    def text(self):
        """ """
        return self._text


class HelperToolButton(QToolButton):
    """ """
    def __init__(self):
        QToolButton.__init__(self)

    def setToolTip(self, text):
        """ """
        self._tip_text = text

    def toolTip(self):
        """ """
        return self._tip_text

    def mousePressEvent(self, event):
        """ """
        QToolTip.hideText()

    def mouseReleaseEvent(self, event):
        """ """
        QToolTip.showText(self.mapToGlobal(QPoint(0, 0)),
                          self._tip_text)


def test():
    """ """
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    app.setStyle('Plastique')

    dlg_inline = NumpyMatrixDialog(None, inline=True)
    dlg_table = NumpyMatrixDialog(None, inline=False)

    if dlg_inline.exec_():
        print(dlg_inline.text())

    if dlg_table.exec_():
        print(dlg_table.text())


if __name__ == "__main__":
    test()
