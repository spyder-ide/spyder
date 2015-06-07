# -*- coding: utf-8 -*-
#
# Copyright © 2015 Gonzalo Peña-Castellanos (@goanpeca)
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Numpy Matrix/Array Builder Widget
"""

# TODO:
# -Set font based on caller? editor console? and adjust size of widget
# -Fix positioning
# -Use the same font as editor/console?

from __future__ import division

import re

from spyderlib.qt.QtGui import (QToolTip, QLineEdit, QHBoxLayout, QWidget,
                                QDialog, QToolButton, QTableWidget,
                                QTableWidgetItem)
from spyderlib.qt.QtCore import (Qt, QPoint, QEvent)
from spyderlib.utils.qthelpers import get_std_icon
from spyderlib.baseconfig import _

# Constants
SHORTCUT_INLINE = "Shift+Ctrl+*"  # fixed shortcuts for editos and consoles
SHORTCUT_TABLE = "Ctrl+*"         # fixed shortcuts for editos and consoles
ELEMENT_SEPARATOR = ', '
ROW_SEPARATOR = ';'
BRACES = '], ['
NAN_VALUES = ['nan', 'NAN', 'NaN', 'Na', 'NA', 'na']


class NumpyArrayInline(QLineEdit):
    """ """
    def __init__(self, parent):
        QLineEdit.__init__(self, parent)
        self._parent = parent

    def keyPressEvent(self, event):
        """ """
        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            self._parent.process_text()
            if self._parent.is_valid():
                self._parent.keyPressEvent(event)
        else:
            QLineEdit.keyPressEvent(self, event)

    # to catch the Tab key event
    def event(self, event):
        if event.type() == QEvent.KeyPress:
            if (event.key() == Qt.Key_Tab or event.key() == Qt.Key_Space):
                text = self.text()
                cursor = self.cursorPosition()
                # fix to include in "undo/redo" history
                if cursor != 0 and text[cursor-1] == ' ':
                    text = text[:cursor-1] + ROW_SEPARATOR + ' ' +\
                        text[cursor:]
                else:
                    text = text[:cursor] + ' ' + text[cursor:]
                self.setCursorPosition(cursor)
                self.setText(text)
                self.setCursorPosition(cursor + 1)
                return False
        return QWidget.event(self, event)


class NumpyArrayTable(QTableWidget):
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
            # To avoid having to enter one final tab
            self.setDisabled(True)
            self.setDisabled(False)
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

        # handle empty table case
        if rows == 2 and cols == 2:
            item = self.item(0, 0)
            if item is None:
                return ''
            elif item.text() == '':
                return ''

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
            text.append(ROW_SEPARATOR)

        return ''.join(text[:-1])  # to remove the final uneeded ;


class NumpyArrayDialog(QDialog):
    """ """
    def __init__(self, parent, inline=True, offset=0):
        QDialog.__init__(self, parent)
        self._parent = parent
        self._text = None
        self._valid = None
        self._offset = offset

        # TODO: add this as an option in the General Preferences?
        self._force_float = False

        self._help_inline = _("""
           <b>Numpy Array/Matrix Helper</b><br>
           Type an array in Matlab    : <code>[1 2;3 4]</code><br>
           or Spyder simplified syntax : <code>1 2;3 4</code>
           <br><br>
           Hit 'Enter' for array or 'Ctrl+Enter' for matrix.
           <br><br>
           <b>Hint:</b><br>
           Use two spaces or two tabs to generate a ';'.
           """)

        self._help_table = _("""
           <b>Numpy Array/Matrix Helper</b><br>
           Enter an array in the table. <br>
           Use Tab to move between cells.
           <br><br>
           Hit 'Enter' for array or 'Ctrl+Enter' for matrix.
           <br><br>
           <b>Hint:</b><br>
           Use two tabs at the end of a row to move to the next row.
           """)

        # widgets
        self._button_warning = QToolButton()
        self._button_help = HelperToolButton()
        self._button_help.setIcon(get_std_icon('MessageBoxInformation'))

        style = """
            QToolButton {
              border: 1px solid grey;
              padding:0px;
              border-radius: 2px;
              background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                  stop: 0 #f6f7fa, stop: 1 #dadbde);
            }
            """
        self._button_help.setStyleSheet(style)

        if inline:
            self._button_help.setToolTip(self._help_inline)
            self._text = NumpyArrayInline(self)
            self._widget = self._text
        else:
            self._button_help.setToolTip(self._help_table)
            self._table = NumpyArrayTable(self)
            self._widget = self._table

        style = """
            QDialog {
              margin:0px;
              border: 1px solid grey;
              padding:0px;
              border-radius: 2px;
            }"""
        self.setStyleSheet(style)

        style = """
            QToolButton {
              margin:1px;
              border: 0px solid grey;
              padding:0px;
              border-radius: 0px;
            }"""
        self._button_warning.setStyleSheet(style)

        # widget setup
        self.setWindowFlags(Qt.Window | Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setWindowOpacity(0.90)
        self._widget.setMinimumWidth(200)

        # layout
        self._layout = QHBoxLayout()
        self._layout.addWidget(self._widget)
        self._layout.addWidget(self._button_warning, 1, Qt.AlignTop)
        self._layout.addWidget(self._button_help, 1, Qt.AlignTop)
        self.setLayout(self._layout)

        self._widget.setFocus()

    def keyPressEvent(self, event):
        """Override Qt method"""
        QToolTip.hideText()
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
        values = self._widget.text().strip()

        if values != '':
            # cleans repeated spaces
            exp = r'(\s*)' + ROW_SEPARATOR + r'(\s*)'
            values = re.sub(exp, ROW_SEPARATOR, values)
            values = re.sub("\s+", " ", values)
            values = re.sub("]$", "", values)
            values = re.sub("^\[", "", values)
            values = re.sub(ROW_SEPARATOR + r'*$', '', values)

            # replaces spaces by commas
            values = values.replace(' ',  ELEMENT_SEPARATOR)

            # iterate to find number of rows and columns
            new_values = []
            rows = values.split(ROW_SEPARATOR)
            nrows = len(rows)
            ncols = []
            for row in rows:
                new_row = []
                elements = row.split(ELEMENT_SEPARATOR)
                ncols.append(len(elements))
                for e in elements:
                    num = e

                    # replaces not defined values
                    if num in NAN_VALUES:
                        num = 'np.nan'

                    # Convert numbers to floating point
                    if self._force_float:
                        try:
                            num = str(float(e))
                        except:
                            pass
                    new_row.append(num)
                new_values.append(ELEMENT_SEPARATOR.join(new_row))
            new_values = ROW_SEPARATOR.join(new_values)
            values = new_values

            # Check validity
            if len(set(ncols)) == 1:
                self._valid = True
            else:
                self._valid = False

            # Single rows are parsed as 1D arrays/matrices
            if nrows == 1:
                prefix = prefix[:-1]
                suffix = suffix.replace("]])", "])")

            # Fix offset
            offset = self._offset
            braces = BRACES.replace(' ', '\n' + ' '*(offset + len(prefix) - 1))

            values = values.replace(ROW_SEPARATOR,  braces)
            text = "{0}{1}{2}".format(prefix, values, suffix)

            self._text = text
        else:
            self._text = ''
        self.update_warning()

    def update_warning(self):
        """ """
        widget = self._button_warning
        if not self.is_valid():
            tip = _('Array dimensions not valid')
            widget.setIcon(get_std_icon('MessageBoxWarning'))
            widget.setToolTip(tip)
            QToolTip.showText(self._widget.mapToGlobal(QPoint(0, 5)), tip)
        else:
            self._button_warning.setToolTip('')

    def is_valid(self):
        """ """
        return self._valid

    def text(self):
        """ """
        return self._text

    def mousePressEvent(self, event):
        """ """
#        print(dir(event))


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
        QToolTip.showText(self.mapToGlobal(QPoint(0, 0)), self._tip_text)


def test():
    """ """
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    app.setStyle('Plastique')

    dlg_inline = NumpyArrayDialog(None, inline=True)
    dlg_table = NumpyArrayDialog(None, inline=False)

    if dlg_inline.exec_():
        print(dlg_inline.text())

    if dlg_table.exec_():
        print(dlg_table.text())


if __name__ == "__main__":
    test()
