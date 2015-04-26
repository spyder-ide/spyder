# -*- coding: utf-8 -*-
#
# Copyright © 2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Shortcut management"""

from __future__ import print_function
<<<<<<< HEAD
import sys

from spyderlib.qt.QtGui import (QVBoxLayout, QTableView, QMessageBox,
                                QPushButton, QKeySequence)
from spyderlib.qt.QtCore import Qt, QAbstractTableModel, QModelIndex
=======
import os
import re
import sys

from spyderlib.qt.QtGui import (QVBoxLayout, QTableView, QMessageBox,
                                QPushButton, QKeySequence, QDialog,
                                QDialogButtonBox, QLabel, QGridLayout,
                                QLineEdit, QAbstractItemView,
                                QSortFilterProxyModel, QStyledItemDelegate,
                                QStyleOptionViewItemV4, QApplication,
                                QTextDocument, QStyle, QSpacerItem,
                                QAbstractTextDocumentLayout)
from spyderlib.qt.QtCore import (Qt, QAbstractTableModel, QModelIndex, QSize,
                                 QPoint)
>>>>>>> 69e106a... Fixing merge
from spyderlib.qt.compat import to_qvariant, from_qvariant
import spyderlib.utils.icon_manager as ima

# Local imports
from spyderlib.baseconfig import _, debug_print
from spyderlib.guiconfig import (get_shortcut, set_shortcut,
                                 iter_shortcuts, reset_shortcuts)
from spyderlib.plugins.configdialog import GeneralConfigPage
<<<<<<< HEAD
=======
Qt.Key_F

MODIFIERS = {Qt.Key_Shift: Qt.SHIFT,
             Qt.Key_Control: Qt.CTRL,
             Qt.Key_Alt: Qt.ALT,
             Qt.Key_Meta: Qt.META}

SINGLE_KEYS = ["F{}".format(_i) for _i in range(1, 36)] + [ "Delete", "Escape"]
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


class HTMLDelegate(QStyledItemDelegate):
    """With this delegate, a QListWidgetItem can render HTML.

    Taken from http://stackoverflow.com/a/5443112/2399799
    """
    def paint(self, painter, option, index):
        options = QStyleOptionViewItemV4(option)
        self.initStyleOption(options, index)

        style = (QApplication.style() if options.widget is None
                 else options.widget.style())

        doc = QTextDocument()
        doc.setDocumentMargin(9)  # FIXME: Need to center vertical text
        doc.setHtml(options.text)

        options.text = ""
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        ctx = QAbstractTextDocumentLayout.PaintContext()

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, options)
        painter.save()
        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        doc.documentLayout().draw(painter, ctx)

        painter.restore()

    def sizeHint(self, option, index):
        options = QStyleOptionViewItemV4(option)
        self.initStyleOption(options, index)

        doc = QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())

        return QSize(doc.idealWidth(), doc.size().height())


class ShortcutFinder(QDialog):
    def __init__(self, parent, callback=None):
        super(ShortcutFinder, self).__init__(parent)
        style = """
            QDialog {
              margin:0px;
              border: 1px solid grey;
              padding:0px;
              border-radius: 2px;
            }"""
        self.setStyleSheet(style)

        # widget setup
        self.setWindowFlags(Qt.Window | Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setWindowOpacity(0.90)

        self.text_edit = QLineEdit()
        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        margin = 1
        layout.setContentsMargins(margin, margin, margin, margin)
        self.setLayout(layout)

        if callback:
            self.text_edit.textChanged.connect(callback)

    def text(self):
        """ """
        return self.text_edit.text()

    def set_text(self, text):
        text = text.strip()
        self.text_edit.setText(text)

    def keyPressEvent(self, event):
        """ """
        key = event.key()
        if key in [Qt.Key_Up]:
            self.parent().previous_row()
        elif key in [Qt.Key_Down]:
            self.parent().next_row()
        elif key in [Qt.Key_Enter, Qt.Key_Return]:
            self.accept()
        super(ShortcutFinder, self).keyPressEvent(event)


class ShortcutEditor(QDialog):
    """ """
    def __init__(self, parent, context, name, sequence):
        super(ShortcutEditor, self).__init__(parent)
        self.npressed = 0
        self.keys = set()
        self.key_modifiers = set()
        self.key_non_modifiers = list()
        self.key_text = list()
        self.sequence = sequence
        self.new_sequence = None
        self.edit_state = True

        # Widgets
        self.label_info = QLabel(_("Press the new shortcut and select 'Ok': \n"
                                   "(Press 'Tab' once to switch focus between "
                                   "shortcut entry and buttons)"))
        self.label_current_sequence = QLabel(_("Current shortcut:"))
        self.text_current_sequence = QLabel(sequence)
        self.label_new_sequence = QLabel(_("New shortcut:"))
        self.text_new_sequence = QLineEdit()

        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_ok = bbox.button(QDialogButtonBox.Ok)
        self.button_cancel = bbox.button(QDialogButtonBox.Cancel)

        self.text_new_sequence.setReadOnly(True)
        self.text_new_sequence.setFocusPolicy(Qt.NoFocus)
        self.button_ok.setFocusPolicy(Qt.NoFocus)
        self.button_ok.setEnabled(False)
        self.button_cancel.setFocusPolicy(Qt.NoFocus)

        # Widget setup
        self.setWindowTitle(_('Shortcut: {0}').format(name))

        spacing = 24
        layout_sequence = QGridLayout()
        layout_sequence.addWidget(self.label_info, 0, 0, 1, 2)
        layout_sequence.addItem(QSpacerItem(spacing, spacing), 1, 0, 1, 2)
        layout_sequence.addWidget(self.label_current_sequence, 2, 0)
        layout_sequence.addWidget(self.text_current_sequence, 2, 1)
        layout_sequence.addWidget(self.label_new_sequence, 3, 0)
        layout_sequence.addWidget(self.text_new_sequence, 3, 1)

        layout = QVBoxLayout()
        layout.addLayout(layout_sequence)
        layout.addSpacing(spacing)
        layout.addWidget(bbox)
        self.setLayout(layout)

        # Signals
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)

    def keyPressEvent(self, e):
        """Qt override"""
        key = e.key()

        self.npressed += 1
        self.key_non_modifiers.append(key)
        self.key_modifiers.add(key)
        self.key_text.append(e.text())

        debug_print('key %s, npressed: %s' % (key, self.npressed))

        if key == Qt.Key_unknown:
            return

        # The user clicked just and only the special keys
        # Ctrl, Shift, Alt, Meta.
        if (key == Qt.Key_Control or
                key == Qt.Key_Shift or
                key == Qt.Key_Alt or
                key == Qt.Key_Meta):
            return

        # Check if valid keys
        if key not in VALID_KEYS:
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

    def keyReleaseEvent(self, e):
        """Qt override"""
        self.npressed -= 1
        if self.npressed <= 0:
            if len(self.keys) == 1 and list(self.keys)[0] == Qt.Key_Tab:
                self.toggle_state()

            if not self.edit_state:
                self.nonedit_keyrelease(e)
            else:
                debug_print('keys: {}'.format(self.keys))
                if self.keys and len(self.keys) <= 4:
                    self.validate_sequence()
                self.keys = set()
                self.key_modifiers = set()
                self.key_non_modifiers = list()
                self.key_text = list()
                self.npressed = 0

    def nonedit_keyrelease(self, e):
        """ """
        key = e.key()

        if key == Qt.Key_Escape:
            self.reject()

        if key in [Qt.Key_Left, Qt.Key_Right, Qt.Key_Up,
                   Qt.Key_Down]:

            if self.button_ok.hasFocus():
                self.button_cancel.setFocus()
            else:
                self.button_ok.setFocus()

    def validate_sequence(self):
        """ """
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

        keys = []
        for i in range(len(self.keys)):
            key_seq = 0
            for m in self.key_modifiers:
                key_seq += MODIFIERS[m]
            key_seq += self.key_non_modifiers[i]
            keys.append(key_seq)

        sequence = QKeySequence(*keys)
        self.set_sequence(sequence.toString())

    def toggle_state(self):
        """ """
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

    def set_sequence(self, sequence):
        """ """
        if self.sequence != sequence:
            self.text_new_sequence.setText(sequence)
            self.button_ok.setEnabled(True)
            self.new_sequence = sequence
        else:
            self.text_new_sequence.setText(sequence)
            self.button_ok.setEnabled(False)

    def check_conflicts(self):
        """Check shortcuts for conflicts"""
        conflicts = []
        for index, sh1 in enumerate(self.model.shortcuts):
            if index == len(self.model.shortcuts)-1:
                break
            for sh2 in self.model.shortcuts[index+1:]:
                if sh2 is sh1:
                    continue
                if str(sh2.key) == str(sh1.key) \
                   and (sh1.context == sh2.context or sh1.context == '_' or
                        sh2.context == '_'):
                    conflicts.append((sh1, sh2))
>>>>>>> 69e106a... Fixing merge


class Shortcut(object):
    """ """
    def __init__(self, context, name, key=None):
        self.context = context
        self.name = name
        self.key = key

    def __str__(self):
        return "%s/%s: %s" % (self.context, self.name, self.key)

    def load(self):
        self.key = get_shortcut(self.context, self.name)

    def save(self):
        set_shortcut(self.context, self.name, self.key)


CONTEXT, NAME, SEQUENCE = list(range(3))


class ShortcutsModel(QAbstractTableModel):
    """ """
    def __init__(self, parent):
        QAbstractTableModel.__init__(self)
        self.shortcuts = []

    def sortByName(self):
        self.shortcuts = sorted(self.shortcuts,
                                key=lambda x: x.context+'/'+x.name)
        self.reset()

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(QAbstractTableModel.flags(self, index))

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or \
           not (0 <= index.row() < len(self.shortcuts)):
            return to_qvariant()

        shortcut = self.shortcuts[index.row()]
        key = shortcut.key
        column = index.column()

        if role == Qt.DisplayRole:
            if column == CONTEXT:
                return to_qvariant(_(shortcut.context.capitalize()))
            elif column == NAME:
<<<<<<< HEAD
                return to_qvariant(_(shortcut.name.capitalize()))
=======
                return to_qvariant(self._enrich_text(shortcut.name))
>>>>>>> 69e106a... Fixing merge
            elif column == SEQUENCE:
                text = QKeySequence(key).toString(QKeySequence.NativeText)
                return to_qvariant(text)
        elif role == Qt.TextAlignmentRole:
            return to_qvariant(int(Qt.AlignHCenter | Qt.AlignVCenter))
        return to_qvariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
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
                return to_qvariant(_("Sequence"))
        return to_qvariant()

    def rowCount(self, index=QModelIndex()):
        return len(self.shortcuts)

    def columnCount(self, index=QModelIndex()):
        return 3
<<<<<<< HEAD
    
=======

>>>>>>> 69e106a... Fixing merge
    def setData(self, index, value, role=Qt.EditRole):
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
        """ """
        self.letters = text
        self.reset()

    def row(self, row_num):
        return self.shortcuts[row_num]

    def reset(self):
#        fm = self.label.fontMetrics()
#        for s in self.shortcuts:
#            self.widths.append(fm.width(s.name))
##        self.header_width = self.parent().horizontalHeader()
        self.beginResetModel()
        self.endResetModel()


<<<<<<< HEAD
=======
class CustomSortFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(CustomSortFilterProxy, self).__init__(parent)
        self._parent = parent
        self.pattern = re.compile(u'')

    def set_filter(self, text):
        """
        text : string
            The string to be used for pattern matching.
        """
        fuzzy_text = [ch for ch in text if ch != ' ']
        fuzzy_text = '.*'.join(fuzzy_text)
        regex = '({0})'.format(fuzzy_text)
        self.pattern = re.compile(regex)
        self.invalidateFilter()

    def filterAcceptsRow(self, row_num, parent):
        """Qt override
        Reimplemented from base class to allow the use of custom filtering
        """
        model = self.sourceModel()
        name = model.row(row_num).name
        r = re.search(self.pattern, name)

        if r is None:
            return False
        else:
            return True


>>>>>>> 69e106a... Fixing merge
class ShortcutsTable(QTableView):
    def __init__(self, parent=None):
        QTableView.__init__(self, parent)
        self.model = ShortcutsModel()
        self.setModel(self.model)
        self.load_shortcuts()
        self.npressed = 0
        self.keys = set()
                     
    def adjust_cells(self):
        self.resizeColumnsToContents()
#        self.resizeRowsToContents()
        self.horizontalHeader().setStretchLastSection(True)

    def load_shortcuts(self):
        shortcuts = []
        for context, name, keystr in iter_shortcuts():
            shortcut = Shortcut(context, name, keystr)
            shortcuts.append(shortcut)
        shortcuts = sorted(shortcuts, key=lambda x: x.context+x.name)
        self.model.shortcuts = shortcuts
        self.model.reset()
        self.adjust_cells()

    def check_shortcuts(self):
        """Check shortcuts for conflicts"""
        conflicts = []
        for index, sh1 in enumerate(self.model.shortcuts):
            if index == len(self.model.shortcuts)-1:
                break
            for sh2 in self.model.shortcuts[index+1:]:
                if sh2 is sh1:
                    continue
                if str(sh2.key) == str(sh1.key) \
                   and (sh1.context == sh2.context or sh1.context == '_'
                        or sh2.context == '_'):
                    conflicts.append((sh1, sh2))
        if conflicts:
            self.parent().show_this_page.emit()
            cstr = "\n".join(['%s <---> %s' % (sh1, sh2)
                              for sh1, sh2 in conflicts])
            QMessageBox.warning(self, _( "Conflicts"),
                                _("The following conflicts have been "
                                  "detected:")+"\n"+cstr, QMessageBox.Ok)

    def save_shortcuts(self):
        self.check_shortcuts()
        for shortcut in self.model.shortcuts:
            shortcut.save()

    def show_editor(self):
        """ """
        index = self.proxy_model.mapToSource(self.currentIndex())
        row, column = index.row(), index.column()
        context = self.source_model.shortcuts[row].context
        name = self.source_model.shortcuts[row].name

        sequence_index = self.source_model.index(row, SEQUENCE)
        sequence = sequence_index.data()

        dialog = ShortcutEditor(self, context, name, sequence)

        if dialog.exec_():
            new_sequence = dialog.new_sequence
            self.source_model.setData(sequence_index, new_sequence)

    def set_regex(self, regex=None, reset=False):
        """ """
        if reset:
            text = ''
        else:
            text = self.finder.text().replace(' ', '')

        self.proxy_model.set_filter(text)
        self.source_model.update_search_letters(text)

        if self.last_regex != regex:
            self.selectRow(0)
        self.last_regex = regex

    def next_row(self):
        """ """
        row = self.currentIndex().row()
        rows = self.proxy_model.rowCount()
        if row + 1 == rows:
            row = -1
        self.selectRow(row + 1)

    def previous_row(self):
        """ """
        row = self.currentIndex().row()
        rows = self.proxy_model.rowCount()
        if row == 0:
            row = rows
        self.selectRow(row - 1)

    def set_finder_pos(self):
        """ """
        head = self.horizontalHeader()
        head_h = head.height()
        head_x = head.rect().x() + head.sectionSize(CONTEXT)
        head_y = head.rect().y()
        finder_h = self.finder.height()

        global_x = head.mapToGlobal(QPoint(head_x, head_y)).x()
        global_y = head.mapToGlobal(QPoint(head_x, head_y)).y() + \
            head_h/2 - finder_h/2 + 4

        self.finder.setFixedWidth(head.sectionSize(NAME))
        self.finder.move(QPoint(global_x, global_y))

    def keyPressEvent(self, event):
        """ """
        key = event.key()
        if key in [Qt.Key_Enter, Qt.Key_Return]:
            self.show_editor()
        elif key not in [Qt.Key_Escape, Qt.Key_Space]:
            text = event.text()
            if text:
                self.finder = ShortcutFinder(self, self.set_regex)
                self.set_finder_pos()
                self.finder.set_text(text)
                while self.finder.exec_():
                    self.show_editor()
                self.set_regex(reset=True)
        super(ShortcutsTable, self).keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """ """
        self.show_editor()


class ShortcutsConfigPage(GeneralConfigPage):
    CONF_SECTION = "shortcuts"
    
    NAME = _("Keyboard shortcuts")
    ICON = ima.icon('genprefs')
    
    def setup_page(self):
        self.table = ShortcutsTable(self)
        self.table.model.dataChanged.connect(
                     lambda i1, i2, opt='': self.has_been_modified(opt))
        vlayout = QVBoxLayout()
        vlayout.addWidget(self.table)
        reset_btn = QPushButton(_("Reset to default values"))
        reset_btn.clicked.connect(self.reset_to_default)
        vlayout.addWidget(reset_btn)
        self.setLayout(vlayout)
        
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
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    table = ShortcutsTable()
    table.show()
    app.exec_()
    print([str(s) for s in table.model.shortcuts])
    table.check_shortcuts()

if __name__ == '__main__':
    test()