# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Run configuration page."""

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QButtonGroup, QGroupBox, QHBoxLayout, QLabel,
                            QVBoxLayout, QComboBox, QTableView,
                            QAbstractItemView, QPushButton, QGridLayout,
                            QHeaderView)

# Local imports
from spyder.plugins.run.container import RunContainer
from spyder.plugins.run.models import (
    RunExecutorNamesListModel, ExecutorRunParametersTableModel)
from spyder.api.preferences import PluginConfigPage
from spyder.api.translations import get_translation
from spyder.utils.misc import getcwd_or_home

# Localization
_ = get_translation("spyder")


class RunParametersTableView(QTableView):
    def __init__(self, parent, model):
        super().__init__(parent)
        self._parent = parent
        self.setModel(model)
        # self.setItemDelegateForColumn(CMD, ItemDelegate(self))
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.selectionModel().selectionChanged.connect(self.selection)
        self.verticalHeader().hide()
        self.reset_plain()

        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

    def focusOutEvent(self, e):
        """Qt Override."""
        # self.source_model.update_active_row()
        self._parent.delete_configuration_btn.setEnabled(False)
        super().focusOutEvent(e)

    def focusInEvent(self, e):
        """Qt Override."""
        super().focusInEvent(e)
        self.selectRow(self.currentIndex().row())
        self.selection(self.currentIndex().row())

    def selection(self, index):
        self.update()
        self.isActiveWindow()
        self._parent.delete_configuration_btn.setEnabled(True)

    def adjust_cells(self):
        """Adjust column size based on contents."""
        self.resizeColumnsToContents()
        model: ExecutorRunParametersTableModel = self.model()
        fm = self.horizontalHeader().fontMetrics()
        names = [fm.width(model.get_parameters_name(idx)) for idx in model]
        if names:
            self.setColumnWidth(
                ExecutorRunParametersTableModel.NAME, max(names))
        self.horizontalHeader().setStretchLastSection(True)

    def reset_plain(self):
        self.model().reset_model()
        self.adjust_cells()
        # self.sortByColumn(self.source_model.TRIGGER, Qt.AscendingOrder)
        self.selectionModel().selectionChanged.connect(self.selection)


class RunConfigPage(PluginConfigPage):
    """Default Run Settings configuration page."""

    def setup_page(self):
        self.plugin_container: RunContainer = self.plugin.get_container()
        self.executor_model = RunExecutorNamesListModel(
            self, self.plugin_container.executor_model)
        self.table_model = ExecutorRunParametersTableModel(self)

        about_label = QLabel(_("The following are the per-executor "
                               "configuration settings used for "
                               "running. These options may be overriden "
                               "using the <b>Configuration per file</b> entry "
                               "of the <b>Run</b> menu."))
        about_label.setWordWrap(True)

        self.executor_combo = QComboBox(self)
        self.executor_combo.currentIndexChanged.connect(
            self.executor_index_changed)
        self.executor_combo.setModel(self.executor_model)

        executor_group = QGroupBox(_('Run executors'))
        executor_layout = QVBoxLayout()
        executor_layout.addWidget(self.executor_combo)
        executor_group.setLayout(executor_layout)

        self.params_table = RunParametersTableView(self, self.table_model)
        self.params_table.setMaximumHeight(180)

        params_group = QGroupBox(_('Available execution parameters'))
        params_layout = QVBoxLayout(params_group)
        params_layout.addWidget(self.params_table)

        self.new_configuration_btn = QPushButton(
            _("Create new parameters"))
        self.delete_configuration_btn = QPushButton(
            _("Delete currently selected parameters"))
        self.delete_configuration_btn.setEnabled(False)

        # Buttons layout
        btns = [self.new_configuration_btn,
                self.delete_configuration_btn]
        sn_buttons_layout = QGridLayout()
        for i, btn in enumerate(btns):
            sn_buttons_layout.addWidget(btn, i, 1)
        sn_buttons_layout.setColumnStretch(0, 1)
        sn_buttons_layout.setColumnStretch(1, 2)
        sn_buttons_layout.setColumnStretch(2, 1)

        vlayout = QVBoxLayout(self)
        vlayout.addWidget(about_label)
        vlayout.addSpacing(10)
        vlayout.addWidget(executor_group)
        vlayout.addWidget(params_group)
        vlayout.addLayout(sn_buttons_layout)
        vlayout.addStretch(1)

    def executor_index_changed(self, index: int):
        executor, available_inputs = self.executor_model.selected_executor(
            index)

        executor_conf_params = {}
        for (ext, context) in available_inputs:
            params = (
                self.plugin_container.get_executor_configuration_parameters(
                    executor, ext, context))
            params = params["params"]
            for exec_params_id in params:
                exec_params = params[exec_params_id]
                executor_conf_params[
                    (ext, context, exec_params_id)] = exec_params

        self.table_model.set_parameters(executor_conf_params)

    def apply_settings(self):
        pass
