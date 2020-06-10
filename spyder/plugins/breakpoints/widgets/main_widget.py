# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# based loosley on pylintgui.py by Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Breakpoint widget.
"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import sys

# Third party imports
from qtpy import API
from qtpy.compat import to_qvariant
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from qtpy.QtWidgets import QItemDelegate, QTableView, QVBoxLayout

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets import (PluginMainWidgetMenus, PluginMainWidget,
                                SpyderWidgetMixin)
from spyder.utils.sourcecode import disambiguate_fname


# Localization
_ = get_translation('spyder')


# --- Constants
# ----------------------------------------------------------------------------
COLUMN_COUNT = 4
EXTRA_COLUMNS = 1
COL_FILE, COL_LINE, COL_CONDITION, COL_BLANK, COL_FULL = list(
    range(COLUMN_COUNT + EXTRA_COLUMNS))
COLUMN_HEADERS = (_("File"), _("Line"), _("Condition"), (""))


class BreakpointTableViewActions:
    # Triggers
    ClearAllBreakpoints = 'clear_all_breakpoints_action'
    ClearBreakpoint = 'clear_breakpoint_action'
    EditBreakpoint = 'edit_breakpoint_action'


# --- Widgets
# ----------------------------------------------------------------------------
class BreakpointTableModel(QAbstractTableModel):
    """
    Table model for breakpoints dictionary.
    """

    def __init__(self, parent, data):
        super().__init__(parent)

        self._data = {} if data is None else data
        self.breakpoints = None

        self.set_data(self._data)

    def set_data(self, data):
        """
        Set model data.

        Parameters
        ----------
        data: dict
            Breakpoint data to use.
        """
        self._data = data
        self.breakpoints = []
        files = []
        # Generate list of filenames with active breakpoints
        for key in data:
            if data[key] and key not in files:
                files.append(key)

        # Insert items
        for key in files:
            for item in data[key]:
                # Store full file name in last position, which is not shown
                self.breakpoints.append((disambiguate_fname(files, key),
                                         item[0], item[1], "", key))
        self.reset()

    def rowCount(self, qindex=QModelIndex()):
        """
        Array row number.
        """
        return len(self.breakpoints)

    def columnCount(self, qindex=QModelIndex()):
        """
        Array column count.
        """
        return COLUMN_COUNT

    def sort(self, column, order=Qt.DescendingOrder):
        """
        Overriding sort method.
        """
        if column == COL_FILE:
            self.breakpoints.sort(key=lambda breakp: int(breakp[COL_LINE]))
            self.breakpoints.sort(key=lambda breakp: breakp[COL_FILE])
        elif column == COL_LINE:
            pass
        elif column == COL_CONDITION:
            pass
        elif column == COL_BLANK:
            pass

        self.reset()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """
        Overriding method headerData.
        """
        if role != Qt.DisplayRole:
            return to_qvariant()

        i_column = int(section)
        if orientation == Qt.Horizontal:
            return to_qvariant(COLUMN_HEADERS[i_column])
        else:
            return to_qvariant()

    def get_value(self, index):
        """
        Return current value.
        """
        return self.breakpoints[index.row()][index.column()]

    def data(self, index, role=Qt.DisplayRole):
        """
        Return data at table index.
        """
        if not index.isValid():
            return to_qvariant()

        if role == Qt.DisplayRole:
            value = self.get_value(index)
            return to_qvariant(value)
        elif role == Qt.TextAlignmentRole:
            if index.column() == COL_LINE:
                # Align line number right
                return to_qvariant(int(Qt.AlignRight | Qt.AlignVCenter))
            else:
                return to_qvariant(int(Qt.AlignLeft | Qt.AlignVCenter))
        elif role == Qt.ToolTipRole:
            if index.column() == COL_FILE:
                # Return full file name (in last position)
                value = self.breakpoints[index.row()][COL_FULL]
                return to_qvariant(value)
            else:
                return to_qvariant()

    def reset(self):
        self.beginResetModel()
        self.endResetModel()


class BreakpointDelegate(QItemDelegate):

    def __init__(self, parent=None):
        super().__init__(parent)


class BreakpointTableView(QTableView, SpyderWidgetMixin):
    """
    Table to display code breakpoints.
    """

    # Signals
    sig_clear_all_breakpoints_requested = Signal()
    sig_clear_breakpoint_requested = Signal(str, int)
    sig_edit_goto_requested = Signal(str, int, str)
    sig_conditional_breakpoint_requested = Signal()

    def __init__(self, parent, data):
        super().__init__(parent)

        # Widgets
        self.model = BreakpointTableModel(self, data)
        self.delegate = BreakpointDelegate(self)

        # Setup
        self.setSortingEnabled(False)
        self.setSelectionBehavior(self.SelectRows)
        self.setSelectionMode(self.SingleSelection)
        self.setModel(self.model)
        self.setItemDelegate(self.delegate)
        self.adjust_columns()
        self.columnAt(0)
        self.horizontalHeader().setStretchLastSection(True)

    # --- SpyderWidgetMixin API
    # ------------------------------------------------------------------------
    def setup(self, options={}):
        clear_all_action = self.create_action(
            BreakpointTableViewActions.ClearAllBreakpoints,
            _("Clear breakpoints in all files"),
            triggered=self.sig_clear_all_breakpoints_requested,
        )
        clear_action = self.create_action(
            BreakpointTableViewActions.ClearBreakpoint,
            _("Clear selected breakpoint"),
            triggered=self.clear_breakpoints,
        )
        edit_action = self.create_action(
            BreakpointTableViewActions.EditBreakpoint,
            _("Edit selected breakpoint"),
            triggered=self.edit_breakpoints,
        )

        self.popup_menu = self.create_menu(PluginMainWidgetMenus.Context)
        for item in [clear_all_action, clear_action, edit_action]:
            self.add_item_to_menu(item, menu=self.popup_menu)

    # --- Qt overrides
    # ------------------------------------------------------------------------
    def contextMenuEvent(self, event):
        """
        Override Qt method.
        """
        c_row = self.indexAt(event.pos()).row()
        enabled = bool(self.model.breakpoints) and c_row is not None
        clear_action = self.get_action(
            BreakpointTableViewActions.ClearBreakpoint)
        edit_action = self.get_action(
            BreakpointTableViewActions.EditBreakpoint)
        clear_action.setEnabled(enabled)
        edit_action.setEnabled(enabled)

        self.popup_menu.popup(event.globalPos())
        event.accept()

    def mouseDoubleClickEvent(self, event):
        """
        Override Qt method.
        """
        index_clicked = self.indexAt(event.pos())
        if self.model.breakpoints:
            c_row = index_clicked.row()
            filename = self.model.breakpoints[c_row][COL_FULL]
            line_number_str = self.model.breakpoints[c_row][COL_LINE]

            self.sig_edit_goto_requested.emit(
                filename, int(line_number_str), '')

        if index_clicked.column() == COL_CONDITION:
            self.sig_conditional_breakpoint_requested.emit()

    # --- API
    # ------------------------------------------------------------------------
    def set_data(self, data):
        """
        Set the model breakpoint data dictionary.

        Parameters
        ----------
        data: dict
            Breakpoint data to use.
        """
        self.model.set_data(data)
        self.adjust_columns()
        self.sortByColumn(COL_FILE, Qt.DescendingOrder)

    def adjust_columns(self):
        """
        Resize three first columns to contents.
        """
        for col in range(COLUMN_COUNT - 1):
            self.resizeColumnToContents(col)

    def clear_breakpoints(self):
        """
        Clear selected row breakpoint.
        """
        rows = self.selectionModel().selectedRows()
        if rows and self.model.breakpoints:
            c_row = rows[0].row()
            filename = self.model.breakpoints[c_row][COL_FULL]
            lineno = int(self.model.breakpoints[c_row][COL_LINE])

            self.sig_clear_breakpoint_requested.emit(filename, lineno)

    def edit_breakpoints(self):
        """
        Edit selected row breakpoint condition.
        """
        rows = self.selectionModel().selectedRows()
        if rows and self.model.breakpoints:
            c_row = rows[0].row()
            filename = self.model.breakpoints[c_row][COL_FULL]
            lineno = int(self.model.breakpoints[c_row][COL_LINE])

            self.sig_edit_goto_requested.emit(filename, lineno, '')
            self.sig_conditional_breakpoint_requested.emit()


class BreakpointWidget(PluginMainWidget):
    """
    Breakpoints widget.
    """

    DEFAULT_OPTIONS = {}

    # --- Signals
    # ------------------------------------------------------------------------
    sig_clear_all_breakpoints_requested = Signal()
    """
    This signal is emitted to send a request to clear all assigned
    breakpoints.
    """

    sig_clear_breakpoint_requested = Signal(str, int)
    """
    This signal is emitted to send a request to clear a single breakpoint.

    Parameters
    ----------
    filename: str
        The path to filename cotaining the breakpoint.
    line_number: int
        The line number of the breakpoint.
    """

    sig_edit_goto_requested = Signal(str, int, str)
    """
    Send a request to open a file in the editor at a given row and word.

    Parameters
    ----------
    filename: str
        The path to the filename containing the breakpoint.
    line_number: int
        The line number of the breakpoint.
    word: str
        Text `word` to select on given `line_number`.
    """

    sig_conditional_breakpoint_requested = Signal()
    """
    Send a request to set/edit a condition on a single selected breakpoint.
    """

    def __init__(self, name=None, plugin=None, parent=None,
                 options=DEFAULT_OPTIONS):
        super().__init__(name, plugin, parent=parent, options=options)

        # Widgets
        self.breakpoints_table = BreakpointTableView(self, {})

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.breakpoints_table)
        self.setLayout(layout)

        # Signals
        bpt = self.breakpoints_table
        bpt.sig_clear_all_breakpoints_requested.connect(
            self.sig_clear_all_breakpoints_requested)
        bpt.sig_clear_breakpoint_requested.connect(
            self.sig_clear_breakpoint_requested)
        bpt.sig_edit_goto_requested.connect(self.sig_edit_goto_requested)
        bpt.sig_conditional_breakpoint_requested.connect(
            self.sig_conditional_breakpoint_requested)

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('Breakpoints')

    def get_focus_widget(self):
        return self.breakpoints_table

    def setup(self, options):
        self.breakpoints_table.setup()

        clear_all_action = self.get_action(
            BreakpointTableViewActions.ClearAllBreakpoints)
        clear_action = self.get_action(
            BreakpointTableViewActions.ClearBreakpoint)
        edit_action = self.get_action(
            BreakpointTableViewActions.EditBreakpoint)

        options_menu = self.get_options_menu()
        for item in [clear_all_action, clear_action, edit_action]:
            self.add_item_to_menu(item, menu=options_menu)

    def on_option_update(self, option, value):
        pass

    def update_actions(self):
        rows = self.breakpoints_table.selectionModel().selectedRows()
        c_row = rows[0] if rows else None

        enabled = (bool(self.breakpoints_table.model.breakpoints)
                   and c_row is not None)
        clear_action = self.get_action(
            BreakpointTableViewActions.ClearBreakpoint)
        edit_action = self.get_action(
            BreakpointTableViewActions.EditBreakpoint)
        clear_action.setEnabled(enabled)
        edit_action.setEnabled(enabled)

    # --- Public API
    # ------------------------------------------------------------------------
    def set_data(self, data):
        """
        Set breakpoint data on widget.

        Parameters
        ----------
        data: dict
            Breakpoint data to use.
        """
        self.breakpoints_table.set_data(data)


# =============================================================================
# Tests
# =============================================================================
def test():
    """Run breakpoint widget test."""
    from spyder.utils.qthelpers import qapplication

    app = qapplication()
    widget = BreakpointWidget()
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
