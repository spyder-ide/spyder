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
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt, Slot, QEvent
from qtpy.QtGui import QKeySequence, QIcon
from qtpy.QtWidgets import (
    QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpacerItem, QTableView, QVBoxLayout,
    QKeySequenceEdit, QStyledItemDelegate, QStyle, QStyleOptionButton)

# Local imports
from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.preferences.configdialog import GeneralConfigPage
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import get_std_icon, create_toolbutton
from spyder.utils.stringmatching import get_search_scores
from spyder.widgets.helperwidgets import (CustomSortFilterProxy,
                                          FinderLineEdit, HelperToolButton,
                                          HTMLDelegate, VALID_FINDER_CHARS)


# Valid shortcut keys
SINGLE_KEYS = ["F{}".format(_i) for _i in range(1, 36)] + ["Del", "Esc"]
EDITOR_SINGLE_KEYS = SINGLE_KEYS + ["Home", "End", "Ins", "Enter",
                                    "Return", "Backspace", "Tab",
                                    "PageUp", "PageDown", "Clear", "Pause",
                                    "Left", "Up", "Right", "Down"]

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


class ShortcutEditor(QDialog):
    """A dialog for entering key sequences."""

    def __init__(self, parent, context, name, sequence, shortcuts,
                 shortcut_index=False):
        super(ShortcutEditor, self).__init__(parent)
        self._parent = parent
        self._shortcut_index = shortcut_index
        self.setWindowFlags(self.windowFlags() &
                            ~Qt.WindowContextHelpButtonHint)

        self.context = context
        self.name = name
        self.shortcuts = shortcuts
        self.current_sequence = sequence or _('<None>')
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
        self.setWindowTitle(
            _('Shortcut {}: {}').format(self._shortcut_index + 1, self.name))
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

        layout = QVBoxLayout(self)
        layout.addLayout(layout_sequence)
        layout.addSpacing(10)
        layout.addLayout(button_box)
        layout.setSizeConstraint(layout.SetFixedSize)

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
        # Added for spyder-ide/spyder#5426.  Due to the focusPolicy of
        # Qt.NoFocus for the buttons, if the cancel button was clicked without
        # first setting focus to the button, it would cause a seg fault crash.
        self.button_cancel.setFocus()
        super(ShortcutEditor, self).reject()

    @Slot()
    def accept(self):
        """Slot for accepted signal."""
        # Added for spyder-ide/spyder#5426.  Due to the focusPolicy of
        # Qt.NoFocus for the buttons, if the cancel button was clicked without
        # first setting focus to the button, it would cause a seg fault crash.
        self.button_ok.setFocus()
        super(ShortcutEditor, self).accept()

    def event(self, event):
        """Qt method override."""
        # We reroute all ShortcutOverride events to our keyPressEvent and block
        # any KeyPress and Shortcut event. This allows to register default
        # Qt shortcuts for which no key press event are emitted.
        # See spyder-ide/spyder/issues/10786.
        if event.type() == QEvent.ShortcutOverride:
            self.keyPressEvent(event)
            return True
        elif event.type() in [QEvent.KeyPress, QEvent.Shortcut]:
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
            if (shortcut.context, shortcut.name) == (self.context, self.name):
                continue
            if shortcut.context in [self.context, '_'] or self.context == '_':
                for shortcut_qsequence in shortcut.qsequences:
                    if shortcut_qsequence.isEmpty():
                        continue
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
            template = '<p style="margin-bottom: 0.3em">{0}</p>{1}{2}'
            tip_title = _('This key sequence conflicts with:')
            tip_body = ''
            for s in conflicts:
                tip_body += '&nbsp;' * 2
                tip_body += ' - {0}: <b>{1}</b><br>'.format(s.context, s.name)
            tip_body += '<br>'
            if len(conflicts) == 1:
                tip_override = _("Press 'Ok' to unbind it and assign it to")
            else:
                tip_override = _("Press 'Ok' to unbind them and assign it to")
            tip_override += ' <b>{}</b>.'.format(self.name)
            tip = template.format(tip_title, tip_body, tip_override)
            icon = get_std_icon('MessageBoxWarning')
        elif new_sequence in BLACKLIST:
            warning = IN_BLACKLIST
            tip = _('This key sequence is forbidden.')
            icon = get_std_icon('MessageBoxWarning')
        elif self.check_singlekey() is False or self.check_ascii() is False:
            warning = INVALID_KEY
            tip = _('This key sequence is invalid.')
            icon = get_std_icon('MessageBoxWarning')
        else:
            warning = NO_WARNING
            tip = _('This key sequence is valid.')
            icon = get_std_icon('DialogApplyButton')

        self.warning = warning
        self.conflicts = conflicts

        self.helper_button.setIcon(icon)
        self.button_ok.setEnabled(
            self.warning in [NO_WARNING, SEQUENCE_CONFLICT])
        self.label_warning.setText(tip)

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
                shortcut.clear_keystr(self.new_sequence)
        self.accept()


class Shortcut(object):
    """
    Shortcut convenience class for holding shortcut context, name,
    original ordering index, key sequence for the shortcut and localized text.
    """

    def __init__(self, context, name, keystrs=None):
        self.index = 0  # Sorted index. Populated when loading shortcuts
        self.context = context
        self.name = name
        self.keystrs = keystrs if keystrs is not None else [""]

    @property
    def keystrs(self):
        """
        Return a list of string representations of the key sequences binded
        to this shortcut.
        """
        return self._keystrs.copy()

    @keystrs.setter
    def keystrs(self, keystrs):
        """
        Set the namespace for the list of string representations of the
        key sequences that need to be binded to this shortcut.
        """
        if isinstance(keystrs, str):
            self._keystrs = [keystrs]
        else:
            self._keystrs = [str(v) for v in keystrs]
        return self._keystrs.copy()

    @property
    def qsequences(self):
        """
        Return the list of Qt key sequences that are binded to this shortcut.
        """
        return (QKeySequence.fromString(keystr) for keystr in self.keystrs)

    def clear_keystr(self, keystr_to_clear):
        """
        Remove the given key str from the list of shortcuts.
        """
        for i, keystr in enumerate(self._keystrs):
            if keystr_to_clear == keystr:
                self._keystrs[i] = ''

    def set_keystr_at(self, index, value):
        """
        Set the string representation of the key sequence at the given index.
        """
        while len(self._keystrs) <= index:
            self._keystrs.append('')
        self._keystrs[index] = str(value)

        # We clear all duplicates of new_keystr everywhere but at the
        # given index, because we don't want the same shortcut to be stored
        # twice here.
        for i, keystr in enumerate(self._keystrs):
            if i != index and keystr == value:
                self._keystrs[i] = ''

    def get_native_keystr_at(self, index):
        """
        Return a platform specific string representation of the key sequence
        stored at the given index.
        """
        try:
            return QKeySequence(
                self.keystrs[index]).toString(QKeySequence.NativeText)
        except IndexError:
            return ''

    def __str__(self):
        return "{0}/{1}: {2}".format(
            self.context, self.name, '; '.join(self.keystrs))

    def load(self):
        self.keystrs = CONF.get_shortcut(self.context, self.name)

    def save(self):
        # TODO!: Return the full list of keystrs when Spyder can handle this
        # correctly.
        CONF.set_shortcut(self.context, self.name, self.keystrs[0])


CONTEXT, NAME, SEQUENCE, SEQUENCE2, SEARCH_SCORE = [0, 1, 2, 3, 4]


class ShortcutsModel(QAbstractTableModel):
    def __init__(self, parent, text_color=None):
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
        flags = QAbstractTableModel.flags(self, index)
        flags &= ~Qt.ItemIsSelectable
        return Qt.ItemFlags(int(flags))

    def data(self, index, role=Qt.DisplayRole):
        """Qt Override."""
        row = index.row()
        if not index.isValid() or not (0 <= row < len(self.shortcuts)):
            return to_qvariant()

        shortcut = self.shortcuts[row]
        column = index.column()
        if role == Qt.DisplayRole:
            if column == CONTEXT:
                return to_qvariant(shortcut.context)
            elif column == NAME:
                color = self.text_color
                text = self.rich_text[row]
                text = '<p style="color:{0}">{1}</p>'.format(color, text)
                return to_qvariant(text)
            elif column == SEQUENCE:
                return to_qvariant(shortcut.get_native_keystr_at(0))
            elif column == SEQUENCE2:
                return to_qvariant(shortcut.get_native_keystr_at(1))
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
                return to_qvariant(_("Shortcut 1"))
            elif section == SEQUENCE2:
                return to_qvariant(_("Shortcut 2"))
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
                shortcut.set_keystr_at(0, text)
            elif column == SEQUENCE2:
                shortcut.set_keystr_at(1, text)
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


# ---- Delegates
class NameDelegate(HTMLDelegate):
    """
    This delegate is used to prevent mouse over highlight and the painting
    of a focus frame in the NAME column of the Shortcuts table.
    """

    def paint(self, painter, option, index):
        """
        Override Qt method to prevent mouse over highlight and the painting
        of a focus frame.
        """
        option.state &= ~QStyle.State_MouseOver
        option.state &= ~QStyle.State_KeyboardFocusChange
        super(NameDelegate, self).paint(painter, option, index)


class ContextDelegate(QStyledItemDelegate):
    """
    This delegate is used to prevent mouse over highlight and the painting
    of a focus frame in the CONTEXT column of the Shortcuts table.
    """

    def paint(self, painter, option, index):
        """
        Override Qt method to prevent mouse over highlight and the painting
        of a focus frame.
        """
        option.state &= ~QStyle.State_MouseOver
        option.state &= ~QStyle.State_KeyboardFocusChange
        super(ContextDelegate, self).paint(painter, option, index)


class SequenceDelegate(QStyledItemDelegate):

    def __init__(self, parent, margins=0):
        super(SequenceDelegate, self).__init__(parent)
        self._margins = margins
        self._widget = QPushButton(self.parent())
        self._widget.setAutoDefault(True)
        self._widget.hide()

    def paint(self, painter, option, index):
        button = QStyleOptionButton()

        self._widget.setDefault(bool(option.state & QStyle.State_HasFocus))
        self._widget.initStyleOption(button)

        button.rect = option.rect.adjusted(
            self._margins, self._margins,
            -2 * self._margins, -2 * self._margins)
        button.text = index.data()
        button.state = option.state
        if bool(option.state & QStyle.State_HasFocus):
            button.state |= QStyle.State_KeyboardFocusChange
        if (self.parent()._mouse_pressed_pos is not None and
                option.rect.contains(self.parent()._mouse_pressed_pos)):
            if bool(option.state & QStyle.State_MouseOver):
                button.state |= QStyle.State_Sunken
            else:
                button.state |= QStyle.State_MouseOver
        style = self._widget.style()
        style = self._widget.style()
        style.drawControl(QStyle.CE_PushButton, button, painter, self._widget)


class ShortcutsTable(QTableView):
    def __init__(self, parent=None, text_color=None):
        QTableView.__init__(self, parent)
        self._parent = parent
        self.finder = None
        self.setMouseTracking(True)
        self.setShowGrid(False)
        self.setSortingEnabled(True)

        self.clicked.connect(self._handle_mouse_clicked)
        self.pressed.connect(self._handle_mouse_pressed)
        self._mouse_pressed_pos = None

        # Setup model.
        self.source_model = ShortcutsModel(self, text_color=text_color)
        self.proxy_model = CustomSortFilterProxy(self)
        self.last_regex = ''

        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setDynamicSortFilter(True)
        self.proxy_model.setFilterKeyColumn(NAME)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setModel(self.proxy_model)

        self.selectionModel().currentChanged.connect(
            self._handle_current_changed)

        # Setup columns.
        self.hideColumn(SEARCH_SCORE)
        self.setItemDelegateForColumn(NAME, NameDelegate(self, margin=9))
        self.setItemDelegateForColumn(CONTEXT, ContextDelegate(self))
        self.setItemDelegateForColumn(
            SEQUENCE, SequenceDelegate(self, margins=2))
        self.setItemDelegateForColumn(
            SEQUENCE2, SequenceDelegate(self, margins=2))

        # Setup headers
        header = self.horizontalHeader()
        header.setSectionResizeMode(CONTEXT, header.Fixed)
        header.setSectionResizeMode(NAME, header.Fixed)
        header.setSectionResizeMode(SEQUENCE, header.Stretch)
        header.setSectionResizeMode(SEQUENCE2, header.Stretch)
        self.verticalHeader().hide()

        self.load_shortcuts()

    def adjust_cells(self):
        """Adjust column size based on contents."""
        self.resizeColumnsToContents()
        fm = self.horizontalHeader().fontMetrics()
        names = [fm.width(s.name + ' '*9) for s in self.source_model.shortcuts]
        self.setColumnWidth(NAME, max(names))

    def load_shortcuts(self):
        """Load shortcuts and assign to table model."""
        shortcuts = []
        for context, name, keystr in CONF.iter_shortcuts():
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
            for sh1_keystr in sh1.keystrs:
                if sh1_keystr == '':
                    continue
                for sh2 in self.source_model.shortcuts[index+1:]:
                    if sh2 is sh1:
                        continue
                    if sh1_keystr in sh2.keystrs \
                       and (sh1.context == sh2.context or
                            sh1.context == '_' or
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
        if column not in [SEQUENCE, SEQUENCE2]:
            return

        shortcuts = self.source_model.shortcuts
        context = shortcuts[row].context
        name = shortcuts[row].name
        shortcut_index = 0 if column == SEQUENCE else 1

        sequence_index = self.source_model.index(row, column)
        sequence = sequence_index.data()

        dialog = ShortcutEditor(self, context, name, sequence, shortcuts,
                                shortcut_index)

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

    def _handle_mouse_clicked(self, index):
        """Qt Override."""
        if index.column() in [SEQUENCE, SEQUENCE2]:
            self.show_editor()
            self.update()

    def _handle_mouse_pressed(self, index):
        """Qt Override."""
        if index.column() in [SEQUENCE, SEQUENCE2]:
            self.setCurrentIndex(index)

    def mousePressEvent(self, event):
        self._mouse_pressed_pos = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._mouse_pressed_pos = None
        super().mouseReleaseEvent(event)
        # We need to emit a data changed signal to force a repaint of the
        # previously pressed button.
        self.model().dataChanged.emit(self.currentIndex(), self.currentIndex())

    def _handle_current_changed(self, current, previous):
        if current.column() in [NAME, CONTEXT]:
            if not previous.isValid():
                self.setCurrentIndex(self.model().index(0, SEQUENCE))
            elif previous.column() in [SEQUENCE, SEQUENCE2]:
                self.setCurrentIndex(previous)
            else:
                self.setCurrentIndex(self.model().index(
                    current.row(), SEQUENCE))


class ShortcutsConfigPage(GeneralConfigPage):
    CONF_SECTION = "shortcuts"
    NAME = _("Keyboard shortcuts")

    def setup_page(self):
        self.ICON = ima.icon('keyboard')
        # Widgets
        self.table = ShortcutsTable(self, text_color=ima.MAIN_FG_COLOR)
        self.finder = FinderLineEdit(self.table, self.table.set_regex)
        self.table.finder = self.finder
        self.table.finder.setPlaceholderText(
            _("Search for a shortcut in the table above"))
        self.label_finder = QLabel(_('Search: '))
        self.reset_btn = QPushButton(_("Reset to default values"))
        self.top_label = QLabel(
            _("Here you can browse the list of all available shortcuts in "
              "Spyder. You can also customize them by double-clicking on any "
              "entry in this table."))
        self.top_label.setWordWrap(True)

        # Layout
        hlayout = QHBoxLayout()
        vlayout = QVBoxLayout()
        vlayout.addWidget(self.top_label)
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

    def reset_to_default(self, force=False):
        """Reset to default values of the shortcuts making a confirmation."""
        if not force:
            reset = QMessageBox.warning(
                self,
                _("Shortcuts reset"),
                _("Do you want to reset to default values?"),
                QMessageBox.Yes | QMessageBox.No)
            if reset == QMessageBox.No:
                return

        CONF.reset_shortcuts()
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
    table.setMinimumWidth(650)
    table.setMinimumHeight(400)
    table.show()
    app.exec_()

    table.check_shortcuts()


if __name__ == '__main__':
    test()
