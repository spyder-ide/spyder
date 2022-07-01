# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Array Builder Widget."""

# TODO:
# - Set font based on caller? editor console? and adjust size of widget
# - Fix positioning
# - Use the same font as editor/console?
# - Generalize separators
# - Generalize API for registering new array builders

# Standard library imports
from __future__ import division
import re

# Third party imports
from qtpy.QtCore import QEvent, QPoint, Qt
from qtpy.QtWidgets import (QDialog, QHBoxLayout, QLineEdit, QTableWidget,
                            QTableWidgetItem, QToolButton, QToolTip)

# Local imports
from spyder.config.base import _
from spyder.utils.icon_manager import ima
from spyder.utils.palette import QStylePalette
from spyder.widgets.helperwidgets import HelperToolButton

# Constants
SHORTCUT_TABLE = "Ctrl+M"
SHORTCUT_INLINE = "Ctrl+Alt+M"


class ArrayBuilderType:
    LANGUAGE = None
    ELEMENT_SEPARATOR = None
    ROW_SEPARATOR = None
    BRACES = None
    EXTRA_VALUES = None
    ARRAY_PREFIX = None
    MATRIX_PREFIX = None

    def check_values(self):
        pass


class ArrayBuilderPython(ArrayBuilderType):
    ELEMENT_SEPARATOR = ', '
    ROW_SEPARATOR = ';'
    BRACES = '], ['
    EXTRA_VALUES = {
        'np.nan': ['nan', 'NAN', 'NaN', 'Na', 'NA', 'na'],
        'np.inf': ['inf', 'INF'],
    }
    ARRAY_PREFIX = 'np.array([['
    MATRIX_PREFIX = 'np.matrix([['


_REGISTERED_ARRAY_BUILDERS = {
    'python': ArrayBuilderPython,
}


class ArrayInline(QLineEdit):
    def __init__(self, parent, options=None):
        super(ArrayInline, self).__init__(parent)
        self._parent = parent
        self._options = options

    def keyPressEvent(self, event):
        """Override Qt method."""
        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            self._parent.process_text()
            if self._parent.is_valid():
                self._parent.keyPressEvent(event)
        else:
            super(ArrayInline, self).keyPressEvent(event)

    # To catch the Tab key event
    def event(self, event):
        """
        Override Qt method.

        This is needed to be able to intercept the Tab key press event.
        """
        if event.type() == QEvent.KeyPress:
            if (event.key() == Qt.Key_Tab or event.key() == Qt.Key_Space):
                text = self.text()
                cursor = self.cursorPosition()

                # Fix to include in "undo/redo" history
                if cursor != 0 and text[cursor-1] == ' ':
                    text = (text[:cursor-1] + self._options.ROW_SEPARATOR
                            + ' ' + text[cursor:])
                else:
                    text = text[:cursor] + ' ' + text[cursor:]
                self.setCursorPosition(cursor)
                self.setText(text)
                self.setCursorPosition(cursor + 1)

                return False

        return super(ArrayInline, self).event(event)


class ArrayTable(QTableWidget):
    def __init__(self, parent, options=None):
        super(ArrayTable, self).__init__(parent)
        self._parent = parent
        self._options = options
        self.setRowCount(2)
        self.setColumnCount(2)
        self.reset_headers()

        # signals
        self.cellChanged.connect(self.cell_changed)

    def keyPressEvent(self, event):
        """Override Qt method."""
        super(ArrayTable, self).keyPressEvent(event)
        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            # To avoid having to enter one final tab
            self.setDisabled(True)
            self.setDisabled(False)
            self._parent.keyPressEvent(event)

    def cell_changed(self, row, col):
        item = self.item(row, col)
        value = None

        if item:
            rows = self.rowCount()
            cols = self.columnCount()
            value = item.text()

        if value:
            if row == rows - 1:
                self.setRowCount(rows + 1)
            if col == cols - 1:
                self.setColumnCount(cols + 1)
        self.reset_headers()

    def reset_headers(self):
        """Update the column and row numbering in the headers."""
        rows = self.rowCount()
        cols = self.columnCount()

        for r in range(rows):
            self.setVerticalHeaderItem(r, QTableWidgetItem(str(r)))
        for c in range(cols):
            self.setHorizontalHeaderItem(c, QTableWidgetItem(str(c)))
            self.setColumnWidth(c, 40)

    def text(self):
        """Return the entered array in a parseable form."""
        text = []
        rows = self.rowCount()
        cols = self.columnCount()

        # handle empty table case
        if rows == 2 and cols == 2:
            item = self.item(0, 0)
            if item is None:
                return ''

        for r in range(rows - 1):
            for c in range(cols - 1):
                item = self.item(r, c)
                if item is not None:
                    value = item.text()
                else:
                    value = '0'

                if not value.strip():
                    value = '0'

                text.append(' ')
                text.append(value)
            text.append(self._options.ROW_SEPARATOR)

        return ''.join(text[:-1])  # Remove the final uneeded `;`


class ArrayBuilderDialog(QDialog):
    def __init__(self, parent=None, inline=True, offset=0, force_float=False,
                 language='python'):
        super(ArrayBuilderDialog, self).__init__(parent=parent)
        self._language = language
        self._options = _REGISTERED_ARRAY_BUILDERS.get('python', None)
        self._parent = parent
        self._text = None
        self._valid = None
        self._offset = offset

        # TODO: add this as an option in the General Preferences?
        self._force_float = force_float

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

        # Widgets
        self._button_warning = QToolButton()
        self._button_help = HelperToolButton()
        self._button_help.setIcon(ima.icon('MessageBoxInformation'))

        style = (("""
            QToolButton {{
              border: 1px solid grey;
              padding:0px;
              border-radius: 2px;
              background-color: qlineargradient(x1: 1, y1: 1, x2: 1, y2: 1,
                  stop: 0 {stop_0}, stop: 1 {stop_1});
            }}
            """).format(stop_0=QStylePalette.COLOR_BACKGROUND_4,
                        stop_1=QStylePalette.COLOR_BACKGROUND_2))

        self._button_help.setStyleSheet(style)

        if inline:
            self._button_help.setToolTip(self._help_inline)
            self._text = ArrayInline(self, options=self._options)
            self._widget = self._text
        else:
            self._button_help.setToolTip(self._help_table)
            self._table = ArrayTable(self, options=self._options)
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
        """Override Qt method."""
        QToolTip.hideText()
        ctrl = event.modifiers() & Qt.ControlModifier

        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            if ctrl:
                self.process_text(array=False)
            else:
                self.process_text(array=True)
            self.accept()
        else:
            super(ArrayBuilderDialog, self).keyPressEvent(event)

    def event(self, event):
        """
        Override Qt method.

        Useful when in line edit mode.
        """
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Tab:
            return False

        return super(ArrayBuilderDialog, self).event(event)

    def process_text(self, array=True):
        """
        Construct the text based on the entered content in the widget.
        """
        if array:
            prefix = self._options.ARRAY_PREFIX
        else:
            prefix = self._options.MATRIX_PREFIX

        suffix = ']])'
        values = self._widget.text().strip()

        if values != '':
            # cleans repeated spaces
            exp = r'(\s*)' + self._options.ROW_SEPARATOR + r'(\s*)'
            values = re.sub(exp, self._options.ROW_SEPARATOR, values)
            values = re.sub(r"\s+", " ", values)
            values = re.sub(r"]$", "", values)
            values = re.sub(r"^\[", "", values)
            values = re.sub(self._options.ROW_SEPARATOR + r'*$', '', values)

            # replaces spaces by commas
            values = values.replace(' ',  self._options.ELEMENT_SEPARATOR)

            # iterate to find number of rows and columns
            new_values = []
            rows = values.split(self._options.ROW_SEPARATOR)
            nrows = len(rows)
            ncols = []
            for row in rows:
                new_row = []
                elements = row.split(self._options.ELEMENT_SEPARATOR)
                ncols.append(len(elements))
                for e in elements:
                    num = e

                    # replaces not defined values
                    for key, values in self._options.EXTRA_VALUES.items():
                        if num in values:
                            num = key

                    # Convert numbers to floating point
                    if self._force_float:
                        try:
                            num = str(float(e))
                        except:
                            pass
                    new_row.append(num)
                new_values.append(
                    self._options.ELEMENT_SEPARATOR.join(new_row))
            new_values = self._options.ROW_SEPARATOR.join(new_values)
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
            braces = self._options.BRACES.replace(
                ' ',
                '\n' + ' '*(offset + len(prefix) - 1))
            values = values.replace(self._options.ROW_SEPARATOR,  braces)
            text = "{0}{1}{2}".format(prefix, values, suffix)

            self._text = text
        else:
            self._text = ''

        self.update_warning()

    def update_warning(self):
        """
        Updates the icon and tip based on the validity of the array content.
        """
        widget = self._button_warning
        if not self.is_valid():
            tip = _('Array dimensions not valid')
            widget.setIcon(ima.icon('MessageBoxWarning'))
            widget.setToolTip(tip)
            QToolTip.showText(self._widget.mapToGlobal(QPoint(0, 5)), tip)
        else:
            self._button_warning.setToolTip('')

    def is_valid(self):
        """Return if the current array state is valid."""
        return self._valid

    def text(self):
        """Return the parsed array/matrix text."""
        return self._text

    @property
    def array_widget(self):
        """Return the array builder widget."""
        return self._widget


def test():  # pragma: no cover
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    dlg_table = ArrayBuilderDialog(None, inline=False)
    dlg_inline = ArrayBuilderDialog(None, inline=True)
    dlg_table.show()
    dlg_inline.show()
    app.exec_()


if __name__ == "__main__":  # pragma: no cover
    test()
