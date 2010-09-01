# -*- coding: utf-8 -*-
#
# Copyright © 2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Shortcut management"""

from PyQt4.QtGui import (QVBoxLayout, QWidget, QComboBox, QItemDelegate,
                         QTableView, QMessageBox, QPushButton)
from PyQt4.QtCore import (Qt, QSize, QAbstractTableModel, QVariant, QModelIndex,
                          SIGNAL)

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import (get_icon, get_shortcut, set_shortcut,
                              iter_shortcuts, reset_shortcuts)
from spyderlib.utils.qthelpers import translate
from spyderlib.plugins.configdialog import GeneralConfigPage


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
                 Qt.ControlModifier: "Ctrl", Qt.AltModifier: "Alt"}
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
        return unicode(self.__str__())
    
    @staticmethod
    def modifier_from_str(modstr):
        for k, v in Key.MODIFIERS.iteritems():
            if v.lower() == modstr.lower():
                return k
    
    @staticmethod
    def key_from_str(keystr):
        for k, v in Key.KEYS.iteritems():
            if v.lower() == keystr.lower():
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
        if isinstance(key, basestring):
            key = keystr2key(key)
        self.key = key
        
    def __str__(self):
        return "%s/%s: %s" % (self.context, self.name, self.key)
    
    def load(self):
        self.key = keystr2key(get_shortcut(self.context, self.name))
    
    def save(self):
        set_shortcut(self.context, self.name, str(self.key))


CONTEXT, NAME, MOD1, MOD2, MOD3, KEY = range(6)

class ShortcutsModel(QAbstractTableModel):
    def __init__(self):
        super(ShortcutsModel, self).__init__()
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
            return QVariant()
        shortcut = self.shortcuts[index.row()]
        key = shortcut.key
        column = index.column()
        if role == Qt.DisplayRole:
            if column == CONTEXT:
                return QVariant(shortcut.context)
            elif column == NAME:
                return QVariant(shortcut.name)
            elif column == MOD1:
                return QVariant(Key.MODIFIERS[key.modifiers[0]])
            elif column == MOD2:
                return QVariant(Key.MODIFIERS[key.modifiers[1]])
            elif column == MOD3:
                return QVariant(Key.MODIFIERS[key.modifiers[2]])
            elif column == KEY:
                return QVariant(Key.KEYS[key.key])
        elif role == Qt.TextAlignmentRole:
            return QVariant(int(Qt.AlignHCenter|Qt.AlignVCenter))
        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return QVariant(int(Qt.AlignHCenter|Qt.AlignVCenter))
            return QVariant(int(Qt.AlignRight|Qt.AlignVCenter))
        if role != Qt.DisplayRole:
            return QVariant()
        if orientation == Qt.Horizontal:
            if section == CONTEXT:
                return QVariant(translate("ShortcutsConfigPage",
                                          "Context"))
            elif section == NAME:
                return QVariant(translate("ShortcutsConfigPage",
                                          "Name"))
            elif section == MOD1:
                return QVariant(translate("ShortcutsConfigPage", "Mod1"))
            elif section == MOD2:
                return QVariant(translate("ShortcutsConfigPage", "Mod2"))
            elif section == MOD3:
                return QVariant(translate("ShortcutsConfigPage", "Mod3"))
            elif section == KEY:
                return QVariant(translate("ShortcutsConfigPage", "Key"))
        return QVariant()

    def rowCount(self, index=QModelIndex()):
        return len(self.shortcuts)

    def columnCount(self, index=QModelIndex()):
        return 6
    
    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid() and 0 <= index.row() < len(self.shortcuts):
            shortcut = self.shortcuts[index.row()]
            key = shortcut.key
            column = index.column()
            if column == MOD1:
                key.modifiers[0] = Key.modifier_from_str(str(value.toString()))
            elif column == MOD2:
                key.modifiers[1] = Key.modifier_from_str(str(value.toString()))
            elif column == MOD3:
                key.modifiers[2] = Key.modifier_from_str(str(value.toString()))
            elif column == KEY:
                key.key = Key.key_from_str(str(value.toString()))
            self.emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"),
                      index, index)
            return True
        return False


class ShortcutsDelegate(QItemDelegate):
    def __init__(self, parent=None):
        super(ShortcutsDelegate, self).__init__(parent)
        self.modifiers = sorted(Key.MODIFIERS.values())
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
        text = index.model().data(index, Qt.DisplayRole).toString()
        if index.column() in (MOD1, MOD2, MOD3, KEY):
            i = editor.findText(text)
            if i == -1:
                i = 0
            editor.setCurrentIndex(i)
        else:
            QItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        if index.column() in (MOD1, MOD2, MOD3, KEY):
            model.setData(index, QVariant(editor.currentText()))
        else:
            QItemDelegate.setModelData(self, editor, model, index)


class ShortcutsTable(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.model = ShortcutsModel()
        self.view = QTableView(self)
        self.view.setModel(self.model)
        self.view.setItemDelegate(ShortcutsDelegate(self))
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)
        self.load_shortcuts()
        
    def load_shortcuts(self):
        shortcuts = []
        for context, name, keystr in iter_shortcuts():
            shortcut = Shortcut(context, name, keystr)
            shortcuts.append(shortcut)
        shortcuts = sorted(shortcuts, key=lambda x: x.context+x.name)
        self.model.shortcuts = shortcuts
        self.model.reset()
        self.view.resizeColumnsToContents()
        
    def save_shortcuts(self):
        conflicts = []
        for index, sh1 in enumerate(self.model.shortcuts):
            if index == len(self.model.shortcuts)-1:
                break
            for sh2 in self.model.shortcuts[index+1:]:
                if sh2 is sh1:
                    continue
                if str(sh2.key) == str(sh1.key):
                    conflicts.append((sh1, sh2))
        if conflicts:
            cstr = "\n".join(['%s <---> %s' % (sh1, sh2)
                              for sh1, sh2 in conflicts])
            QMessageBox.warning(self,
                                translate("ShortcutsConfigPage", "Conflicts"),
                                translate("ShortcutsConfigPage",
                                          "The following conflicts have been "
                                          "detected:")+"\n"+cstr,
                                QMessageBox.Ok)
        for shortcut in self.model.shortcuts:
            shortcut.save()
        

class ShortcutsConfigPage(GeneralConfigPage):
    CONF_SECTION = "shortcuts"
    def get_name(self):
        return self.tr("Keyboard shortcuts")
    
    def get_icon(self):
        return get_icon("genprefs.png")
    
    def setup_page(self):
        self.table = ShortcutsTable(self)
        self.connect(self.table.model,
                     SIGNAL("dataChanged(QModelIndex,QModelIndex)"),
                     lambda i1, i2: self.has_been_modified())
        vlayout = QVBoxLayout()
        vlayout.addWidget(self.table)
        reset_btn = QPushButton(self.tr("Reset to default values"))
        self.connect(reset_btn, SIGNAL('clicked()'), self.reset_to_default)
        vlayout.addWidget(reset_btn)
        self.setLayout(vlayout)
        
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
    print [str(s) for s in table.model.shortcuts]
    table.save_shortcuts()

if __name__ == '__main__':
    test()