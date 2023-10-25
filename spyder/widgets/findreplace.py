# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Find/Replace widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import re

# Third party imports
from qtpy.QtCore import QEvent, QSize, Qt, QTimer, Signal, Slot
from qtpy.QtGui import QPixmap, QTextCursor
from qtpy.QtWidgets import (QAction, QGridLayout, QHBoxLayout, QLabel,
                            QLineEdit, QToolButton, QSizePolicy, QSpacerItem,
                            QWidget)

# Local imports
from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.py3compat import to_text_string
from spyder.utils.icon_manager import ima
from spyder.utils.misc import regexp_error_msg
from spyder.plugins.editor.utils.editor import TextHelper
from spyder.utils.qthelpers import create_toolbutton
from spyder.utils.sourcecode import get_eol_chars
from spyder.widgets.comboboxes import PatternComboBox


def is_position_sup(pos1, pos2):
    """Return True is pos1 > pos2"""
    return pos1 > pos2

def is_position_inf(pos1, pos2):
    """Return True is pos1 < pos2"""
    return pos1 < pos2


class SearchText(PatternComboBox):

    def __init__(self, parent):
        self.recommended_width = 400
        super().__init__(parent, adjust_to_minimum=False)

    def sizeHint(self):
        """Recommended size."""
        return QSize(self.recommended_width, 10)


class FindReplace(QWidget):
    """Find widget"""
    TOOLTIP = {
        'regexp_error': _("Regular expression error"),
        'no_matches': _("No matches")
    }

    visibility_changed = Signal(bool)
    return_shift_pressed = Signal()
    return_pressed = Signal()

    def __init__(self, parent, enable_replace=False):
        QWidget.__init__(self, parent)
        self.enable_replace = enable_replace
        self.editor = None
        self.is_code_editor = None

        glayout = QGridLayout()
        glayout.setContentsMargins(6, 3, 6, 3)
        self.setLayout(glayout)

        self.close_button = create_toolbutton(
            self,
            triggered=self.hide,
            icon=ima.icon('DialogCloseButton')
        )
        glayout.addWidget(self.close_button, 0, 0)

        # Icon size is the same for all buttons
        self.icon_size = self.close_button.iconSize()

        # Find layout
        self.search_text = SearchText(self)

        self.return_shift_pressed.connect(
            lambda:
            self.find(changed=False, forward=False, rehighlight=False,
                      multiline_replace_check = False)
        )

        self.return_pressed.connect(
            lambda:
            self.find(changed=False, forward=True, rehighlight=False,
                      multiline_replace_check = False)
        )

        self.search_text.lineEdit().textEdited.connect(
            self.text_has_been_edited)
        self.search_text.sig_resized.connect(self._resize_replace_text)

        self.number_matches_text = QLabel(self)
        self.search_text.clear_action.triggered.connect(self.clear_matches)
        self.hide_number_matches_text = False
        self.number_matches_pixmap = (
            ima.icon('number_matches').pixmap(self.icon_size)
        )
        self.matches_string = ""

        self.no_matches_icon = ima.icon('no_matches')
        self.error_icon = ima.icon('error')
        self.messages_action = QAction(self)
        self.messages_action.setVisible(False)
        self.search_text.lineEdit().addAction(
            self.messages_action, QLineEdit.TrailingPosition)

        # Button corresponding to the messages_action above
        self.messages_button = (
            self.search_text.lineEdit().findChildren(QToolButton)[1]
        )

        self.replace_on = False
        self.replace_text_button = create_toolbutton(
            self,
            toggled=self.change_replace_state,
            icon=ima.icon('replace'),
            tip=_("Replace text")
        )
        if not self.enable_replace:
            self.replace_text_button.hide()

        self.previous_button = create_toolbutton(
            self,
            triggered=self.find_previous,
            icon=ima.icon('findprevious'),
            tip=_("Find previous")
        )

        self.next_button = create_toolbutton(
            self,
            triggered=self.find_next,
            icon=ima.icon('findnext'),
            tip=_("Find next")
        )
        self.next_button.clicked.connect(self.update_search_combo)
        self.previous_button.clicked.connect(self.update_search_combo)

        self.re_button = create_toolbutton(
            self, icon=ima.icon('regex'),
            tip=_("Use regular expressions")
        )
        self.re_button.setCheckable(True)
        self.re_button.toggled.connect(lambda state: self.find())

        self.case_button = create_toolbutton(
            self,
            icon=ima.icon("format_letter_case"),
            tip=_("Enable case sensitive searches")
        )
        self.case_button.setCheckable(True)
        self.case_button.toggled.connect(lambda state: self.find())

        self.words_button = create_toolbutton(
            self,
            icon=ima.icon("format_letter_matches"),
            tip=_("Only search for whole words")
        )
        self.words_button.setCheckable(True)
        self.words_button.toggled.connect(lambda state: self.find())

        self.widgets = [
            self.close_button,
            self.search_text,
            self.previous_button,
            self.next_button,
            self.re_button,
            self.case_button,
            self.words_button,
            self.replace_text_button,
            self.number_matches_text,
        ]

        # Search layout
        search_layout = QHBoxLayout()
        for widget in self.widgets[1:-1]:
            search_layout.addWidget(widget)

        search_layout.addSpacerItem(QSpacerItem(10, 0))
        search_layout.addWidget(self.number_matches_text)
        search_layout.addSpacerItem(
            QSpacerItem(6, 0, QSizePolicy.Expanding)
        )

        glayout.addLayout(search_layout, 0, 1)

        # Replace layout
        self.replace_text = PatternComboBox(
            self,
            adjust_to_minimum=False
        )
        self.replace_text.valid.connect(
            lambda _: self.replace_find(focus_replace_text=True))
        self.replace_text.lineEdit().setPlaceholderText(_("Replace"))

        self.replace_button = create_toolbutton(
            self,
            tip=_('Replace next occurrence'),
            icon=ima.icon('replace_next'),
            triggered=self.replace_find,
        )

        self.replace_sel_button = create_toolbutton(
            self,
            tip=_('Replace occurrences in selection'),
            icon=ima.icon('replace_selection'),
            triggered=self.replace_find_selection,
        )
        self.replace_sel_button.clicked.connect(self.update_replace_combo)
        self.replace_sel_button.clicked.connect(self.update_search_combo)

        self.replace_all_button = create_toolbutton(
            self,
            tip=_('Replace all occurrences'),
            icon=ima.icon('replace_all'),
            triggered=self.replace_find_all,
        )
        self.replace_all_button.clicked.connect(self.update_replace_combo)
        self.replace_all_button.clicked.connect(self.update_search_combo)

        replace_layout = QHBoxLayout()
        widgets = [
            self.replace_text,
            self.replace_button,
            self.replace_sel_button,
            self.replace_all_button
        ]
        for widget in widgets:
            replace_layout.addWidget(widget)
        replace_layout.addStretch(1)
        glayout.addLayout(replace_layout, 1, 1)
        self.widgets.extend(widgets)
        self.replace_widgets = widgets
        self.hide_replace()

        # Additional adjustments
        self.search_text.setTabOrder(self.search_text, self.replace_text)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.shortcuts = self.create_shortcuts(parent)

        # To highlight found results in the editor
        self.highlight_timer = QTimer(self)
        self.highlight_timer.setSingleShot(True)
        self.highlight_timer.setInterval(300)
        self.highlight_timer.timeout.connect(self.highlight_matches)

        # Install event filter for search_text
        self.search_text.installEventFilter(self)

        # To avoid painting number_matches_text on every resize event
        self.show_matches_timer = QTimer(self)
        self.show_matches_timer.setSingleShot(True)
        self.show_matches_timer.setInterval(25)
        self.show_matches_timer.timeout.connect(self.show_matches)

    def eventFilter(self, widget, event):
        """
        Event filter for search_text widget.

        Notes
        -----
        * Emit signals when Enter and Shift+Enter are pressed. These signals
          are used for search forward and backward.
        * Add crude hack to get tab working between the find/replace boxes.
        * Reduce space between the messages_button and the clear one.
        """

        # Type check: Prevent error in PySide where 'event' may be of type
        # QtGui.QPainter (for whatever reason).
        if not isinstance(event, QEvent):
            return True

        if event.type() == QEvent.KeyPress:
            key = event.key()
            shift = event.modifiers() & Qt.ShiftModifier

            if key == Qt.Key_Return:
                if shift:
                    self.return_shift_pressed.emit()
                else:
                    self.return_pressed.emit()

            if key == Qt.Key_Tab:
                if self.search_text.hasFocus():
                    self.replace_text.set_current_text(
                        self.search_text.currentText())
                self.focusNextChild()

        if event.type() == QEvent.Paint:
            self.messages_button.move(
                self.search_text.lineEdit().width() - 42,
                self.messages_button.y()
            )

        return super().eventFilter(widget, event)

    def create_shortcuts(self, parent):
        """Create shortcuts for this widget"""
        # Configurable
        findnext = CONF.config_shortcut(
            self.find_next,
            context='find_replace',
            name='Find next',
            parent=parent)

        findprev = CONF.config_shortcut(
            self.find_previous,
            context='find_replace',
            name='Find previous',
            parent=parent)

        togglefind = CONF.config_shortcut(
            self.show,
            context='find_replace',
            name='Find text',
            parent=parent)

        togglereplace = CONF.config_shortcut(
            self.show_replace,
            context='find_replace',
            name='Replace text',
            parent=parent)

        hide = CONF.config_shortcut(
            self.hide,
            context='find_replace',
            name='hide find and replace',
            parent=self)

        return [findnext, findprev, togglefind, togglereplace, hide]

    def get_shortcut_data(self):
        """
        Returns shortcut data, a list of tuples (shortcut, text, default)
        shortcut (QShortcut or QAction instance)
        text (string): action/shortcut description
        default (string): default key sequence
        """
        return [sc.data for sc in self.shortcuts]

    def update_search_combo(self):
        self.search_text.lineEdit().returnPressed.emit()

    def update_replace_combo(self):
        self.replace_text.lineEdit().returnPressed.emit()

    def show(self, hide_replace=True):
        """Overrides Qt Method"""
        QWidget.show(self)

        self._width_adjustments()
        self.visibility_changed.emit(True)
        self.change_number_matches()

        if self.editor is not None:
            if hide_replace:
                if self.replace_widgets[0].isVisible():
                    self.hide_replace()
            else:
                self.replace_text_button.setChecked(True)

            # When selecting several lines, and replace box is activated the
            # text won't be replaced for the selection
            text = self.editor.get_selected_text()
            if hide_replace or len(text.splitlines()) <= 1:
                highlighted = True
                # If no text is highlighted for search, use whatever word is
                # under the cursor
                if not text:
                    highlighted = False
                    try:
                        cursor = self.editor.textCursor()
                        cursor.select(QTextCursor.WordUnderCursor)
                        text = to_text_string(cursor.selectedText())
                    except AttributeError:
                        # We can't do this for all widgets, e.g. WebView's
                        pass

                # Now that text value is sorted out, use it for the search
                if text and not self.search_text.currentText() or highlighted:
                    self.search_text.setEditText(text)
                    self.search_text.lineEdit().selectAll()
                    self.refresh()
                else:
                    self.search_text.lineEdit().selectAll()
            self.search_text.setFocus()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._width_adjustments()

    @Slot()
    def replace_widget(self, replace_on):
        """Show and hide replace widget"""
        if replace_on:
            self.show_replace()
        else:
            self.hide_replace()

    def change_replace_state(self):
        """Handle the change of the replace state widget."""
        self.replace_on = not self.replace_on
        self.replace_text_button.setChecked(self.replace_on)
        self.replace_widget(self.replace_on)

    def hide(self):
        """Overrides Qt Method"""
        for widget in self.replace_widgets:
            widget.hide()
        QWidget.hide(self)
        self.replace_text_button.setChecked(False)
        self.visibility_changed.emit(False)
        if self.editor is not None:
            self.editor.setFocus()
            self.clear_matches()

    def show_replace(self):
        """Show replace widgets"""
        if self.enable_replace:
            self.show(hide_replace=False)
            for widget in self.replace_widgets:
                widget.show()

    def hide_replace(self):
        """Hide replace widgets"""
        for widget in self.replace_widgets:
            widget.hide()
            self.replace_text_button.setChecked(False)

    def refresh(self):
        """Refresh widget"""
        if self.isHidden():
            if self.editor is not None:
                self.clear_matches()
            return
        state = self.editor is not None
        for widget in self.widgets:
            widget.setEnabled(state)
        if state:
            self.find()

    def set_editor(self, editor, refresh=True):
        """Set associated editor."""
        # Note: This is necessary to test widgets/editor.py in Qt builds that
        # don't have web widgets
        try:
            from qtpy.QtWebEngineWidgets import QWebEngineView
        except ImportError:
            QWebEngineView = type(None)
        from spyder.plugins.editor.widgets.codeeditor import CodeEditor

        self.words_button.setVisible(not isinstance(editor, QWebEngineView))
        self.re_button.setVisible(not isinstance(editor, QWebEngineView))
        self.is_code_editor = isinstance(editor, CodeEditor)

        # Disconnect previous connection to highlight matches
        if self.editor is not None and self.is_code_editor:
            self.editor.textChanged.disconnect(self.update_matches)

        # Set current editor
        self.editor = editor

        # Keep number of matches updated if editor text has changed
        if self.is_code_editor:
            self.editor.textChanged.connect(self.update_matches)

        if refresh:
            self.refresh()
        if self.isHidden() and editor is not None:
            self.clear_matches()

    @Slot()
    def find_next(self, set_focus=True):
        """Find next occurrence"""
        state = self.find(changed=False, forward=True, rehighlight=False,
                          multiline_replace_check=False)
        if set_focus:
            self.editor.setFocus()
        self.search_text.add_current_text()
        return state

    @Slot()
    def find_previous(self, set_focus=True):
        """Find previous occurrence"""
        state = self.find(changed=False, forward=False, rehighlight=False,
                          multiline_replace_check=False)
        if set_focus:
            self.editor.setFocus()
        return state

    def text_has_been_edited(self, text):
        """
        Find text has been edited (this slot won't be triggered when setting
        the search pattern combo box text programmatically).
        """
        self.find(changed=True, forward=True, start_highlight_timer=True)

    def highlight_matches(self):
        """Highlight found results"""
        if self.is_code_editor:
            text = self.search_text.currentText()
            case = self.case_button.isChecked()
            word = self.words_button.isChecked()
            regexp = self.re_button.isChecked()
            self.editor.highlight_found_results(
                text, word=word, regexp=regexp, case=case)

    def clear_matches(self):
        """Clear all highlighted matches"""
        self.matches_string = ""
        self.messages_action.setVisible(False)
        self.number_matches_text.hide()
        if self.is_code_editor:
            self.editor.clear_found_results()

    def find(self, changed=True, forward=True, rehighlight=True,
             start_highlight_timer=False, multiline_replace_check=True):
        """Call the find function"""
        # When several lines are selected in the editor and replace box is
        # activated, dynamic search is deactivated to prevent changing the
        # selection. Otherwise we show matching items.
        if multiline_replace_check and self.replace_widgets[0].isVisible():
            sel_text = self.editor.get_selected_text()
            if len(to_text_string(sel_text).splitlines()) > 1:
                return None
        text = self.search_text.currentText()
        if len(text) == 0:
            if not self.is_code_editor:
                # Clears the selection for WebEngine
                self.editor.find_text('')
            self.change_number_matches()
            self.clear_matches()
            return None
        else:
            case = self.case_button.isChecked()
            word = self.words_button.isChecked()
            regexp = self.re_button.isChecked()
            found = self.editor.find_text(text, changed, forward, case=case,
                                          word=word, regexp=regexp)

            error_msg = False
            if not found and regexp:
                error_msg = regexp_error_msg(text)
                if error_msg:
                    self.show_error(error_msg)

            # No need to continue after this point if we detected an error in
            # the passed regexp.
            if error_msg:
                return

            if self.is_code_editor and found:
                cursor = QTextCursor(self.editor.textCursor())
                TextHelper(self.editor).unfold_if_colapsed(cursor)

                if rehighlight or not self.editor.found_results:
                    self.highlight_timer.stop()
                    if start_highlight_timer:
                        self.highlight_timer.start()
                    else:
                        self.highlight_matches()
            else:
                self.clear_matches()

            number_matches = self.editor.get_number_matches(text, case=case,
                                                            regexp=regexp,
                                                            word=word)
            if hasattr(self.editor, 'get_match_number'):
                match_number = self.editor.get_match_number(text, case=case,
                                                            regexp=regexp,
                                                            word=word)
            else:
                match_number = 0
            self.change_number_matches(current_match=match_number,
                                       total_matches=number_matches)
            return found

    @Slot()
    def replace_find(self, focus_replace_text=False):
        """Replace and find."""
        if self.editor is None:
            return
        replace_text = to_text_string(self.replace_text.currentText())
        search_text = to_text_string(self.search_text.currentText())
        re_pattern = None
        case = self.case_button.isChecked()
        re_flags = re.MULTILINE if case else re.IGNORECASE | re.MULTILINE

        # Check regexp before proceeding
        if self.re_button.isChecked():
            try:
                re_pattern = re.compile(search_text, flags=re_flags)
                # Check if replace_text can be substituted in re_pattern
                # Fixes spyder-ide/spyder#7177.
                re_pattern.sub(replace_text, '')
            except re.error:
                # Do nothing with an invalid regexp
                return

        # First found
        seltxt = to_text_string(self.editor.get_selected_text())
        cmptxt1 = search_text if case else search_text.lower()
        cmptxt2 = seltxt if case else seltxt.lower()
        do_replace = True
        if re_pattern is None:
            has_selected = self.editor.has_selected_text()
            if not has_selected or cmptxt1 != cmptxt2:
                if not self.find(changed=False, forward=True,
                                 rehighlight=False):
                    do_replace = False
        else:
            if len(re_pattern.findall(cmptxt2)) <= 0:
                if not self.find(changed=False, forward=True,
                                 rehighlight=False):
                    do_replace = False
        cursor = None
        if do_replace:
            cursor = self.editor.textCursor()
            cursor.beginEditBlock()

            if re_pattern is None:
                cursor.removeSelectedText()
                cursor.insertText(replace_text)
            else:
                seltxt = to_text_string(cursor.selectedText())

                # Note: If the selection obtained from an editor spans a line
                # break, the text will contain a Unicode U+2029 paragraph
                # separator character instead of a newline \n character.
                # See: spyder-ide/spyder#2675
                eol_char = get_eol_chars(self.editor.toPlainText())
                seltxt = seltxt.replace(u'\u2029', eol_char)

                cursor.removeSelectedText()
                cursor.insertText(re_pattern.sub(replace_text, seltxt))

            if self.find_next(set_focus=False):
                found_cursor = self.editor.textCursor()
                cursor.setPosition(found_cursor.selectionStart(),
                                   QTextCursor.MoveAnchor)
                cursor.setPosition(found_cursor.selectionEnd(),
                                   QTextCursor.KeepAnchor)


        if cursor is not None:
            cursor.endEditBlock()

        if focus_replace_text:
            self.replace_text.setFocus()
        else:
            self.editor.setFocus()

        if getattr(self.editor, 'document_did_change', False):
            self.editor.document_did_change()

    @Slot()
    def replace_find_all(self):
        """Replace and find all matching occurrences"""
        if self.editor is None:
            return

        replace_text = str(self.replace_text.currentText())
        search_text = str(self.search_text.currentText())
        re_pattern = None
        case = self.case_button.isChecked()
        re_flags = re.MULTILINE if case else re.IGNORECASE | re.MULTILINE
        re_enabled = self.re_button.isChecked()

        # Escape backslashes present in replace_text to avoid an error when
        # using the regexp pattern below to perform the substitution.
        # Fixes spyder-ide/spyder#21007.
        replace_text = replace_text.replace('\\', r'\\')

        # Check regexp before proceeding
        if re_enabled:
            try:
                re_pattern = re.compile(search_text, flags=re_flags)
                # Check if replace_text can be substituted in re_pattern
                # Fixes spyder-ide/spyder#7177.
                re_pattern.sub(replace_text, '')
            except re.error:
                # Do nothing with an invalid regexp
                return
        else:
            re_pattern = re.compile(re.escape(search_text), flags=re_flags)

        cursor = self.editor._select_text("sof", "eof")
        text = self.editor.toPlainText()
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(re_pattern.sub(replace_text, text))
        cursor.endEditBlock()

        self.editor.setFocus()

    @Slot()
    def replace_find_selection(self, focus_replace_text=False):
        """Replace and find in the current selection"""
        if self.editor is not None:
            replace_text = to_text_string(self.replace_text.currentText())
            search_text = to_text_string(self.search_text.currentText())
            case = self.case_button.isChecked()
            word = self.words_button.isChecked()
            re_flags = re.MULTILINE if case else re.IGNORECASE | re.MULTILINE

            re_pattern = None
            if self.re_button.isChecked():
                pattern = search_text
            else:
                pattern = re.escape(search_text)
                replace_text = replace_text.replace('\\', r'\\')
            if word:  # match whole words only
                pattern = r'\b{pattern}\b'.format(pattern=pattern)

            # Check regexp before proceeding
            try:
                re_pattern = re.compile(pattern, flags=re_flags)
                # Check if replace_text can be substituted in re_pattern
                # Fixes spyder-ide/spyder#7177.
                re_pattern.sub(replace_text, '')
            except re.error:
                # Do nothing with an invalid regexp
                return

            selected_text = to_text_string(self.editor.get_selected_text())
            replacement = re_pattern.sub(replace_text, selected_text)
            if replacement != selected_text:
                cursor = self.editor.textCursor()
                start_pos = cursor.selectionStart()
                cursor.beginEditBlock()
                cursor.removeSelectedText()
                cursor.insertText(replacement)
                # Restore selection
                self.editor.set_cursor_position(start_pos)
                for c in range(len(replacement)):
                    self.editor.extend_selection_to_next('character', 'right')
                cursor.endEditBlock()

            if focus_replace_text:
                self.replace_text.setFocus()
            else:
                self.editor.setFocus()

            if getattr(self.editor, 'document_did_change', False):
                self.editor.document_did_change()

    def change_number_matches(self, current_match=0, total_matches=0):
        """Change number of match and total matches."""
        if current_match and total_matches:
            self.matches_string = "{} {} {}".format(current_match, _("of"),
                                                    total_matches)
            self.show_matches()
        elif total_matches:
            self.matches_string = "{} {}".format(total_matches, _("matches"))
            self.show_matches()
        else:
            self.number_matches_text.hide()
            if self.search_text.currentText():
                self.show_no_matches()

    def update_matches(self):
        """Update total number of matches if text has changed in the editor."""
        if self.isVisible():
            number_matches = self.editor.get_number_matches(
                self.search_text.lineEdit().text(),
                case=self.case_button.isChecked(),
                regexp=self.re_button.isChecked(),
                word=self.words_button.isChecked()
            )
            self.change_number_matches(total_matches=number_matches)

    def show_no_matches(self):
        """Show a no matches message with an icon."""
        self._show_icon_message('no_matches')

    def show_matches(self):
        """Show the number of matches found in the document."""
        if not self.matches_string:
            return

        self.number_matches_text.show()
        self.messages_action.setVisible(False)

        if self.hide_number_matches_text:
            self.number_matches_text.setPixmap(self.number_matches_pixmap)
            self.number_matches_text.setToolTip(self.matches_string)
        else:
            self.number_matches_text.setPixmap(QPixmap())
            self.number_matches_text.setText(self.matches_string)

    def show_error(self, error_msg):
        """Show a regexp error message with an icon."""
        self._show_icon_message('error', extra_info=error_msg)

    def _show_icon_message(self, kind, extra_info=None):
        """
        Show a message to users with an icon when no matches can be found or
        there's an error in the passed regexp.

        Parameters
        ----------
        kind: str
            The kind of message. It can be 'no_matches' or 'error'.
        extra_info:
            Extra info to add to the icon's tooltip.
        """
        if kind == 'no_matches':
            tooltip = self.TOOLTIP['no_matches']
            icon = self.no_matches_icon
        else:
            tooltip = self.TOOLTIP['regexp_error']
            icon = self.error_icon

        if extra_info:
            tooltip = tooltip + ': ' + extra_info

        self.messages_action.setIcon(icon)
        self.messages_action.setToolTip(tooltip)
        self.messages_action.setVisible(True)

    def _width_adjustments(self):
        """Several adjustments according to the widget's total width."""
        # The widgets list includes search_text and number_matches_text. That's
        # why we substract a 2 below.
        buttons_width = self.icon_size.width() * (len(self.widgets) - 2)

        total_width = self.size().width()
        matches_width = self.number_matches_text.size().width()
        minimal_width = (
            self.search_text.recommended_width + buttons_width + matches_width
        )

        if total_width < minimal_width:
            self.search_text.setMinimumWidth(30)
            self.hide_number_matches_text = True
        else:
            self.search_text.setMinimumWidth(int(total_width / 2))
            self.hide_number_matches_text = False

        # We don't call show_matches directly here to avoid flickering when the
        # user hits the widget's minimal width, which changes from text to an
        # icon (or vice versa) for number_matches_text.
        self.show_matches_timer.start()

    def _resize_replace_text(self, size, old_size):
        """
        Resize replace_text combobox to match the width of the search one.
        """
        self.replace_text.setMinimumWidth(size.width())
        self.replace_text.setMaximumWidth(size.width())
