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
import re

# Third party imports
import qstylizer.style
from qtpy.QtCore import QEvent, QPoint, Qt
from qtpy.QtGui import QKeyEvent
from qtpy.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QToolTip,
    QVBoxLayout,
)

# Local imports
from spyder.api.translations import _
from spyder.config.base import running_under_pytest
from spyder.utils.icon_manager import ima
from spyder.utils.palette import SpyderPalette
from spyder.utils.stylesheet import AppStyle
from spyder.widgets.helperwidgets import TipWidget

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


_REGISTERED_ARRAY_BUILDERS = {
    'python': ArrayBuilderPython,
}


class ArrayInline(QLineEdit):

    def __init__(self, parent, options=None):
        super().__init__(parent)
        self._parent = parent
        self._options = options

    def keyPressEvent(self, event):
        """Override Qt method."""
        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            self._parent.process_text()
            if self._parent.is_valid():
                self._parent.keyPressEvent(event)
        else:
            super().keyPressEvent(event)

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

        return super().event(event)


class ArrayTable(QTableWidget):

    def __init__(self, parent, options=None):
        super().__init__(parent)
        self._parent = parent
        self._options = options

        # Default number of rows and columns
        self.setRowCount(2)
        self.setColumnCount(2)

        # Select the first cell and send an Enter to it so users can start
        # editing the array after it's displayed.
        # Idea taken from https://stackoverflow.com/a/32205884/438386
        if not running_under_pytest():
            self.setCurrentCell(0, 0)
            event = QKeyEvent(QEvent.KeyPress, Qt.Key_Enter, Qt.NoModifier)
            QApplication.postEvent(self, event)

        # Set headers
        self.reset_headers()

        # Signals
        self.cellChanged.connect(self.cell_changed)

    def keyPressEvent(self, event):
        shift = event.modifiers() & Qt.ShiftModifier

        if event.key() in [Qt.Key_Enter, Qt.Key_Return] and not shift:
            # To edit a cell when pressing Enter.
            # From https://stackoverflow.com/a/70166617/438386
            if self.state() != QAbstractItemView.EditingState:
                self.edit(self.currentIndex())

        super().keyPressEvent(event)

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
        super().__init__(parent=parent)
        self._language = language
        self._options = _REGISTERED_ARRAY_BUILDERS.get('python', None)
        self._parent = parent
        self._text = None
        self._valid = None
        self._offset = offset

        # TODO: add this as an option in the General Preferences?
        self._force_float = force_float

        help_inline = _("""
           <b>Numpy array helper</b><br><br>
           * Type an array using the syntax: <tt>1 2;3 4</tt><br>
           * Use two spaces or tabs to generate a <b>;</b>.<br>
           * You can press <b>Shift+Enter</b> when you are done.
           """
        )

        help_table = _("""
           <b>Numpy array helper</b><br><br>
           * Introduce an array in the table.<br>
           * Use <b>Tab</b> to move between cells or introduce additional
             rows and columns.<br>
           * Use two tabs at the end of a row to move to the next one.<br>
           * You can press <b>Shift+Enter</b> when you are done.
           """
        )

        # Widgets
        button_ok = QToolButton()
        button_ok.setIcon(ima.icon("DialogApplyButton"))
        button_ok.setToolTip(_("Introduce contents"))
        button_ok.clicked.connect(self.accept)

        button_close = QToolButton()
        button_close.setIcon(ima.icon("DialogCloseButton"))
        button_close.setToolTip(_("Cancel"))
        button_close.clicked.connect(self.reject)

        buttons_css = qstylizer.style.StyleSheet()
        buttons_css.QToolButton.setValues(
            height="16px",
            width="16px",
            borderRadius=SpyderPalette.SIZE_BORDER_RADIUS
        )
        for button in [button_ok, button_close]:
            button.setStyleSheet(buttons_css.toString())

        button_help = TipWidget(
            tip_text=help_inline if inline else help_table,
            icon=ima.icon('info_tip'),
            hover_icon=ima.icon('info_tip_hover')
        )

        if inline:
            self._text = ArrayInline(self, options=self._options)
            self._widget = self._text
        else:
            self._table = ArrayTable(self, options=self._options)
            self._widget = self._table

        # Style
        css = qstylizer.style.StyleSheet()
        css.QDialog.setValues(
            margin="0px",
            border=f"1px solid {SpyderPalette.COLOR_BACKGROUND_6}",
            borderRadius=SpyderPalette.SIZE_BORDER_RADIUS,
        )
        self.setStyleSheet(css.toString())

        # widget setup
        self.setWindowFlags(Qt.Window | Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self._widget.setMinimumWidth(200)

        # layout
        if inline:
            buttons_layout = QHBoxLayout()
            buttons_layout.addWidget(button_help, alignment=Qt.AlignVCenter)
            buttons_layout.addWidget(button_ok, alignment=Qt.AlignVCenter)
            buttons_layout.addWidget(button_close, alignment=Qt.AlignVCenter)
        else:
            buttons_layout = QVBoxLayout()
            buttons_layout.addWidget(button_ok)
            buttons_layout.addSpacing(3)
            buttons_layout.addWidget(button_close)
            buttons_layout.addStretch()
            buttons_layout.addWidget(button_help)

        layout = QHBoxLayout()
        layout.setContentsMargins(
            3 * AppStyle.MarginSize,
            3 * AppStyle.MarginSize,
            2 * AppStyle.MarginSize + 1,
            3 * AppStyle.MarginSize
        )
        layout.addWidget(self._widget)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self._widget.setFocus()

    def keyPressEvent(self, event):
        """Override Qt method."""
        QToolTip.hideText()
        shift = event.modifiers() & Qt.ShiftModifier

        if event.key() in [Qt.Key_Enter, Qt.Key_Return] and shift:
            self.accept()
        else:
            super().keyPressEvent(event)

    def event(self, event):
        """
        Override Qt method.

        Useful when in line edit mode.
        """
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Tab:
            return False

        return super().event(event)

    def accept(self):
        self.process_text()
        super().accept()

    def process_text(self):
        """
        Construct the text based on the entered content in the widget.
        """
        prefix = self._options.ARRAY_PREFIX

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
        if not self.is_valid():
            tip = _('Array dimensions are not valid')
            QToolTip.showText(
                self._widget.mapToGlobal(QPoint(3, 18)), tip, self
            )

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
    from spyder.utils.stylesheet import APP_STYLESHEET

    app = qapplication()
    app.setStyleSheet(str(APP_STYLESHEET))

    dlg_table = ArrayBuilderDialog(None, inline=False)
    dlg_inline = ArrayBuilderDialog(None, inline=True)
    dlg_table.show()
    dlg_inline.show()
    app.exec_()


if __name__ == "__main__":  # pragma: no cover
    test()
