# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Layout dialogs"""

# Standard library imports
import sys

# Third party imports
from qtpy.QtCore import QAbstractTableModel, QModelIndex, QSize, Qt
from qtpy.compat import from_qvariant, to_qvariant
from qtpy.QtWidgets import (QAbstractItemView, QComboBox, QDialog,
                            QDialogButtonBox, QGroupBox, QHBoxLayout,
                            QPushButton, QTableView, QVBoxLayout)

# Local imports
from spyder.config.base import _
from spyder.py3compat import to_text_string


class LayoutModel(QAbstractTableModel):
    """ """
    def __init__(self, parent, names, ui_names, order, active, read_only):
        super(LayoutModel, self).__init__(parent)

        # variables
        self._parent = parent
        self.names = names
        self.ui_names = ui_names
        self.order = order
        self.active = active
        self.read_only = read_only
        self._rows = []
        self.set_data(names, ui_names, order, active, read_only)

    def set_data(self, names, ui_names, order, active, read_only):
        """ """
        self._rows = []
        self.names = names
        self.ui_names = ui_names
        self.order = order
        self.active = active
        self.read_only = read_only
        for name in order:
            index = names.index(name)
            if name in active:
                row = [ui_names[index], name, True]
            else:
                row = [ui_names[index], name, False]
            self._rows.append(row)

    def flags(self, index):
        """Override Qt method"""
        row = index.row()
        ui_name, name, state = self.row(row)

        if name in self.read_only:
            return Qt.NoItemFlags
        if not index.isValid():
            return Qt.ItemIsEnabled
        column = index.column()
        if column in [0]:
            return Qt.ItemFlags(int(Qt.ItemIsEnabled | Qt.ItemIsSelectable |
                                    Qt.ItemIsUserCheckable |
                                    Qt.ItemIsEditable))
        else:
            return Qt.ItemFlags(Qt.ItemIsEnabled)

    def data(self, index, role=Qt.DisplayRole):
        """Override Qt method"""
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return to_qvariant()
        row = index.row()
        column = index.column()

        ui_name, name, state = self.row(row)

        if role == Qt.DisplayRole or role == Qt.EditRole:
            if column == 0:
                return to_qvariant(ui_name)
        elif role == Qt.UserRole:
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
        """Override Qt method"""
        row = index.row()
        ui_name, name, state = self.row(row)

        if role == Qt.CheckStateRole:
            self.set_row(row, [ui_name, name, not state])
            self._parent.setCurrentIndex(index)
            self._parent.setFocus()
            self.dataChanged.emit(index, index)
            return True
        elif role == Qt.EditRole:
            self.set_row(
                row, [from_qvariant(value, to_text_string), name, state])
            self.dataChanged.emit(index, index)
            return True
        return True

    def rowCount(self, index=QModelIndex()):
        """Override Qt method"""
        return len(self._rows)

    def columnCount(self, index=QModelIndex()):
        """Override Qt method"""
        return 2

    def row(self, rownum):
        """ """
        if self._rows == [] or rownum >= len(self._rows):
            return [None, None, None]
        else:
            return self._rows[rownum]

    def set_row(self, rownum, value):
        """ """
        self._rows[rownum] = value


class LayoutSaveDialog(QDialog):
    """ """
    def __init__(self, parent, order):
        super(LayoutSaveDialog, self).__init__(parent)

        # variables
        self._parent = parent

        # widgets
        self.combo_box = QComboBox(self)
        self.combo_box.addItems(order)
        self.combo_box.setEditable(True)
        self.combo_box.clearEditText()
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok |
                                           QDialogButtonBox.Cancel,
                                           Qt.Horizontal, self)
        self.button_ok = self.button_box.button(QDialogButtonBox.Ok)
        self.button_cancel = self.button_box.button(QDialogButtonBox.Cancel)

        # widget setup
        self.button_ok.setEnabled(False)
        self.dialog_size = QSize(300, 100)
        self.setWindowTitle('Save layout as')
        self.setModal(True)
        self.setMinimumSize(self.dialog_size)
        self.setFixedSize(self.dialog_size)

        # layouts
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.combo_box)
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)

        # signals and slots
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.close)
        self.combo_box.editTextChanged.connect(self.check_text)

    def check_text(self, text):
        """Disable empty layout name possibility"""
        if to_text_string(text) == u'':
            self.button_ok.setEnabled(False)
        else:
            self.button_ok.setEnabled(True)


class LayoutSettingsDialog(QDialog):
    """Layout settings dialog"""
    def __init__(self, parent, names, ui_names, order, active, read_only):
        super(LayoutSettingsDialog, self).__init__(parent)
        # variables
        self._parent = parent
        self._selection_model = None
        self.names = names
        self.ui_names = ui_names
        self.order = order
        self.active = active
        self.read_only = read_only

        # widgets
        self.button_move_up = QPushButton(_('Move Up'))
        self.button_move_down = QPushButton(_('Move Down'))
        self.button_delete = QPushButton(_('Delete Layout'))
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok |
                                           QDialogButtonBox.Cancel,
                                           Qt.Horizontal, self)
        self.group_box = QGroupBox(_("Layout Display and Order"))
        self.table = QTableView(self)
        self.ok_button = self.button_box.button(QDialogButtonBox.Ok)
        self.cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        self.cancel_button.setDefault(True)
        self.cancel_button.setAutoDefault(True)

        # widget setup
        self.dialog_size = QSize(300, 200)
        self.setMinimumSize(self.dialog_size)
        self.setFixedSize(self.dialog_size)
        self.setWindowTitle('Layout Settings')

        self.table.setModel(
            LayoutModel(self.table, names, ui_names, order, active, read_only))
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().hide()
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnHidden(1, True)

        # need to keep a reference for pyside not to segfault!
        self._selection_model = self.table.selectionModel()

        # layout
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

        # signals and slots
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.close)
        self.button_delete.clicked.connect(self.delete_layout)
        self.button_move_up.clicked.connect(lambda: self.move_layout(True))
        self.button_move_down.clicked.connect(lambda: self.move_layout(False))
        self.table.model().dataChanged.connect(
           lambda: self.selection_changed(None, None))
        self._selection_model.selectionChanged.connect(
           lambda: self.selection_changed(None, None))

        # focus table
        if len(names) > len(read_only):
            row = len(read_only)
            index = self.table.model().index(row, 0)
            self.table.setCurrentIndex(index)
            self.table.setFocus()
        else:
            # initial button state in case only programmatic layouts
            # are available
            self.button_move_up.setDisabled(True)
            self.button_move_down.setDisabled(True)
            self.button_delete.setDisabled(True)

    def delete_layout(self):
        """Delete layout from the config."""
        names, ui_names, order, active, read_only = (
            self.names, self.ui_names, self.order, self.active, self.read_only)
        row = self.table.selectionModel().currentIndex().row()
        ui_name, name, state = self.table.model().row(row)

        if name not in read_only:
            name = from_qvariant(
                self.table.selectionModel().currentIndex().data(),
                to_text_string)
            if ui_name in ui_names:
                index = ui_names.index(ui_name)
            else:
                # In case nothing has focus in the table
                return
            if index != -1:
                order.remove(ui_name)
                names.remove(ui_name)
                ui_names.remove(ui_name)
                if name in active:
                    active.remove(ui_name)
                self.names, self.ui_names, self.order, self.active = (
                    names, ui_names, order, active)
                self.table.model().set_data(
                    names, ui_names, order, active, read_only)
                index = self.table.model().index(0, 0)
                self.table.setCurrentIndex(index)
                self.table.setFocus()
                self.selection_changed(None, None)
                if len(order) == 0 or len(names) == len(read_only):
                    self.button_move_up.setDisabled(True)
                    self.button_move_down.setDisabled(True)
                    self.button_delete.setDisabled(True)

    def move_layout(self, up=True):
        """ """
        names, ui_names, order, active, read_only = (
            self.names, self.ui_names, self.order, self.active, self.read_only)
        row = self.table.selectionModel().currentIndex().row()
        row_new = row
        _ui_name, name, _state = self.table.model().row(row)

        if name not in read_only:
            if up:
                row_new -= 1
            else:
                row_new += 1

            if order[row_new] not in read_only:
                order[row], order[row_new] = order[row_new], order[row]

                self.order = order
                self.table.model().set_data(
                    names, ui_names, order, active, read_only)
                index = self.table.model().index(row_new, 0)
                self.table.setCurrentIndex(index)
                self.table.setFocus()
                self.selection_changed(None, None)

    def selection_changed(self, selection, deselection):
        """ """
        model = self.table.model()
        index = self.table.currentIndex()
        row = index.row()
        order, names, ui_names, active, read_only = (
            self.order, self.names, self.ui_names, self.active, self.read_only)

        state = model.row(row)[2]
        ui_name = model.row(row)[0]

        # Check if name changed
        if ui_name not in ui_names:  # Did changed
            # row == -1, means no items left to delete
            if row != -1 and len(names) > len(read_only):
                old_name = order[row]
                order[row] = ui_name
                names[names.index(old_name)] = ui_name
                ui_names = names
                if old_name in active:
                    active[active.index(old_name)] = ui_name

        # Check if checkbox clicked
        if state:
            if ui_name not in active:
                active.append(ui_name)
        else:
            if ui_name in active:
                active.remove(ui_name)

        self.active = active
        self.order = order
        self.names = names
        self.ui_names = ui_names
        self.button_move_up.setDisabled(False)
        self.button_move_down.setDisabled(False)

        if row == 0:
            self.button_move_up.setDisabled(True)
        if row == len(names) - 1:
            self.button_move_down.setDisabled(True)
        if len(names) == 0:
            self.button_move_up.setDisabled(True)
            self.button_move_down.setDisabled(True)


def test():
    """Run layout test widget test"""
    from spyder.utils.qthelpers import qapplication

    app = qapplication()
    names = ['test', 'tester', '20', '30', '40']
    ui_names = ['L1', 'L2', '20', '30', '40']
    order = ['test', 'tester', '20', '30', '40']
    read_only = ['test', 'tester']
    active = ['test', 'tester']
    widget_1 = LayoutSettingsDialog(
        None, names, ui_names, order, active, read_only)
    widget_2 = LayoutSaveDialog(None, order)
    widget_1.show()
    widget_2.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    test()
