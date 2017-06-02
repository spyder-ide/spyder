# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Shortcut management"""

# Standard library imports
from __future__ import print_function
import os
import re
import sys

# Third party imports
from qtpy import PYQT5
from qtpy.compat import from_qvariant, to_qvariant
from qtpy.QtCore import (QAbstractTableModel, QModelIndex, QRegExp,
                         QSortFilterProxyModel, Qt)
from qtpy.QtGui import (QKeySequence, QRegExpValidator)
from qtpy.QtWidgets import (QAbstractItemView, QApplication, QDialog,
                            QDialogButtonBox, QGridLayout, QHBoxLayout, QLabel,
                            QLineEdit, QMessageBox, QPushButton, QSpacerItem,
                            QTableView, QVBoxLayout)

# Local imports
from spyder.config.base import _, debug_print
from spyder.config.gui import (get_shortcut, iter_shortcuts,
                               reset_shortcuts, set_shortcut)
from spyder.plugins.configdialog import GeneralConfigPage
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import get_std_icon
from spyder.utils.stringmatching import get_search_scores, get_search_regex
from spyder.widgets.helperwidgets import HTMLDelegate
from spyder.widgets.helperwidgets import HelperToolButton


MODIFIERS = {Qt.Key_Shift: Qt.SHIFT,
             Qt.Key_Control: Qt.CTRL,
             Qt.Key_Alt: Qt.ALT,
             Qt.Key_Meta: Qt.META}

# Valid shortcut keys
SINGLE_KEYS = ["F{}".format(_i) for _i in range(1, 36)] + ["Delete", "Escape"]
KEYSTRINGS = ["Tab", "Backtab", "Backspace", "Return", "Enter",
              "Pause", "Print", "Clear", "Home", "End", "Left",
              "Up", "Right", "Down", "PageUp", "PageDown"] + \
             ["Space", "Exclam", "QuoteDbl", "NumberSign", "Dollar",
              "Percent", "Ampersand", "Apostrophe", "ParenLeft",
              "ParenRight", "Asterisk", "Plus", "Comma", "Minus",
              "Period", "Slash"] + \
             [str(_i) for _i in range(10)] + \
             ["Colon", "Semicolon", "Less", "Equal", "Greater",
              "Question", "At"] + [chr(_i) for _i in range(65, 91)] + \
             ["BracketLeft", "Backslash", "BracketRight", "Underscore",
              "Control", "Alt", "Shift", "Meta"]
VALID_SINGLE_KEYS = [getattr(Qt, 'Key_{0}'.format(k)) for k in SINGLE_KEYS]
VALID_KEYS = [getattr(Qt, 'Key_{0}'.format(k)) for k in KEYSTRINGS+SINGLE_KEYS]

# Valid finder chars. To be improved
VALID_ACCENT_CHARS = "ÁÉÍOÚáéíúóàèìòùÀÈÌÒÙâêîôûÂÊÎÔÛäëïöüÄËÏÖÜñÑ"
VALID_FINDER_CHARS = "[A-Za-z\s{0}]".format(VALID_ACCENT_CHARS)

BLACKLIST = {
    'Shift+Del': _('Currently used to delete lines on editor')
}

if os.name == 'nt':
    BLACKLIST['Alt+Backspace'] = _('We cannot support this '
                                   'shortcut on Windows')

BLACKLIST['Shift'] = _('Shortcuts that use Shift and another key'
                       ' are unsupported')


class CustomLineEdit(QLineEdit):
    """QLineEdit that filters its key press and release events."""
    def __init__(self, parent):
        super(CustomLineEdit, self).__init__(parent)
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.NoFocus)

    def keyPressEvent(self, e):
        """Qt Override"""
        self.parent().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        """Qt Override"""
        self.parent().keyReleaseEvent(e)


class ShortcutFinder(QLineEdit):
    """Textbox for filtering listed shortcuts in the table."""
    def __init__(self, parent, callback=None):
        super(ShortcutFinder, self).__init__(parent)
        self._parent = parent

        # Widget setup
        regex = QRegExp(VALID_FINDER_CHARS + "{100}")
        self.setValidator(QRegExpValidator(regex))

        # Signals
        if callback:
            self.textChanged.connect(callback)

    def set_text(self, text):
        """Set the filter text."""
        text = text.strip()
        new_text = self.text() + text
        self.setText(new_text)

    def keyPressEvent(self, event):
        """Qt Override."""
        key = event.key()
        if key in [Qt.Key_Up]:
            self._parent.previous_row()
        elif key in [Qt.Key_Down]:
            self._parent.next_row()
        elif key in [Qt.Key_Enter, Qt.Key_Return]:
            self._parent.show_editor()
        else:
            super(ShortcutFinder, self).keyPressEvent(event)


# Error codes for the shortcut editor dialog
(NO_WARNING, SEQUENCE_LENGTH, SEQUENCE_CONFLICT,
 INVALID_KEY, IN_BLACKLIST, SHIFT_BLACKLIST) = [0, 1, 2, 3, 4, 5]


class ShortcutEditor(QDialog):
    """A dialog for entering key sequences."""
    def __init__(self, parent, context, name, sequence, shortcuts):
        super(ShortcutEditor, self).__init__(parent)
        self._parent = parent

        self.context = context
        self.npressed = 0
        self.keys = set()
        self.key_modifiers = set()
        self.key_non_modifiers = list()
        self.key_text = list()
        self.sequence = sequence
        self.new_sequence = None
        self.edit_state = True
        self.shortcuts = shortcuts

        # Widgets
        self.label_info = QLabel()
        self.label_info.setText(_("Press the new shortcut and select 'Ok': \n"
             "(Press 'Tab' once to switch focus between the shortcut entry \n"
             "and the buttons below it)"))
        self.label_current_sequence = QLabel(_("Current shortcut:"))
        self.text_current_sequence = QLabel(sequence)
        self.label_new_sequence = QLabel(_("New shortcut:"))
        self.text_new_sequence = CustomLineEdit(self)
        self.text_new_sequence.setPlaceholderText(sequence)
        self.helper_button = HelperToolButton()
        self.helper_button.hide()
        self.label_warning = QLabel()
        self.label_warning.hide()

        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_ok = bbox.button(QDialogButtonBox.Ok)
        self.button_cancel = bbox.button(QDialogButtonBox.Cancel)

        # Setup widgets
        self.setWindowTitle(_('Shortcut: {0}').format(name))
        self.button_ok.setFocusPolicy(Qt.NoFocus)
        self.button_ok.setEnabled(False)
        self.button_cancel.setFocusPolicy(Qt.NoFocus)
        self.helper_button.setToolTip('')
        self.helper_button.setFocusPolicy(Qt.NoFocus)
        style = """
            QToolButton {
              margin:1px;
              border: 0px solid grey;
              padding:0px;
              border-radius: 0px;
            }"""
        self.helper_button.setStyleSheet(style)
        self.text_new_sequence.setFocusPolicy(Qt.NoFocus)
        self.label_warning.setFocusPolicy(Qt.NoFocus)

        # Layout
        spacing = 5
        layout_sequence = QGridLayout()
        layout_sequence.addWidget(self.label_info, 0, 0, 1, 3)
        layout_sequence.addItem(QSpacerItem(spacing, spacing), 1, 0, 1, 2)
        layout_sequence.addWidget(self.label_current_sequence, 2, 0)
        layout_sequence.addWidget(self.text_current_sequence, 2, 2)
        layout_sequence.addWidget(self.label_new_sequence, 3, 0)
        layout_sequence.addWidget(self.helper_button, 3, 1)
        layout_sequence.addWidget(self.text_new_sequence, 3, 2)
        layout_sequence.addWidget(self.label_warning, 4, 2, 1, 2)

        layout = QVBoxLayout()
        layout.addLayout(layout_sequence)
        layout.addSpacing(spacing)
        layout.addWidget(bbox)
        self.setLayout(layout)

        # Signals
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)

    def keyPressEvent(self, e):
        """Qt override."""
        key = e.key()
        # Check if valid keys
        if key not in VALID_KEYS:
            self.invalid_key_flag = True
            return

        self.npressed += 1
        self.key_non_modifiers.append(key)
        self.key_modifiers.add(key)
        self.key_text.append(e.text())
        self.invalid_key_flag = False

        debug_print('key {0}, npressed: {1}'.format(key, self.npressed))

        if key == Qt.Key_unknown:
            return

        # The user clicked just and only the special keys
        # Ctrl, Shift, Alt, Meta.
        if (key == Qt.Key_Control or
                key == Qt.Key_Shift or
                key == Qt.Key_Alt or
                key == Qt.Key_Meta):
            return

        modifiers = e.modifiers()
        if modifiers & Qt.ShiftModifier:
            key += Qt.SHIFT
        if modifiers & Qt.ControlModifier:
            key += Qt.CTRL
            if sys.platform == 'darwin':
                self.npressed -= 1
            debug_print('decrementing')
        if modifiers & Qt.AltModifier:
            key += Qt.ALT
        if modifiers & Qt.MetaModifier:
            key += Qt.META

        self.keys.add(key)

    def toggle_state(self):
        """Switch between shortcut entry and Accept/Cancel shortcut mode."""
        self.edit_state = not self.edit_state

        if not self.edit_state:
            self.text_new_sequence.setEnabled(False)
            if self.button_ok.isEnabled():
                self.button_ok.setFocus()
            else:
                self.button_cancel.setFocus()
        else:
            self.text_new_sequence.setEnabled(True)
            self.text_new_sequence.setFocus()

    def nonedit_keyrelease(self, e):
        """Key release event for non-edit state."""
        key = e.key()
        if key in [Qt.Key_Escape]:
            self.close()
            return

        if key in [Qt.Key_Left, Qt.Key_Right, Qt.Key_Up,
                   Qt.Key_Down]:
            if self.button_ok.hasFocus():
                self.button_cancel.setFocus()
            else:
                self.button_ok.setFocus()

    def keyReleaseEvent(self, e):
        """Qt override."""
        self.npressed -= 1
        if self.npressed <= 0:
            key = e.key()

            if len(self.keys) == 1 and key == Qt.Key_Tab:
                self.toggle_state()
                return

            if len(self.keys) == 1 and key == Qt.Key_Escape:
                self.set_sequence('')
                self.label_warning.setText(_("Please introduce a different "
                                             "shortcut"))

            if len(self.keys) == 1 and key in [Qt.Key_Return, Qt.Key_Enter]:
                self.toggle_state()
                return

            if not self.edit_state:
                self.nonedit_keyrelease(e)
            else:
                debug_print('keys: {}'.format(self.keys))
                if self.keys and key != Qt.Key_Escape:
                    self.validate_sequence()
                self.keys = set()
                self.key_modifiers = set()
                self.key_non_modifiers = list()
                self.key_text = list()
                self.npressed = 0

    def check_conflicts(self):
        """Check shortcuts for conflicts."""
        conflicts = []
        for index, shortcut in enumerate(self.shortcuts):
            sequence = str(shortcut.key)
            if sequence == self.new_sequence and \
                (shortcut.context == self.context or shortcut.context == '_' or
                 self.context == '_'):
                conflicts.append(shortcut)
        return conflicts

    def update_warning(self, warning_type=NO_WARNING, conflicts=[]):
        """Update warning label to reflect conflict status of new shortcut"""
        if warning_type == NO_WARNING:
            warn = False
            tip = 'This shortcut is correct!'
        elif warning_type == SEQUENCE_CONFLICT:
            template = '<i>{0}<b>{1}</b></i>'
            tip_title = _('The new shorcut conflicts with:') + '<br>'
            tip_body = ''
            for s in conflicts:
                tip_body += ' - {0}: {1}<br>'.format(s.context, s.name)
            tip_body = tip_body[:-4]  # Removing last <br>
            tip = template.format(tip_title, tip_body)
            warn = True
        elif warning_type == IN_BLACKLIST:
            template = '<i>{0}<b>{1}</b></i>'
            tip_title = _('Forbidden key sequence!') + '<br>'
            tip_body = ''
            use = BLACKLIST[self.new_sequence]
            if use is not None:
                tip_body = use
            tip = template.format(tip_title, tip_body)
            warn = True
        elif warning_type == SHIFT_BLACKLIST:
            template = '<i>{0}<b>{1}</b></i>'
            tip_title = _('Forbidden key sequence!') + '<br>'
            tip_body = ''
            use = BLACKLIST['Shift']
            if use is not None:
                tip_body = use
            tip = template.format(tip_title, tip_body)
            warn = True
        elif warning_type == SEQUENCE_LENGTH:
            # Sequences with 5 keysequences (i.e. Ctrl+1, Ctrl+2, Ctrl+3,
            # Ctrl+4, Ctrl+5) are invalid
            template = '<i>{0}</i>'
            tip = _('A compound sequence can have {break} a maximum of '
                    '4 subsequences.{break}').format(**{'break': '<br>'})
            warn = True
        elif warning_type == INVALID_KEY:
            template = '<i>{0}</i>'
            tip = _('Invalid key entered') + '<br>'
            warn = True

        self.helper_button.show()
        if warn:
            self.label_warning.show()
            self.helper_button.setIcon(get_std_icon('MessageBoxWarning'))
            self.button_ok.setEnabled(False)
        else:
            self.helper_button.setIcon(get_std_icon('DialogApplyButton'))

        self.label_warning.setText(tip)

    def set_sequence(self, sequence):
        """Set the new shortcut and update buttons."""
        if not sequence or self.sequence == sequence:
            self.button_ok.setEnabled(False)
            different_sequence = False
        else:
            self.button_ok.setEnabled(True)
            different_sequence = True

        if sys.platform == 'darwin':
            if 'Meta+Ctrl' in sequence:
                shown_sequence = sequence.replace('Meta+Ctrl', 'Ctrl+Cmd')
            elif 'Ctrl+Meta' in sequence:
                shown_sequence = sequence.replace('Ctrl+Meta', 'Cmd+Ctrl')
            elif 'Ctrl' in sequence:
                shown_sequence = sequence.replace('Ctrl', 'Cmd')
            elif 'Meta' in sequence:
                shown_sequence = sequence.replace('Meta', 'Ctrl')
            else:
                shown_sequence = sequence
        else:
            shown_sequence = sequence
        self.text_new_sequence.setText(shown_sequence)
        self.new_sequence = sequence

        conflicts = self.check_conflicts()
        blacklist = self.new_sequence in BLACKLIST
        individual_keys = self.new_sequence.split('+')
        if conflicts and different_sequence:
            warning_type = SEQUENCE_CONFLICT
        elif blacklist:
            warning_type = IN_BLACKLIST
        elif len(individual_keys) == 2 and individual_keys[0] == 'Shift':
            warning_type = SHIFT_BLACKLIST
        else:
            warning_type = NO_WARNING

        self.update_warning(warning_type=warning_type, conflicts=conflicts)

    def validate_sequence(self):
        """Provide additional checks for accepting or rejecting shortcuts."""
        if self.invalid_key_flag:
            self.update_warning(warning_type=INVALID_KEY)
            return

        for mod in MODIFIERS:
            non_mod = set(self.key_non_modifiers)
            non_mod.discard(mod)
            if mod in self.key_non_modifiers:
                self.key_non_modifiers.remove(mod)

        self.key_modifiers = self.key_modifiers - non_mod

        while u'' in self.key_text:
            self.key_text.remove(u'')

        self.key_text = [k.upper() for k in self.key_text]

        # Fix Backtab, Tab issue
        if os.name == 'nt':
            if Qt.Key_Backtab in self.key_non_modifiers:
                idx = self.key_non_modifiers.index(Qt.Key_Backtab)
                self.key_non_modifiers[idx] = Qt.Key_Tab

        if len(self.key_modifiers) == 0:
            # Filter single key allowed
            if self.key_non_modifiers[0] not in VALID_SINGLE_KEYS:
                return
            # Filter
            elif len(self.key_non_modifiers) > 1:
                return

        # QKeySequence accepts a maximum of 4 different sequences
        if len(self.keys) > 4:
            # Update warning
            self.update_warning(warning_type=SEQUENCE_LENGTH)
            return

        keys = []
        for i in range(len(self.keys)):
            key_seq = 0
            for m in self.key_modifiers:
                key_seq += MODIFIERS[m]
            key_seq += self.key_non_modifiers[i]
            keys.append(key_seq)

        sequence = QKeySequence(*keys)

        self.set_sequence(sequence.toString())


class Shortcut(object):
    """Shortcut convenience class for holding shortcut context, name,
    original ordering index, key sequence for the shortcut and localized text.
    """
    def __init__(self, context, name, key=None):
        self.index = 0  # Sorted index. Populated when loading shortcuts
        self.context = context
        self.name = name
        self.key = key

    def __str__(self):
        return "{0}/{1}: {2}".format(self.context, self.name, self.key)

    def load(self):
        self.key = get_shortcut(self.context, self.name)

    def save(self):
        set_shortcut(self.context, self.name, self.key)


CONTEXT, NAME, SEQUENCE, SEARCH_SCORE = [0, 1, 2, 3]


class ShortcutsModel(QAbstractTableModel):
    def __init__(self, parent):
        QAbstractTableModel.__init__(self)
        self._parent = parent

        self.shortcuts = []
        self.scores = []
        self.rich_text = []
        self.normal_text = []
        self.letters = ''
        self.label = QLabel()
        self.widths = []

        # Needed to compensate for the HTMLDelegate color selection unawarness
        palette = parent.palette()
        self.text_color = palette.text().color().name()
        self.text_color_highlight = palette.highlightedText().color().name()

    def current_index(self):
        """Get the currently selected index in the parent table view."""
        i = self._parent.proxy_model.mapToSource(self._parent.currentIndex())
        return i

    def sortByName(self):
        """Qt Override."""
        self.shortcuts = sorted(self.shortcuts,
                                key=lambda x: x.context+'/'+x.name)
        self.reset()

    def flags(self, index):
        """Qt Override."""
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(QAbstractTableModel.flags(self, index))

    def data(self, index, role=Qt.DisplayRole):
        """Qt Override."""
        row = index.row()
        if not index.isValid() or not (0 <= row < len(self.shortcuts)):
            return to_qvariant()

        shortcut = self.shortcuts[row]
        key = shortcut.key
        column = index.column()

        if role == Qt.DisplayRole:
            if column == CONTEXT:
                return to_qvariant(shortcut.context)
            elif column == NAME:
                color = self.text_color
                if self._parent == QApplication.focusWidget():
                    if self.current_index().row() == row:
                        color = self.text_color_highlight
                    else:
                        color = self.text_color
                text = self.rich_text[row]
                text = '<p style="color:{0}">{1}</p>'.format(color, text)
                return to_qvariant(text)
            elif column == SEQUENCE:
                text = QKeySequence(key).toString(QKeySequence.NativeText)
                return to_qvariant(text)
            elif column == SEARCH_SCORE:
                # Treating search scores as a table column simplifies the
                # sorting once a score for a specific string in the finder
                # has been defined. This column however should always remain
                # hidden.
                return to_qvariant(self.scores[row])
        elif role == Qt.TextAlignmentRole:
            return to_qvariant(int(Qt.AlignHCenter | Qt.AlignVCenter))
        return to_qvariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Qt Override."""
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return to_qvariant(int(Qt.AlignHCenter | Qt.AlignVCenter))
            return to_qvariant(int(Qt.AlignRight | Qt.AlignVCenter))
        if role != Qt.DisplayRole:
            return to_qvariant()
        if orientation == Qt.Horizontal:
            if section == CONTEXT:
                return to_qvariant(_("Context"))
            elif section == NAME:
                return to_qvariant(_("Name"))
            elif section == SEQUENCE:
                return to_qvariant(_("Shortcut"))
            elif section == SEARCH_SCORE:
                return to_qvariant(_("Score"))
        return to_qvariant()

    def rowCount(self, index=QModelIndex()):
        """Qt Override."""
        return len(self.shortcuts)

    def columnCount(self, index=QModelIndex()):
        """Qt Override."""
        return 4

    def setData(self, index, value, role=Qt.EditRole):
        """Qt Override."""
        if index.isValid() and 0 <= index.row() < len(self.shortcuts):
            shortcut = self.shortcuts[index.row()]
            column = index.column()
            text = from_qvariant(value, str)
            if column == SEQUENCE:
                shortcut.key = text
            self.dataChanged.emit(index, index)
            return True
        return False

    def update_search_letters(self, text):
        """Update search letters with text input in search box."""
        self.letters = text
        names = [shortcut.name for shortcut in self.shortcuts]
        results = get_search_scores(text, names, template='<b>{0}</b>')
        self.normal_text, self.rich_text, self.scores = zip(*results)
        self.reset()

    def update_active_row(self):
        """Update active row to update color in selected text."""
        self.data(self.current_index())

    def row(self, row_num):
        """Get row based on model index. Needed for the custom proxy model."""
        return self.shortcuts[row_num]

    def reset(self):
        """"Reset model to take into account new search letters."""
        self.beginResetModel()
        self.endResetModel()


class CustomSortFilterProxy(QSortFilterProxyModel):
    """Custom column filter based on regex."""
    def __init__(self, parent=None):
        super(CustomSortFilterProxy, self).__init__(parent)
        self._parent = parent
        self.pattern = re.compile(u'')

    def set_filter(self, text):
        """Set regular expression for filter."""
        self.pattern = get_search_regex(text)
        if self.pattern:
            self._parent.setSortingEnabled(False)
        else:
            self._parent.setSortingEnabled(True)
        self.invalidateFilter()

    def filterAcceptsRow(self, row_num, parent):
        """Qt override.

        Reimplemented from base class to allow the use of custom filtering.
        """
        model = self.sourceModel()
        name = model.row(row_num).name
        r = re.search(self.pattern, name)

        if r is None:
            return False
        else:
            return True


class ShortcutsTable(QTableView):
    def __init__(self, parent=None):
        QTableView.__init__(self, parent)
        self._parent = parent
        self.finder = None

        self.source_model = ShortcutsModel(self)
        self.proxy_model = CustomSortFilterProxy(self)
        self.last_regex = ''

        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setDynamicSortFilter(True)
        self.proxy_model.setFilterKeyColumn(NAME)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setModel(self.proxy_model)

        self.hideColumn(SEARCH_SCORE)
        self.setItemDelegateForColumn(NAME, HTMLDelegate(self, margin=9))
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.selectionModel().selectionChanged.connect(self.selection)

        self.verticalHeader().hide()
        self.load_shortcuts()

    def focusOutEvent(self, e):
        """Qt Override."""
        self.source_model.update_active_row()
        super(ShortcutsTable, self).focusOutEvent(e)

    def focusInEvent(self, e):
        """Qt Override."""
        super(ShortcutsTable, self).focusInEvent(e)
        self.selectRow(self.currentIndex().row())

    def selection(self, index):
        """Update selected row."""
        self.update()
        self.isActiveWindow()

    def adjust_cells(self):
        """Adjust column size based on contents."""
        self.resizeColumnsToContents()
        fm = self.horizontalHeader().fontMetrics()
        names = [fm.width(s.name + ' '*9) for s in self.source_model.shortcuts]
        self.setColumnWidth(NAME, max(names))
        self.horizontalHeader().setStretchLastSection(True)

    def load_shortcuts(self):
        """Load shortcuts and assign to table model."""
        shortcuts = []
        for context, name, keystr in iter_shortcuts():
            shortcut = Shortcut(context, name, keystr)
            shortcuts.append(shortcut)
        shortcuts = sorted(shortcuts, key=lambda x: x.context+x.name)
        # Store the original order of shortcuts
        for i, shortcut in enumerate(shortcuts):
            shortcut.index = i
        self.source_model.shortcuts = shortcuts
        self.source_model.scores = [0]*len(shortcuts)
        self.source_model.rich_text = [s.name for s in shortcuts]
        self.source_model.reset()
        self.adjust_cells()
        self.sortByColumn(CONTEXT, Qt.AscendingOrder)

    def check_shortcuts(self):
        """Check shortcuts for conflicts."""
        conflicts = []
        for index, sh1 in enumerate(self.source_model.shortcuts):
            if index == len(self.source_model.shortcuts)-1:
                break
            for sh2 in self.source_model.shortcuts[index+1:]:
                if sh2 is sh1:
                    continue
                if str(sh2.key) == str(sh1.key) \
                   and (sh1.context == sh2.context or sh1.context == '_' or
                        sh2.context == '_'):
                    conflicts.append((sh1, sh2))
        if conflicts:
            self.parent().show_this_page.emit()
            cstr = "\n".join(['%s <---> %s' % (sh1, sh2)
                              for sh1, sh2 in conflicts])
            QMessageBox.warning(self, _("Conflicts"),
                                _("The following conflicts have been "
                                  "detected:")+"\n"+cstr, QMessageBox.Ok)

    def save_shortcuts(self):
        """Save shortcuts from table model."""
        self.check_shortcuts()
        for shortcut in self.source_model.shortcuts:
            shortcut.save()

    def show_editor(self):
        """Create, setup and display the shortcut editor dialog."""
        index = self.proxy_model.mapToSource(self.currentIndex())
        row, column = index.row(), index.column()
        shortcuts = self.source_model.shortcuts
        context = shortcuts[row].context
        name = shortcuts[row].name

        sequence_index = self.source_model.index(row, SEQUENCE)
        sequence = sequence_index.data()

        dialog = ShortcutEditor(self, context, name, sequence, shortcuts)

        if dialog.exec_():
            new_sequence = dialog.new_sequence
            self.source_model.setData(sequence_index, new_sequence)

    def set_regex(self, regex=None, reset=False):
        """Update the regex text for the shortcut finder."""
        if reset:
            text = ''
        else:
            text = self.finder.text().replace(' ', '').lower()

        self.proxy_model.set_filter(text)
        self.source_model.update_search_letters(text)
        self.sortByColumn(SEARCH_SCORE, Qt.AscendingOrder)

        if self.last_regex != regex:
            self.selectRow(0)
        self.last_regex = regex

    def next_row(self):
        """Move to next row from currently selected row."""
        row = self.currentIndex().row()
        rows = self.proxy_model.rowCount()
        if row + 1 == rows:
            row = -1
        self.selectRow(row + 1)

    def previous_row(self):
        """Move to previous row from currently selected row."""
        row = self.currentIndex().row()
        rows = self.proxy_model.rowCount()
        if row == 0:
            row = rows
        self.selectRow(row - 1)

    def keyPressEvent(self, event):
        """Qt Override."""
        key = event.key()
        if key in [Qt.Key_Enter, Qt.Key_Return]:
            self.show_editor()
        elif key in [Qt.Key_Tab]:
            self.finder.setFocus()
        elif key in [Qt.Key_Backtab]:
            self.parent().reset_btn.setFocus()
        elif key in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right]:
            super(ShortcutsTable, self).keyPressEvent(event)
        elif key not in [Qt.Key_Escape, Qt.Key_Space]:
            text = event.text()
            if text:
                if re.search(VALID_FINDER_CHARS, text) is not None:
                    self.finder.setFocus()
                    self.finder.set_text(text)
        elif key in [Qt.Key_Escape]:
            self.finder.keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Qt Override."""
        self.show_editor()


class ShortcutsConfigPage(GeneralConfigPage):
    CONF_SECTION = "shortcuts"

    NAME = _("Keyboard shortcuts")
    ICON = ima.icon('keyboard')

    def setup_page(self):
        # Widgets
        self.table = ShortcutsTable(self)
        self.finder = ShortcutFinder(self.table, self.table.set_regex)
        self.table.finder = self.finder
        self.label_finder = QLabel(_('Search: '))
        self.reset_btn = QPushButton(_("Reset to default values"))

        # Layout
        hlayout = QHBoxLayout()
        vlayout = QVBoxLayout()
        hlayout.addWidget(self.label_finder)
        hlayout.addWidget(self.finder)
        vlayout.addWidget(self.table)
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.reset_btn)
        self.setLayout(vlayout)

        self.setTabOrder(self.table, self.finder)
        self.setTabOrder(self.finder, self.reset_btn)

        # Signals and slots
        if PYQT5:
            # Qt5 'dataChanged' has 3 parameters
            self.table.proxy_model.dataChanged.connect(
                lambda i1, i2, roles, opt='': self.has_been_modified(opt))
        else:
            self.table.proxy_model.dataChanged.connect(
                lambda i1, i2, opt='': self.has_been_modified(opt))
        self.reset_btn.clicked.connect(self.reset_to_default)

    def check_settings(self):
        self.table.check_shortcuts()

    def reset_to_default(self):
        reset_shortcuts()
        self.main.apply_shortcuts()
        self.table.load_shortcuts()
        self.load_from_conf()
        self.set_modified(False)

    def apply_settings(self, options):
        self.table.save_shortcuts()
        self.main.apply_shortcuts()


def test():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    table = ShortcutsTable()
    table.show()
    app.exec_()
    print([str(s) for s in table.source_model.shortcuts])  # spyder: test-skip
    table.check_shortcuts()

if __name__ == '__main__':
    test()
