# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Completion widget class."""

# Standard library imports
import html
import sys

# Third psrty imports
from qtpy.QtCore import QPoint, Qt, Signal, Slot
from qtpy.QtGui import QFontMetrics, QFocusEvent
from qtpy.QtWidgets import QListWidget, QListWidgetItem, QToolTip

# Local imports
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.utils.icon_manager import ima
from spyder.plugins.completion.api import CompletionItemKind
from spyder.py3compat import to_text_string
from spyder.utils.qthelpers import keyevent_to_keysequence_str
from spyder.widgets.helperwidgets import HTMLDelegate


DEFAULT_COMPLETION_ITEM_HEIGHT = 15
DEFAULT_COMPLETION_ITEM_WIDTH = 250


class CompletionWidget(QListWidget, SpyderConfigurationAccessor):
    """Completion list widget."""
    ITEM_TYPE_MAP = {
        CompletionItemKind.TEXT: 'text',
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
        CompletionItemKind.FILE: 'file',
        CompletionItemKind.REFERENCE: 'reference',
    }
    ICON_MAP = {}

    sig_show_completions = Signal(object)

    # Signal with the info about the current completion item documentation
    # str: completion name
    # str: completion signature/documentation,
    # QPoint: QPoint where the hint should be shown
    sig_completion_hint = Signal(str, str, QPoint)

    def __init__(self, parent, ancestor):
        super(CompletionWidget, self).__init__(ancestor)
        self.textedit = parent
        self._language = None
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.hide()
        self.itemActivated.connect(self.item_selected)
        self.currentRowChanged.connect(self.row_changed)
        self.is_internal_console = False
        self.completion_list = None
        self.completion_position = None
        self.automatic = False
        self.current_selected_item_label = None
        self.current_selected_item_point = None
        self.display_index = []

        # Setup item rendering
        self.setItemDelegate(HTMLDelegate(self, margin=3))
        self.setMinimumWidth(DEFAULT_COMPLETION_ITEM_WIDTH)

        # Initial item height and width
        fm = QFontMetrics(self.textedit.font())
        self.item_height = fm.height()
        self.item_width = self.width()

    def setup_appearance(self, size, font):
        """Setup size and font of the completion widget."""
        self.resize(*size)
        self.setFont(font)

    def is_empty(self):
        """Check if widget is empty."""
        if self.count() == 0:
            return True
        return False

    def show_list(self, completion_list, position, automatic):
        """Show list corresponding to position."""
        self.current_selected_item_label = None
        self.current_selected_item_point = None

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
        self.update_current(new=True)

        # If update_current called close, stop loading
        if not self.completion_list:
            return

        # If only one, must be chosen if not automatic
        single_match = self.count() == 1
        if single_match and not self.automatic:
            self.item_selected(self.item(0))
            # signal used for testing
            self.sig_show_completions.emit(completion_list)
            return

        self.show()
        self.setFocus()
        self.raise_()

        self.textedit.position_widget_at_cursor(self)

        if not self.is_internal_console:
            tooltip_point = self.rect().topRight()
            tooltip_point = self.mapToGlobal(tooltip_point)

            if self.completion_list is not None:
                for completion in self.completion_list:
                    completion['point'] = tooltip_point

        # Show hint for first completion element
        self.setCurrentRow(0)
        self.row_changed(0)

        # signal used for testing
        self.sig_show_completions.emit(completion_list)

    def set_language(self, language):
        """Set the completion language."""
        self._language = language.lower()

    def update_list(self, current_word, new=True):
        """
        Update the displayed list by filtering self.completion_list based on
        the current_word under the cursor (see check_can_complete).

        If we're not updating the list with new completions, we filter out
        textEdit completions, since it's difficult to apply them correctly
        after the user makes edits.

        If no items are left on the list the autocompletion should stop
        """
        self.clear()

        self.display_index = []
        height = self.item_height
        width = self.item_width

        for i, completion in enumerate(self.completion_list):
            if not self.is_internal_console:
                if not new and 'textEdit' in completion:
                    continue
                completion_label = completion['filterText']
            else:
                completion_label = completion[0]

            if not self.check_can_complete(completion_label, current_word):
                continue
            item = QListWidgetItem()

            if not self.is_internal_console:
                self.set_item_display(
                    item, completion, height=height, width=width)
                item.setData(Qt.UserRole, completion)
            else:
                completion_text = self.get_html_item_representation(
                    completion_label, '', height=height, width=width)
                item.setData(Qt.UserRole, completion_label)
                item.setText(completion_text)

            self.addItem(item)
            self.display_index.append(i)

        if self.count() == 0:
            self.hide()

    def _get_cached_icon(self, name):
        if name not in self.ICON_MAP:
            self.ICON_MAP[name] = ima.icon(name)
        return self.ICON_MAP[name]

    def set_item_display(self, item_widget, item_info, height, width):
        """Set item text & icons using the info available."""
        item_type = self.ITEM_TYPE_MAP.get(item_info['kind'], 'no_match')
        item_label = item_info['label']
        icon_provider = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0l"
                         "EQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
        img_height = height - 2
        img_width = img_height * 0.8

        icon_provider, icon_scale = item_info.get('icon', (None, 1))
        if icon_provider is not None:
            icon_height = img_height
            icon_width = icon_scale * icon_height
            icon_provider = ima.icon(icon_provider)
            icon_provider = ima.base64_from_icon_obj(
                icon_provider, icon_width, icon_height)

        item_text = self.get_html_item_representation(
            item_label, item_type, icon_provider=icon_provider,
            img_height=img_height, img_width=img_width, height=height,
            width=width)

        item_widget.setText(item_text)
        item_widget.setIcon(self._get_cached_icon(item_type))

        # Set data for accessible readers using item label and type
        # See spyder-ide/spyder#17047 and
        # https://doc.qt.io/qt-5/qt.html#ItemDataRole-enum
        item_widget.setData(Qt.AccessibleTextRole, f"{item_label} {item_type}")

    def get_html_item_representation(self, item_completion, item_type,
                                     icon_provider=None,
                                     img_height=0,
                                     img_width=0,
                                     height=DEFAULT_COMPLETION_ITEM_HEIGHT,
                                     width=DEFAULT_COMPLETION_ITEM_WIDTH):
        """Get HTML representation of and item."""
        height = to_text_string(height)
        width = to_text_string(width)

        # Unfortunately, both old- and new-style Python string formatting
        # have poor performance due to being implemented as functions that
        # parse the format string.
        # f-strings in new versions of Python are fast due to Python
        # compiling them into efficient string operations, but to be
        # compatible with old versions of Python, we manually join strings.
        parts = [
            '<table width="', width, '" height="', height, '">', '<tr>',

            '<td valign="middle" style="color:' + ima.MAIN_FG_COLOR + '">',
            html.escape(item_completion).replace(' ', '&nbsp;'),
            '</td>',

            '<td valign="middle" align="right" float="right" style="color:',
            ima.MAIN_FG_COLOR, '">',
            item_type,
            '</td>',
        ]
        if icon_provider is not None:
            img_height = to_text_string(img_height)
            img_width = to_text_string(img_width)

            parts.extend([
                '<td valign="top" align="right" float="right" width="',
                img_width, '">',
                '<img src="data:image/png;base64, ', icon_provider,
                '" height="', img_height, '" width="', img_width, '"/>',
                '</td>',
            ])
        parts.extend([
            '</tr>', '</table>',
        ])

        return ''.join(parts)

    def hide(self, focus_to_parent=True):
        """Override Qt method."""
        self.completion_position = None
        self.completion_list = None
        self.clear()

        # Used to control when to give focus to its parent.
        # This is necessary to have a better fix than the initially
        # proposed for issue spyder-ide/spyder#11502.
        if focus_to_parent:
            self.textedit.setFocus()

        tooltip = getattr(self.textedit, 'tooltip_widget', None)
        if tooltip:
            tooltip.hide()

        QListWidget.hide(self)
        QToolTip.hideText()

    def keyPressEvent(self, event):
        """Override Qt method to process keypress."""
        text, key = event.text(), event.key()
        alt = event.modifiers() & Qt.AltModifier
        shift = event.modifiers() & Qt.ShiftModifier
        ctrl = event.modifiers() & Qt.ControlModifier
        altgr = event.modifiers() and (key == Qt.Key_AltGr)

        # Needed to properly handle Neo2 and other keyboard layouts
        # See spyder-ide/spyder#11293
        neo2_level4 = (key == 0)  # AltGr (ISO_Level5_Shift) in Neo2 on Linux
        modifier = shift or ctrl or alt or altgr or neo2_level4

        if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
            # Check that what was selected can be selected,
            # otherwise timing issues
            item = self.currentItem()
            if item is None:
                item = self.item(0)

            if self.is_up_to_date(item=item):
                self.item_selected(item=item)
            else:
                self.hide()
                self.textedit.keyPressEvent(event)
        elif key == Qt.Key_Escape:
            self.hide()
        elif key in (Qt.Key_Left, Qt.Key_Right) or text in ('.', ':'):
            self.hide()
            self.textedit.keyPressEvent(event)
        elif (
            key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown)
            and not modifier
        ):
            self.textedit._completions_hint_idle = True
            if key == Qt.Key_Up and self.currentRow() == 0:
                self.setCurrentRow(self.count() - 1)
            elif key == Qt.Key_Down and self.currentRow() == self.count()-1:
                self.setCurrentRow(0)
            else:
                QListWidget.keyPressEvent(self, event)
        elif key in (Qt.Key_Home, Qt.Key_End):
            # This allows users to easily move to the beginning/end of the
            # current line when this widget is visible.
            # Fixes spyder-ide/spyder#19989
            self.hide()
            self.textedit.keyPressEvent(event)
        elif key == Qt.Key_Backspace:
            self.textedit.keyPressEvent(event)
            self.update_current(new=False)
        elif len(text):
            # Determine the key sequence introduced by the user to check if
            # we need to call the action associated to it in textedit. This
            # way is not necessary to hide this widget for the sequence to
            # take effect in textedit.
            # Fixes spyder-ide/spyder#19372
            if modifier:
                key_sequence = keyevent_to_keysequence_str(event)

                # Ask to save file if the user pressed the sequence for that.
                # Fixes spyder-ide/spyder#14806
                save_shortcut = self.get_conf(
                    'editor/save file', section='shortcuts')
                if key_sequence == save_shortcut:
                    self.textedit.sig_save_requested.emit()

                    # Hiding the widget reassures users that the save operation
                    # took place.
                    self.hide()

            self.textedit.keyPressEvent(event)
            self.update_current(new=False)
        elif modifier:
            self.textedit.keyPressEvent(event)
        else:
            self.hide()
            QListWidget.keyPressEvent(self, event)

    def is_up_to_date(self, item=None):
        """
        Check if the selection is up to date.
        """
        if self.is_empty():
            return False
        if not self.is_position_correct():
            return False
        if item is None:
            item = self.currentItem()
        current_word = self.textedit.get_current_word(completion=True)
        completion = item.data(Qt.UserRole)
        if isinstance(completion, dict):
            filter_text = completion['filterText']
        else:
            filter_text = completion
        return self.check_can_complete(filter_text, current_word)

    def check_can_complete(self, filter_text, current_word):
        """Check if current_word matches filter_text."""
        if not filter_text:
            return True

        if not current_word:
            return True

        return to_text_string(filter_text).lower().startswith(
                to_text_string(current_word).lower())

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

    def update_current(self, new=False):
        """
        Update the displayed list.
        """
        if not self.is_position_correct():
            self.hide()
            return

        current_word = self.textedit.get_current_word(completion=True)
        self.update_list(current_word, new=new)

    def focusOutEvent(self, event):
        """Override Qt method."""

        # Type check: Prevent error in PySide where 'event' may be of type
        # QtGui.QPainter (for whatever reason).
        if type(event) is not QFocusEvent:
            return

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
            self.textedit.insert_completion(item.data(Qt.UserRole),
                                            self.completion_position)
        self.hide()

    def _get_insert_text(self, item):
        if 'textEdit' in item:
            insert_text = item['textEdit']['newText']
        else:
            insert_text = item['insertText']

            # Split by starting $ or language specific chars
            chars = ['$']
            if self._language == 'python':
                chars.append('(')

            for ch in chars:
                insert_text = insert_text.split(ch)[0]
        return insert_text

    def trigger_completion_hint(self, row=None):
        self.current_selected_item_label = None
        self.current_selected_item_point = None

        if not self.completion_list:
            return
        if row is None:
            row = self.currentRow()
        if row < 0 or len(self.completion_list) <= row:
            return

        item = self.completion_list[row]
        if 'point' not in item:
            return

        self.current_selected_item_label = item['label']
        self.current_selected_item_point = item['point']

        insert_text = self._get_insert_text(item)

        if hasattr(self.textedit, 'resolve_completion_item'):
            if item.get('resolve', False):
                to_resolve = item.copy()
                to_resolve.pop('point')
                to_resolve.pop('resolve')
                self.textedit.resolve_completion_item(to_resolve)

        if isinstance(item['documentation'], dict):
            item['documentation'] = item['documentation']['value']

        self.sig_completion_hint.emit(
            insert_text,
            item['documentation'],
            item['point'])

    def augment_completion_info(self, item):
        if self.current_selected_item_label == item['label']:
            insert_text = self._get_insert_text(item)

            if isinstance(item['documentation'], dict):
                item['documentation'] = item['documentation']['value']

            self.sig_completion_hint.emit(
                insert_text,
                item['documentation'],
                self.current_selected_item_point)

    @Slot(int)
    def row_changed(self, row):
        """Set completion hint info and show it."""
        self.trigger_completion_hint(row)
