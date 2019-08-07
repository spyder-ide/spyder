# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Completion widget class"""

# Standard library imports
import sys

# Third psrty imports
from qtpy.QtCore import QPoint, Qt, Signal, Slot
from qtpy.QtGui import QFontMetrics
from qtpy.QtWidgets import (QAbstractItemView, QApplication, QListWidget,
                            QListWidgetItem, QToolTip)

# Local imports
from spyder.utils import icon_manager as ima
from spyder.plugins.completion.languageserver import CompletionItemKind
from spyder.py3compat import to_text_string
from spyder.widgets.helperwidgets import HTMLDelegate


COMPLETION_ITEM_TEMPLATE = """
<table width="{width}" height="{height}">
    <tr>
        <td valign="middle" style="color:{color}">
            {completion}
        </td>

        <td valign="middle" align="right" float="right" style="color:{color}">
            {type}
        </td>
    </tr>
</table>
"""
DEFAULT_COMPLETION_ITEM_HEIGHT = 15
DEFAULT_COMPLETION_ITEM_WIDTH = 250


class CompletionWidget(QListWidget):
    """Completion list widget"""

    sig_show_completions = Signal(object)

    def __init__(self, parent, ancestor):
        QListWidget.__init__(self, ancestor)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.textedit = parent
        self.hide()
        self.itemActivated.connect(self.item_selected)
        self.currentRowChanged.connect(self.row_changed)
        self.is_internal_console = False
        self.completion_list = None
        self.completion_position = None
        self.automatic = False

        # Setup item rendering
        self.setItemDelegate(HTMLDelegate(self, margin=3))
        self.setMinimumWidth(DEFAULT_COMPLETION_ITEM_WIDTH)

        # Initial item height and width
        fm = QFontMetrics(self.textedit.font())
        self.item_height = fm.height()
        self.item_width = self.width()

        # Text to be displayed if no match is found.
        self.empty_text = self.get_html_item_representation(
            'No match', '',
            height=self.item_height,
            width=self.item_width)

    def setup_appearance(self, size, font):
        self.resize(*size)
        self.setFont(font)

    def is_empty(self):
        """Check if widget is empty."""
        if self.count() == 0:
            return True
        if self.count() == 1 and self.item(0).text() == self.empty_text:
            return True
        return False

    def show_list(self, completion_list, position, automatic):
        """Show list corresponding to position."""

        if not completion_list:
            self.hide()
            return

        self.automatic = automatic

        if position is None:
            # Somehow the position was not saved.
            # Hope that the current position is still valid
            self.completion_position = self.textedit.textCursor().position()

        elif self.textedit.textCursor().position() < position:
            # hide the text as we moved away from the position
            self.hide()
            return

        else:
            self.completion_position = position

        # Completions are handled differently for the Internal
        # console.
        if not isinstance(completion_list[0], dict):
            self.is_internal_console = True
        self.completion_list = completion_list
        # Check everything is in order
        self.update_current()

        # If update_current called close, stop loading
        if not self.completion_list:
            return

        # If only one, must be chosen if not automatic
        single_match = (self.count() == 1 and
                        self.item(0).text() != self.empty_text)
        if single_match and not self.automatic:
            self.item_selected()
            self.hide()
            # signal used for testing
            self.sig_show_completions.emit(completion_list)
            return

        self.show()
        self.setFocus()
        self.raise_()

        # Retrieving current screen height
        desktop = QApplication.desktop()
        srect = desktop.availableGeometry(desktop.screenNumber(self))
        screen_right = srect.right()
        screen_bottom = srect.bottom()

        point = self.textedit.cursorRect().bottomRight()
        point = self.textedit.calculate_real_position(point)
        point = self.textedit.mapToGlobal(point)

        # Computing completion widget and its parent right positions
        comp_right = point.x() + self.width()
        ancestor = self.parent()
        if ancestor is None:
            anc_right = screen_right
        else:
            anc_right = min([ancestor.x() + ancestor.width(), screen_right])

        # Moving completion widget to the left
        # if there is not enough space to the right
        if comp_right > anc_right:
            point.setX(point.x() - self.width())

        # Computing completion widget and its parent bottom positions
        comp_bottom = point.y() + self.height()
        ancestor = self.parent()
        if ancestor is None:
            anc_bottom = screen_bottom
        else:
            anc_bottom = min([ancestor.y() + ancestor.height(), screen_bottom])

        # Moving completion widget above if there is not enough space below
        x_position = point.x()
        if comp_bottom > anc_bottom:
            point = self.textedit.cursorRect().topRight()
            point = self.textedit.mapToGlobal(point)
            point.setX(x_position)
            point.setY(point.y() - self.height())

        if ancestor is not None:
            # Useful only if we set parent to 'ancestor' in __init__
            point = ancestor.mapFromGlobal(point)
        self.move(point)

        if not self.is_internal_console:
            tooltip_point = QPoint(point)
            tooltip_point.setX(point.x() + self.width())
            tooltip_point.setY(point.y() - (3 * self.height()) // 4)
            for completion in completion_list:
                completion['point'] = tooltip_point

        # signal used for testing
        self.sig_show_completions.emit(completion_list)

    def update_list(self, filter_text):
        """
        Update the displayed list by filtering self.completion_list.

        If returns False, the autocompletion should stop.
        """
        self.clear()
        icons_map = {CompletionItemKind.TEXT: 'text',
                     CompletionItemKind.METHOD: 'method',
                     CompletionItemKind.FUNCTION: 'function',
                     CompletionItemKind.CONSTRUCTOR: 'constructor',
                     CompletionItemKind.FIELD: 'field',
                     CompletionItemKind.VARIABLE: 'variable',
                     CompletionItemKind.CLASS: 'class',
                     CompletionItemKind.INTERFACE: 'interface',
                     CompletionItemKind.MODULE: 'module',
                     CompletionItemKind.PROPERTY: 'property',
                     CompletionItemKind.UNIT: 'unit',
                     CompletionItemKind.VALUE: 'value',
                     CompletionItemKind.ENUM: 'enum',
                     CompletionItemKind.KEYWORD: 'keyword',
                     CompletionItemKind.SNIPPET: 'snippet',
                     CompletionItemKind.COLOR: 'color',
                     CompletionItemKind.FILE: 'filenew',
                     CompletionItemKind.REFERENCE: 'reference',
                     }

        height = self.item_height
        width = self.item_width

        for completion in self.completion_list:
            if not self.is_internal_console:
                completion_label = completion['filterText']
                icon = icons_map.get(completion['kind'], 'no_match')
                completion_data = completion['insertText']
                completion_text = self.get_html_item_representation(
                    completion_data, icon, height=height, width=width)
                item = QListWidgetItem(ima.icon(icon),
                                       completion_text)
                item.setData(Qt.UserRole, completion_data)
            else:
                completion_label = completion[0]
                completion_text = self.get_html_item_representation(
                    completion_label, '', height=height, width=width)
                item = QListWidgetItem()
                item.setData(Qt.UserRole, completion_label)
                item.setText(completion_text)

            if self.check_can_complete(
                    completion_label, filter_text):
                self.addItem(item)

        if self.count() > 0:
            self.setCurrentRow(0)
            self.scrollTo(self.currentIndex(),
                          QAbstractItemView.PositionAtTop)
        else:
            self.addItem(QListWidgetItem(self.empty_text))

    def get_html_item_representation(self, item_completion, item_type,
                                     height=DEFAULT_COMPLETION_ITEM_HEIGHT,
                                     width=DEFAULT_COMPLETION_ITEM_WIDTH):
        """Get HTML representation of and item."""

        return COMPLETION_ITEM_TEMPLATE.format(completion=item_completion,
                                               type=item_type,
                                               color=ima.MAIN_FG_COLOR,
                                               height=height,
                                               width=width)

    def hide(self):
        """Hide the widget."""
        self.completion_position = None
        self.completion_list = None
        self.clear()
        QToolTip.hideText()
        QListWidget.hide(self)
        self.textedit.setFocus()

    def keyPressEvent(self, event):
        """Process keypress."""
        text, key = event.text(), event.key()
        alt = event.modifiers() & Qt.AltModifier
        shift = event.modifiers() & Qt.ShiftModifier
        ctrl = event.modifiers() & Qt.ControlModifier
        modifier = shift or ctrl or alt
        if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
            # Check that what was selected can be selected,
            # otherwise timing issues
            if self.up_to_date():
                self.item_selected()
            else:
                self.hide()
                self.textedit.keyPressEvent(event)
        elif key == Qt.Key_Escape:
            self.hide()
        elif key in (Qt.Key_Left, Qt.Key_Right) or text in ('.', ':'):
            self.hide()
            self.textedit.keyPressEvent(event)
        elif key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown,
                     Qt.Key_Home, Qt.Key_End,
                     Qt.Key_CapsLock) and not modifier:
            if key == Qt.Key_Up and self.currentRow() == 0:
                self.setCurrentRow(self.count() - 1)
            elif key == Qt.Key_Down and self.currentRow() == self.count()-1:
                self.setCurrentRow(0)
            else:
                QListWidget.keyPressEvent(self, event)
        elif len(text) or key == Qt.Key_Backspace:
            self.textedit.keyPressEvent(event)
            self.update_current()
        elif modifier:
            self.textedit.keyPressEvent(event)
        else:
            self.hide()
            QListWidget.keyPressEvent(self, event)

    def up_to_date(self):
        """
        Check if the selection is up to date.
        """
        if self.is_empty():
            return False
        if not self.is_position_correct():
            return False
        completion_text = self.textedit.get_current_word(completion=True)
        selected_text = self.currentItem().data(Qt.UserRole)
        return self.check_can_complete(selected_text, completion_text)

    def check_can_complete(self, text, sub):
        """Check if sub can be completed to text."""
        if not sub:
            return True
        return to_text_string(text).lower().startswith(
                to_text_string(sub).lower())

    def is_position_correct(self):
        """Check if the position is correct."""

        if self.completion_position is None:
            return False

        cursor_position = self.textedit.textCursor().position()

        # Can only go forward from the data we have
        if cursor_position < self.completion_position:
            return False

        completion_text = self.textedit.get_current_word_and_position(
            completion=True)

        # If no text found, we must be at self.completion_position
        if completion_text is None:
            if self.completion_position == cursor_position:
                return True
            else:
                return False

        completion_text, text_position = completion_text
        completion_text = to_text_string(completion_text)

        # The position of text must compatible with completion_position
        if not text_position <= self.completion_position <= (
                text_position + len(completion_text)):
            return False

        return True

    def update_current(self):
        """
        Update the displayed list.
        """
        if not self.is_position_correct():
            self.hide()
            return

        completion_text = self.textedit.get_current_word(completion=True)
        self.update_list(completion_text)

    def focusOutEvent(self, event):
        event.ignore()
        # Don't hide it on Mac when main window loses focus because
        # keyboard input is lost.
        # Fixes spyder-ide/spyder#1318.
        if sys.platform == "darwin":
            if event.reason() != Qt.ActiveWindowFocusReason:
                self.hide()
        else:
            # Avoid an error when running tests that show
            # the completion widget
            try:
                self.hide()
            except RuntimeError:
                pass

    def item_selected(self, item=None):
        """Perform the item selected action."""
        if item is None:
            item = self.currentItem()

        if item is not None and self.completion_position is not None:
            self.textedit.insert_completion(
                to_text_string(item.data(Qt.UserRole)),
                self.completion_position)
        self.hide()

    @Slot(int)
    def row_changed(self, row):
        if self.completion_list:
            item = self.completion_list[row]
            if len(item['documentation']) > 0:
                # TODO: LSP - Define an UI element to display the documentation
                # self.textedit.show_calltip(
                #     item['detail'], item['documentation'], color='#daa520',
                #     at_point=item['point'])
                return
        QToolTip.hideText()
