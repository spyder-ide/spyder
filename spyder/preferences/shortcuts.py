# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Shortcut management"""

# Standard library imports
from __future__ import print_function
import re

# Third party imports
from qtpy import PYQT5
from qtpy.compat import from_qvariant, to_qvariant
from qtpy.QtCore import (QAbstractTableModel, QModelIndex, QRegExp,
                         QSortFilterProxyModel, Qt, Slot, QEvent)
from qtpy.QtGui import (QKeySequence, QRegExpValidator, QIcon)
from qtpy.QtWidgets import (QAbstractItemView, QApplication, QDialog,
                            QGridLayout, QHBoxLayout, QLabel,
                            QLineEdit, QMessageBox, QPushButton, QSpacerItem,
                            QTableView, QVBoxLayout, QKeySequenceEdit)

# Local imports
from spyder.config.base import _
from spyder.config.main import CONF
from spyder.config.gui import (get_shortcut, iter_shortcuts,
                               reset_shortcuts, set_shortcut)
from spyder.preferences.configdialog import GeneralConfigPage
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import get_std_icon, create_toolbutton
from spyder.utils.stringmatching import get_search_scores, get_search_regex
from spyder.widgets.helperwidgets import HTMLDelegate
from spyder.widgets.helperwidgets import HelperToolButton


# Valid shortcut keys
SINGLE_KEYS = ["F{}".format(_i) for _i in range(1, 36)] + ["Del", "Esc"]
EDITOR_SINGLE_KEYS = SINGLE_KEYS + ["Home", "End", "Ins", "Enter",
                                    "Return", "Backspace", "Tab",
                                    "PageUp", "PageDown", "Clear",  "Pause",
                                    "Left", "Up", "Right", "Down"]

# Valid finder chars. To be improved
VALID_ACCENT_CHARS = "ÁÉÍOÚáéíúóàèìòùÀÈÌÒÙâêîôûÂÊÎÔÛäëïöüÄËÏÖÜñÑ"
VALID_FINDER_CHARS = r"[A-Za-z\s{0}]".format(VALID_ACCENT_CHARS)


# Key sequences blacklist for the shortcut editor dialog
BLACKLIST = {}

# Error codes for the shortcut editor dialog
NO_WARNING = 0
SEQUENCE_EMPTY = 1
SEQUENCE_CONFLICT = 2
INVALID_KEY = 3
IN_BLACKLIST = 4


class ShortcutTranslator(QKeySequenceEdit):
    """
    A QKeySequenceEdit that is not meant to be shown and is used only
    to convert QKeyEvent into QKeySequence. To our knowledge, this is
    the only way to do this within the Qt framework, because the code that does
    this in Qt is protected. Porting the code to Python would be nearly
    impossible because it relies on low level and OS-dependent Qt libraries
    that are not public for the most part.
    """

    def __init__(self):
        super(ShortcutTranslator, self).__init__()
        self.hide()

    def keyevent_to_keyseq(self, event):
        """Return a QKeySequence representation of the provided QKeyEvent."""
        self.keyPressEvent(event)
        event.accept()
        return self.keySequence()

    def keyReleaseEvent(self, event):
        """Qt Override"""
        return False

    def timerEvent(self, event):
        """Qt Override"""
        return False

    def event(self, event):
        """Qt Override"""
        return False


class ShortcutLineEdit(QLineEdit):
    """QLineEdit that filters its key press and release events."""

    def __init__(self, parent):
        super(ShortcutLineEdit, self).__init__(parent)
        self.setReadOnly(True)

        tw = self.fontMetrics().width(
            "Ctrl+Shift+Alt+Backspace, Ctrl+Shift+Alt+Backspace")
        fw = self.style().pixelMetric(self.style().PM_DefaultFrameWidth)
        self.setMinimumWidth(tw + (2 * fw) + 4)
        # We need to add 4 to take into account the horizontalMargin of the
        # line edit, whose value is hardcoded in qt.

    def keyPressEvent(self, e):
        """Qt Override"""
        self.parent().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        """Qt Override"""
        self.parent().keyReleaseEvent(e)

    def setText(self, sequence):
        """Qt method extension."""
        self.setToolTip(sequence)
        super(ShortcutLineEdit, self).setText(sequence)


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


class ShortcutEditor(QDialog):
    """A dialog for entering key sequences."""

    def __init__(self, parent, context, name, sequence, shortcuts):
        super(ShortcutEditor, self).__init__(parent)
        self._parent = parent

        self.context = context
        self.name = name
        self.shortcuts = shortcuts
        self.current_sequence = sequence
        self._qsequences = list()

        self.setup()
        self.update_warning()

    @property
    def new_sequence(self):
        """Return a string representation of the new key sequence."""
        return ', '.join(self._qsequences)

    @property
    def new_qsequence(self):
        """Return the QKeySequence object of the new key sequence."""
        return QKeySequence(self.new_sequence)

    def setup(self):
        """Setup the ShortcutEditor with the provided arguments."""
        # Widgets
        icon_info = HelperToolButton()
        icon_info.setIcon(get_std_icon('MessageBoxInformation'))
        layout_icon_info = QVBoxLayout()
        layout_icon_info.setContentsMargins(0, 0, 0, 0)
        layout_icon_info.setSpacing(0)
        layout_icon_info.addWidget(icon_info)
        layout_icon_info.addStretch(100)

        self.label_info = QLabel()
        self.label_info.setText(
            _("Press the new shortcut and select 'Ok' to confirm, "
              "click 'Cancel' to revert to the previous state, "
              "or use 'Clear' to unbind the command from a shortcut."))
        self.label_info.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.label_info.setWordWrap(True)
        layout_info = QHBoxLayout()
        layout_info.setContentsMargins(0, 0, 0, 0)
        layout_info.addLayout(layout_icon_info)
        layout_info.addWidget(self.label_info)
        layout_info.setStretch(1, 100)

        self.label_current_sequence = QLabel(_("Current shortcut:"))
        self.text_current_sequence = QLabel(self.current_sequence)

        self.label_new_sequence = QLabel(_("New shortcut:"))
        self.text_new_sequence = ShortcutLineEdit(self)
        self.text_new_sequence.setPlaceholderText(_("Press shortcut."))

        self.helper_button = HelperToolButton()
        self.helper_button.setIcon(QIcon())
        self.label_warning = QLabel()
        self.label_warning.setWordWrap(True)
        self.label_warning.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.button_default = QPushButton(_('Default'))
        self.button_ok = QPushButton(_('Ok'))
        self.button_ok.setEnabled(False)
        self.button_clear = QPushButton(_('Clear'))
        self.button_cancel = QPushButton(_('Cancel'))
        button_box = QHBoxLayout()
        button_box.addWidget(self.button_default)
        button_box.addStretch(100)
        button_box.addWidget(self.button_ok)
        button_box.addWidget(self.button_clear)
        button_box.addWidget(self.button_cancel)

        # New Sequence button box
        self.btn_clear_sequence = create_toolbutton(
            self, icon=ima.icon('editclear'),
            tip=_("Clear all entered key sequences"),
            triggered=self.clear_new_sequence)
        self.button_back_sequence = create_toolbutton(
            self, icon=ima.icon('ArrowBack'),
            tip=_("Remove last key sequence entered"),
            triggered=self.back_new_sequence)

        newseq_btnbar = QHBoxLayout()
        newseq_btnbar.setSpacing(0)
        newseq_btnbar.setContentsMargins(0, 0, 0, 0)
        newseq_btnbar.addWidget(self.button_back_sequence)
        newseq_btnbar.addWidget(self.btn_clear_sequence)

        # Setup widgets
        self.setWindowTitle(_('Shortcut: {0}').format(self.name))
        self.helper_button.setToolTip('')
        style = """
            QToolButton {
              margin:1px;
              border: 0px solid grey;
              padding:0px;
              border-radius: 0px;
            }"""
        self.helper_button.setStyleSheet(style)
        icon_info.setToolTip('')
        icon_info.setStyleSheet(style)

        # Layout
        layout_sequence = QGridLayout()
        layout_sequence.setContentsMargins(0, 0, 0, 0)
        layout_sequence.addLayout(layout_info, 0, 0, 1, 4)
        layout_sequence.addItem(QSpacerItem(15, 15), 1, 0, 1, 4)
        layout_sequence.addWidget(self.label_current_sequence, 2, 0)
        layout_sequence.addWidget(self.text_current_sequence, 2, 2)
        layout_sequence.addWidget(self.label_new_sequence, 3, 0)
        layout_sequence.addWidget(self.helper_button, 3, 1)
        layout_sequence.addWidget(self.text_new_sequence, 3, 2)
        layout_sequence.addLayout(newseq_btnbar, 3, 3)
        layout_sequence.addWidget(self.label_warning, 4, 2, 1, 2)
        layout_sequence.setColumnStretch(2, 100)
        layout_sequence.setRowStretch(4, 100)

        layout = QVBoxLayout()
        layout.addLayout(layout_sequence)
        layout.addSpacing(5)
        layout.addLayout(button_box)
        self.setLayout(layout)

        # Signals
        self.button_ok.clicked.connect(self.accept_override)
        self.button_clear.clicked.connect(self.unbind_shortcut)
        self.button_cancel.clicked.connect(self.reject)
        self.button_default.clicked.connect(self.set_sequence_to_default)

        # Set all widget to no focus so that we can register <Tab> key
        # press event.
        widgets = (
            self.label_warning, self.helper_button, self.text_new_sequence,
            self.button_clear, self.button_default, self.button_cancel,
            self.button_ok, self.btn_clear_sequence, self.button_back_sequence)
        for w in widgets:
            w.setFocusPolicy(Qt.NoFocus)
            w.clearFocus()

    @Slot()
    def reject(self):
        """Slot for rejected signal."""
        # Added for issue #5426.  Due to the focusPolicy of Qt.NoFocus for the
        # buttons, if the cancel button was clicked without first setting focus
        # to the button, it would cause a seg fault crash.
        self.button_cancel.setFocus()
        super(ShortcutEditor, self).reject()

    @Slot()
    def accept(self):
        """Slot for accepted signal."""
        # Added for issue #5426.  Due to the focusPolicy of Qt.NoFocus for the
        # buttons, if the ok button was clicked without first setting focus to
        # the button, it would cause a seg fault crash.
        self.button_ok.setFocus()
        super(ShortcutEditor, self).accept()

    def event(self, event):
        """Qt method override."""
        if event.type() in (QEvent.Shortcut, QEvent.ShortcutOverride):
            return True
        else:
            return super(ShortcutEditor, self).event(event)

    def keyPressEvent(self, event):
        """Qt method override."""
        event_key = event.key()
        if not event_key or event_key == Qt.Key_unknown:
            return
        if len(self._qsequences) == 4:
            # QKeySequence accepts a maximum of 4 different sequences.
            return
        if event_key in [Qt.Key_Control, Qt.Key_Shift,
                         Qt.Key_Alt, Qt.Key_Meta]:
            # The event corresponds to just and only a special key.
            return

        translator = ShortcutTranslator()
        event_keyseq = translator.keyevent_to_keyseq(event)
        event_keystr = event_keyseq.toString(QKeySequence.PortableText)
        self._qsequences.append(event_keystr)
        self.update_warning()

    def check_conflicts(self):
        """Check shortcuts for conflicts."""
        conflicts = []
        if len(self._qsequences) == 0:
            return conflicts

        new_qsequence = self.new_qsequence
        for shortcut in self.shortcuts:
            shortcut_qsequence = QKeySequence.fromString(str(shortcut.key))
            if shortcut_qsequence.isEmpty():
                continue
            if (shortcut.context, shortcut.name) == (self.context, self.name):
                continue
            if shortcut.context in [self.context, '_'] or self.context == '_':
                if (shortcut_qsequence.matches(new_qsequence) or
                        new_qsequence.matches(shortcut_qsequence)):
                    conflicts.append(shortcut)
        return conflicts

    def check_ascii(self):
        """
        Check that all characters in the new sequence are ascii or else the
        shortcut will not work.
        """
        try:
            self.new_sequence.encode('ascii')
        except UnicodeEncodeError:
            return False
        else:
            return True

    def check_singlekey(self):
        """Check if the first sub-sequence of the new key sequence is valid."""
        if len(self._qsequences) == 0:
            return True
        else:
            keystr = self._qsequences[0]
            valid_single_keys = (EDITOR_SINGLE_KEYS if
                                 self.context == 'editor' else SINGLE_KEYS)
            if any((m in keystr for m in ('Ctrl', 'Alt', 'Shift', 'Meta'))):
                return True
            else:
                # This means that the the first subsequence is composed of
                # a single key with no modifier.
                valid_single_keys = (EDITOR_SINGLE_KEYS if
                                     self.context == 'editor' else SINGLE_KEYS)
                if any((k == keystr for k in valid_single_keys)):
                    return True
                else:
                    return False

    def update_warning(self):
        """Update the warning label, buttons state and sequence text."""
        new_qsequence = self.new_qsequence
        new_sequence = self.new_sequence
        self.text_new_sequence.setText(
            new_qsequence.toString(QKeySequence.NativeText))

        conflicts = self.check_conflicts()
        if len(self._qsequences) == 0:
            warning = SEQUENCE_EMPTY
            tip = ''
            icon = QIcon()
        elif conflicts:
            warning = SEQUENCE_CONFLICT
            template = '<i>{0}<b>{1}</b>{2}</i>'
            tip_title = _('The new shortcut conflicts with:') + '<br>'
            tip_body = ''
            for s in conflicts:
                tip_body += ' - {0}: {1}<br>'.format(s.context, s.name)
            tip_body = tip_body[:-4]  # Removing last <br>
            tip_override = '<br>Press <b>OK</b> to unbind '
            tip_override += 'it' if len(conflicts) == 1 else 'them'
            tip_override += ' and assign it to <b>{}</b>'.format(self.name)
            tip = template.format(tip_title, tip_body, tip_override)
            icon = get_std_icon('MessageBoxWarning')
        elif new_sequence in BLACKLIST:
            warning = IN_BLACKLIST
            template = '<i>{0}<b>{1}</b></i>'
            tip_title = _('Forbidden key sequence!') + '<br>'
            tip_body = ''
            use = BLACKLIST[new_sequence]
            if use is not None:
                tip_body = use
            tip = template.format(tip_title, tip_body)
            icon = get_std_icon('MessageBoxWarning')
        elif self.check_singlekey() is False or self.check_ascii() is False:
            warning = INVALID_KEY
            template = '<i>{0}</i>'
            tip = _('Invalid key sequence entered') + '<br>'
            icon = get_std_icon('MessageBoxWarning')
        else:
            warning = NO_WARNING
            tip = 'This shortcut is valid.'
            icon = get_std_icon('DialogApplyButton')

        self.warning = warning
        self.conflicts = conflicts

        self.helper_button.setIcon(icon)
        self.button_ok.setEnabled(
            self.warning in [NO_WARNING, SEQUENCE_CONFLICT])
        self.label_warning.setText(tip)
        # Everytime after update warning message, update the label height
        new_height = self.label_warning.sizeHint().height()
        self.label_warning.setMaximumHeight(new_height)

    def set_sequence_from_str(self, sequence):
        """
        This is a convenience method to set the new QKeySequence of the
        shortcut editor from a string.
        """
        self._qsequences = [QKeySequence(s) for s in sequence.split(', ')]
        self.update_warning()

    def set_sequence_to_default(self):
        """Set the new sequence to the default value defined in the config."""
        sequence = CONF.get_default(
            'shortcuts', "{}/{}".format(self.context, self.name))
        self._qsequences = sequence.split(', ')
        self.update_warning()

    def back_new_sequence(self):
        """Remove the last subsequence from the sequence compound."""
        self._qsequences = self._qsequences[:-1]
        self.update_warning()

    def clear_new_sequence(self):
        """Clear the new sequence."""
        self._qsequences = []
        self.update_warning()

    def unbind_shortcut(self):
        """Unbind the shortcut."""
        self._qsequences = []
        self.accept()

    def accept_override(self):
        """Unbind all conflicted shortcuts, and accept the new one"""
        conflicts = self.check_conflicts()
        if conflicts:
            for shortcut in conflicts:
                shortcut.key = ''
        self.accept()


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
    def __init__(self, parent, text_color=None, text_color_highlight=None):
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
        if text_color is None:
            self.text_color = palette.text().color().name()
        else:
            self.text_color = text_color

        if text_color_highlight is None:
            self.text_color_highlight = \
                palette.highlightedText().color().name()
        else:
            self.text_color_highlight = text_color_highlight

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
        self.pattern = re.compile(r'')

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
    def __init__(self,
                 parent=None, text_color=None, text_color_highlight=None):
        QTableView.__init__(self, parent)
        self._parent = parent
        self.finder = None

        self.source_model = ShortcutsModel(
                                    self,
                                    text_color=text_color,
                                    text_color_highlight=text_color_highlight)
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
            if str(sh1.key) == '':
                continue
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

    def setup_page(self):
        self.ICON = ima.icon('keyboard')
        # Widgets
        self.table = ShortcutsTable(self, text_color=ima.MAIN_FG_COLOR)
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
        """Reset to default values of the shortcuts making a confirmation."""
        reset = QMessageBox.warning(self, _("Shortcuts reset"),
                                    _("Do you want to reset "
                                      "to default values?"),
                                    QMessageBox.Yes | QMessageBox.No)
        if reset == QMessageBox.No:
            return
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

    table.check_shortcuts()


if __name__ == '__main__':
    test()
