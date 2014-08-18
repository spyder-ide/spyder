# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Layout dialogs"""

import sys

from spyderlib.baseconfig import _

from spyderlib.qt.QtGui import (QVBoxLayout, QHBoxLayout,
                                QDialogButtonBox, QComboBox, QPushButton,
                                QTableView, QAbstractItemView,
                                QDialog, QGroupBox)
from spyderlib.qt.QtCore import (Qt, QSize, SIGNAL, SLOT,
                                 QAbstractTableModel, QModelIndex)
from spyderlib.qt.compat import (to_qvariant)
from spyderlib.py3compat import to_text_string


class LayoutModel(QAbstractTableModel):
    """ """
    def __init__(self, parent, order, active):
        QAbstractTableModel.__init__(self)
        self.parent = parent
        self.order = order
        self.active = active
        self.__rows = []
        self.set_data(order, active)

    def set_data(self, order, active):
        """ """
        self.__rows = []
        self.order = order
        self.active = active
        for name in order:
            if name in active:
                row = [name, True]
            else:
                row = [name, False]
            self.__rows.append(row)

    def flags(self, index):
        """Override Qt method"""
        if not index.isValid():
            return Qt.ItemIsEnabled
        column = index.column()
        if column in [0]:
            return Qt.ItemFlags(Qt.ItemIsEnabled |
                                Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
#                                | Qt.ItemIsEditable )
        else:
            return Qt.ItemFlags(Qt.ItemIsEnabled)

    def data(self, index, role=Qt.DisplayRole):
        """Override Qt method"""
        if not index.isValid() or not 0 <= index.row() < len(self.__rows):
            return to_qvariant()
        row = index.row()
        column = index.column()

        name = self.row(row)[0]
        state = self.row(row)[1]

        if role == Qt.DisplayRole:# or role == Qt.EditRole:
            if column == 0:
                return to_qvariant(name)
        elif role == Qt.CheckStateRole:
            if column == 0:
                if state:
                    return Qt.Checked
                else:
                    return Qt.Unchecked
            if column == 1:
                return to_qvariant(state)
        return to_qvariant()

    def setData(self, index, value, role):
        """ """
        row = index.row()
        name = self.row(row)[0]
        state = self.row(row)[1]

        if role == Qt.CheckStateRole:
            self.set_row(row, [name, not state])
            self.parent.setCurrentIndex(index)
            self.parent.setFocus()
            self.emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"),
                      index, index)
            return True
#        elif role == Qt.EditRole:
#            self.set_row(row, [to_text_string(value), state])
#            self.emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"),
#                      index, index)
#            return True
        return True

    def rowCount(self, index=QModelIndex()):
        """Override Qt method"""
        return len(self.__rows)

    def columnCount(self, index=QModelIndex()):
        """Override Qt method"""
        return 2

    def row(self, rownum):
        """ """
        if self.__rows == []:
            return [None, None]
        else:
            return self.__rows[rownum]

    def set_row(self, rownum, value):
        """ """
        self.__rows[rownum] = value


class LayoutSaveDialog(QDialog):
    """ """
    def __init__(self, order):
        QDialog.__init__(self)

        self.combo_box = QComboBox(self)
        self.combo_box.addItems(order)
        self.combo_box.setEditable(True)
        self.combo_box.clearEditText()
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok |
                                           QDialogButtonBox.Cancel,
                                           Qt.Horizontal, self)
        self.button_ok = self.button_box.button(QDialogButtonBox.Ok)
        self.button_cancel = self.button_box.button(QDialogButtonBox.Cancel)

        self.dialog_size = QSize(300, 100)
        self.setWindowTitle('Save layout as')

        layout = QVBoxLayout()
        layout.addWidget(self.combo_box)
        layout.addWidget(self.button_box)

        self.setModal(True)
        self.setLayout(layout)
        self.setMinimumSize(self.dialog_size)
        self.setFixedSize(self.dialog_size)
        self.connect(self.button_box, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(self.button_box, SIGNAL("rejected()"), self.close)
        self.connect(self.combo_box, SIGNAL("editTextChanged(QString)"),
                     self.check_text)
        self.button_ok.setEnabled(False)

    def check_text(self, text):
        """Disable empty layout name possibility"""
        if to_text_string(text) == u'':
            self.button_ok.setEnabled(False)
        else:
            self.button_ok.setEnabled(True)


class LayoutSettingsDialog(QDialog):
    """Layout settings dialog"""
    def __init__(self, names, order, active):
        QDialog.__init__(self)

        # Variables
        self.names = names
        self.order = order
        self.active = active

        # Widgets
        self.button_move_up = QPushButton(_('Move Up'))
        self.button_move_down = QPushButton(_('Move Down'))
        self.button_delete = QPushButton(_('Delete Layout'))
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok |
                                           QDialogButtonBox.Cancel,
                                           Qt.Horizontal, self)
        self.group_box = QGroupBox(_("Layout Dispay and Order"))
        self.table = QTableView(self)
        self.ok_button = self.button_box.button(QDialogButtonBox.Ok)
        self.cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        self.cancel_button.setDefault(True)
        self.cancel_button.setAutoDefault(True)

        # Layouts
        self.dialog_size = QSize(300, 200)
        self.setWindowTitle('Layout Settings')
        self.table.setModel(LayoutModel(self.table, order, active))
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().hide()
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnHidden(1, True)

        buttons_layout = QVBoxLayout()
        buttons_layout.addWidget(self.button_move_up)
        buttons_layout.addWidget(self.button_move_down)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.button_delete)

        group_layout = QHBoxLayout()
        group_layout.addWidget(self.table)
        group_layout.addLayout(buttons_layout)
        self.group_box.setLayout(group_layout)

        layout = QVBoxLayout()
        layout.addWidget(self.group_box)
        layout.addWidget(self.button_box)

        self.setLayout(layout)
        self.setMinimumSize(self.dialog_size)
        self.setFixedSize(self.dialog_size)

        # Signlas and slots
        self.connect(self.button_box, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(self.button_box, SIGNAL("rejected()"), self.close)
        self.connect(self.button_delete, SIGNAL("clicked()"),
                     self.delete_layout)
        self.connect(self.button_move_up, SIGNAL("clicked()"),
                     lambda: self.move_layout(True))
        self.connect(self.button_move_down, SIGNAL("clicked()"),
                     lambda: self.move_layout(False))
        self.connect(self.table.selectionModel(),
                     SIGNAL("selectionChanged(QItemSelection,QItemSelection)"),
                     lambda: self.selection_changed(None, None))
        self.connect(self.table.model(),
                     SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                     lambda: self.selection_changed(None, None))

        # Focus table
        index = self.table.model().index(0, 0)
        self.table.setCurrentIndex(index)
        self.table.setFocus()

    def delete_layout(self):
        """ """
        names, order, active = self.names, self.order, self.order
        index = self.table.selectionModel().currentIndex().row()

        # In case nothing has focus in the table
        if index != -1:
            name = order.pop(index)
            names.remove(name)
            if name in active:
                active.remove(name)
            self.names, self.order, self.active = names, order, active
            self.table.model().set_data(order, active)
            index = self.table.model().index(0, 0)
            self.table.setCurrentIndex(index)
            self.table.setFocus()
            self.selection_changed(None, None)
            if len(names) == 0:
                self.button_move_up.setDisabled(True)
                self.button_move_down.setDisabled(True)
                self.button_delete.setDisabled(True)

    def move_layout(self, up=True):
        """ """
        names, order, active = self.names, self.order, self.active
        row = self.table.selectionModel().currentIndex().row()
        row_new = row

        if up:
            row_new -= 1
        else:
            row_new += 1

        order[row], order[row_new] = order[row_new], order[row]

        self.order = order
        self.table.model().set_data(order, active)
        index = self.table.model().index(row_new, 0)
        self.table.setCurrentIndex(index)
        self.table.setFocus()
        self.selection_changed(None, None)

    def selection_changed(self, selection, deselection):
        """ """
        model = self.table.model()
        index = self.table.currentIndex()
        row = index.row()
        names = self.names
        active = self.active

        state = model.row(row)[1]
        name = model.row(row)[0]

        if state:
            if name not in active:
                active.append(name)
        else:
            if name in active:
                active.remove(name)

        self.active = active
        self.button_move_up.setDisabled(False)
        self.button_move_down.setDisabled(False)

        if row == 0:
            self.button_move_up.setDisabled(True)
        if row == len(names) - 1:
            self.button_move_down.setDisabled(True)
        if len(names) == 0:
            self.button_move_up.setDisabled(True)
            self.button_move_down.setDisabled(True)
#        print(names, active, self.order)


def test(type_=True):
    """Run layout test widget test"""
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    names = ['test', 'tester', '20', '30', '40']
    order = ['test', 'tester', '20', '30', '40']
    active = ['test', 'tester']

    if type_:
        widget = LayoutSettingsDialog(names, order, active)
    else:
        widget = LayoutSaveDialog(order)
    widget.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    test(True)
#    test(False)
