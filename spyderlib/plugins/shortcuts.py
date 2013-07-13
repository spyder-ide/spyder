# -*- coding: utf-8 -*-
#
# Copyright © 2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Shortcut management"""

from __future__ import print_function

from spyderlib.qt.QtGui import (QVBoxLayout, QComboBox, QItemDelegate,
                                QTableView, QMessageBox, QPushButton)
from spyderlib.qt.QtCore import (Qt, QSize, QAbstractTableModel, QModelIndex,
                                 SIGNAL)
from spyderlib.qt.compat import to_qvariant, from_qvariant

import sys

# Local imports
from spyderlib.baseconfig import _
from spyderlib.guiconfig import (get_shortcut, set_shortcut,
                                 iter_shortcuts, reset_shortcuts)
from spyderlib.plugins.configdialog import GeneralConfigPage
from spyderlib.py3compat import to_text_string, is_text_string


KEYSTRINGS = ["Escape", "Tab", "Backtab", "Backspace", "Return", "Enter",
              "Delete", "Pause", "Print", "Clear", "Home", "End", "Left",
              "Up", "Right", "Down", "PageUp", "PageDown"] + \
             ["F%d" % _i for _i in range(1, 36)] + \
             ["Space", "Exclam", "QuoteDbl", "NumberSign", "Dollar", "Percent",
              "Ampersand", "Apostrophe", "ParenLeft", "ParenRight", "Asterisk",
              "Plus", "Comma", "Minus", "Period", "Slash"] + \
             [str(_i) for _i in range(10)] + \
             ["Colon", "Semicolon", "Less", "Equal", "Greater", "Question",
              "At"] + [chr(_i) for _i in range(65, 91)] + \
             ["BracketLeft", "Backslash", "BracketRight", "Underscore"]


class Key(object):
    MODIFIERS = {Qt.NoModifier: "", Qt.ShiftModifier: "Shift",
                 Qt.ControlModifier: "Ctrl", Qt.AltModifier: "Alt",
                 Qt.MetaModifier: "Meta"}
    if sys.platform == 'darwin':
        MODIFIERNAMES = {Qt.NoModifier: "", Qt.ShiftModifier: "Shift",
                         Qt.ControlModifier: "Cmd", Qt.AltModifier: "Alt",
                         Qt.MetaModifier: "Ctrl"}
    elif sys.platform == 'win32':
        MODIFIERNAMES = {Qt.NoModifier: "", Qt.ShiftModifier: "Shift",
                         Qt.ControlModifier: "Ctrl", Qt.AltModifier: "Alt",
                         Qt.MetaModifier: "Win"}
    else:
        MODIFIERNAMES = {Qt.NoModifier: "", Qt.ShiftModifier: "Shift",
                         Qt.ControlModifier: "Ctrl", Qt.AltModifier: "Alt",
                         Qt.MetaModifier: "Meta"}
    KEYS = {}
    for attr in KEYSTRINGS:
        KEYS[getattr(Qt, "Key_"+attr)] = attr

    def __init__(self, key, mod1=Qt.NoModifier, mod2=Qt.NoModifier,
                 mod3=Qt.NoModifier):
        modifiers = [mod1, mod2, mod3]
        assert all([mod in self.MODIFIERS for mod in modifiers])
        self.modifiers = sorted(modifiers)
        assert key in self.KEYS
        self.key = key
        
    def __str__(self):
        tlist = []
        for mod in sorted(list(set(self.modifiers))):
            if mod != Qt.NoModifier:
                tlist.append(self.MODIFIERS[mod])
        tlist.append(self.KEYS[self.key])
        return "+".join(tlist)
    
    def __unicode__(self):
        return to_text_string(self.__str__())
    
    @staticmethod
    def modifier_from_str(modstr):
        for k, v in list(Key.MODIFIERS.items()):
            if v.lower() == modstr.lower():
                return k
    
    @staticmethod
    def key_from_str(keystr):
        for k, v in list(Key.KEYS.items()):
            if v.lower() == keystr.lower():
                return k

    @staticmethod
    def modifier_from_name(modname):
        for k, v in list(Key.MODIFIERNAMES.items()):
            if v.lower() == modname.lower():
                return k        

def keystr2key(keystr):
    keylist = keystr.split("+")
    mods = []
    if len(keylist) > 1:
        for modstr in keylist[:-1]:
            mods.append(Key.modifier_from_str(modstr))
    return Key(Key.key_from_str(keylist[-1]), *mods)

class Shortcut(object):
    def __init__(self, context, name, key=None):
        self.context = context
        self.name = name
        if is_text_string(key):
            key = keystr2key(key)
        self.key = key
        
    def __str__(self):
        return "%s/%s: %s" % (self.context, self.name, self.key)
    
    def load(self):
        self.key = keystr2key(get_shortcut(self.context, self.name))
    
    def save(self):
        set_shortcut(self.context, self.name, str(self.key))


CONTEXT, NAME, MOD1, MOD2, MOD3, KEY = list(range(6))

class ShortcutsModel(QAbstractTableModel):
    def __init__(self):
        QAbstractTableModel.__init__(self)
        self.shortcuts = []

    def sortByName(self):
        self.shortcuts = sorted(self.shortcuts,
                                key=lambda x: x.context+'/'+x.name)
        self.reset()

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        column = index.column()
        if column in (MOD1, MOD2, MOD3, KEY):
            return Qt.ItemFlags(QAbstractTableModel.flags(self, index)|
                                Qt.ItemIsEditable)
        else:
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
                return to_qvariant(shortcut.context)
            elif column == NAME:
                return to_qvariant(shortcut.name)
            elif column == MOD1:
                return to_qvariant(Key.MODIFIERNAMES[key.modifiers[0]])
            elif column == MOD2:
                return to_qvariant(Key.MODIFIERNAMES[key.modifiers[1]])
            elif column == MOD3:
                return to_qvariant(Key.MODIFIERNAMES[key.modifiers[2]])
            elif column == KEY:
                return to_qvariant(Key.KEYS[key.key])
        elif role == Qt.TextAlignmentRole:
            return to_qvariant(int(Qt.AlignHCenter|Qt.AlignVCenter))
        return to_qvariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return to_qvariant(int(Qt.AlignHCenter|Qt.AlignVCenter))
            return to_qvariant(int(Qt.AlignRight|Qt.AlignVCenter))
        if role != Qt.DisplayRole:
            return to_qvariant()
        if orientation == Qt.Horizontal:
            if section == CONTEXT:
                return to_qvariant(_("Context"))
            elif section == NAME:
                return to_qvariant(_("Name"))
            elif section == MOD1:
                return to_qvariant(_("Mod1"))
            elif section == MOD2:
                return to_qvariant(_("Mod2"))
            elif section == MOD3:
                return to_qvariant(_("Mod3"))
            elif section == KEY:
                return to_qvariant(_("Key"))
        return to_qvariant()

    def rowCount(self, index=QModelIndex()):
        return len(self.shortcuts)

    def columnCount(self, index=QModelIndex()):
        return 6
    
    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid() and 0 <= index.row() < len(self.shortcuts):
            shortcut = self.shortcuts[index.row()]
            key = shortcut.key
            column = index.column()
            text = from_qvariant(value, str)
            if column == MOD1:
                key.modifiers[0] = Key.modifier_from_name(text)
            elif column == MOD2:
                key.modifiers[1] = Key.modifier_from_name(text)
            elif column == MOD3:
                key.modifiers[2] = Key.modifier_from_name(text)
            elif column == KEY:
                key.key = Key.key_from_str(text)
            self.emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"),
                      index, index)
            return True
        return False


class ShortcutsDelegate(QItemDelegate):
    def __init__(self, parent=None):
        QItemDelegate.__init__(self, parent)
        self.modifiers = sorted(Key.MODIFIERNAMES.values())
        self.mod = None
        self.keys = sorted(Key.KEYS.values())
        self.key = None
        
    def sizeHint(self, option, index):
        fm = option.fontMetrics
        if index.column() in (MOD1, MOD2, MOD3):
            if self.mod is None:
                w = 0
                for mod in self.modifiers:
                    cw = fm.width(mod)
                    if cw > w:
                        w = cw
                        self.mod = mod
            else:
                w = fm.width(self.mod)
            return QSize(w+20, fm.height())
        elif index.column() == KEY:
            if self.key is None:
                w = 0
                for key in self.keys:
                    cw = fm.width(key)
                    if cw > w:
                        w = cw
                        self.key = key
            else:
                w = fm.width(self.key)
            return QSize(w+20, fm.height())
        return QItemDelegate.sizeHint(self, option, index)

    def createEditor(self, parent, option, index):
        if index.column() in (MOD1, MOD2, MOD3):
            combobox = QComboBox(parent)
            combobox.addItems(self.modifiers)
            return combobox
        elif index.column() == KEY:
            combobox = QComboBox(parent)
            combobox.addItems(self.keys)
            return combobox
        else:
            return QItemDelegate.createEditor(self, parent, option,
                                              index)

    def setEditorData(self, editor, index):
        text = from_qvariant(index.model().data(index, Qt.DisplayRole), str)
        if index.column() in (MOD1, MOD2, MOD3, KEY):
            i = editor.findText(text)
            if i == -1:
                i = 0
            editor.setCurrentIndex(i)
        else:
            QItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        if index.column() in (MOD1, MOD2, MOD3, KEY):
            model.setData(index, to_qvariant(editor.currentText()))
        else:
            QItemDelegate.setModelData(self, editor, model, index)


class ShortcutsTable(QTableView):
    def __init__(self, parent=None):
        QTableView.__init__(self, parent)
        self.model = ShortcutsModel()
        self.setModel(self.model)
        self.setItemDelegate(ShortcutsDelegate(self))
        self.load_shortcuts()
                     
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
            self.parent().emit(SIGNAL('show_this_page()'))
            cstr = "\n".join(['%s <---> %s' % (sh1, sh2)
                              for sh1, sh2 in conflicts])
            QMessageBox.warning(self, _( "Conflicts"),
                                _("The following conflicts have been "
                                  "detected:")+"\n"+cstr, QMessageBox.Ok)
        
    def save_shortcuts(self):
        self.check_shortcuts()
        for shortcut in self.model.shortcuts:
            shortcut.save()
        

class ShortcutsConfigPage(GeneralConfigPage):
    CONF_SECTION = "shortcuts"
    
    NAME = _("Keyboard shortcuts")
    ICON = "genprefs.png"
    
    def setup_page(self):
        self.table = ShortcutsTable(self)
        self.connect(self.table.model,
                     SIGNAL("dataChanged(QModelIndex,QModelIndex)"),
                     lambda i1, i2, opt='': self.has_been_modified(opt))
        vlayout = QVBoxLayout()
        vlayout.addWidget(self.table)
        reset_btn = QPushButton(_("Reset to default values"))
        self.connect(reset_btn, SIGNAL('clicked()'), self.reset_to_default)
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