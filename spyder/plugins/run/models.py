# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder run models."""

# Standard library imports
from collections import OrderedDict
from typing import Dict, Tuple, Optional, Set, Union, List

# Third-party imports
from qtpy.QtCore import (Qt, Signal, QAbstractListModel, QModelIndex,
                         QAbstractTableModel)

# Local imports
from spyder.api.translations import _
from spyder.plugins.run.api import (
    ExtendedRunExecutionParameters,
    RunConfigurationMetadata,
    RunContext,
    StoredRunConfigurationExecutor,
    StoredRunExecutorParameters,
    SupportedExecutionRunConfiguration,
)


class RunExecutorListModel(QAbstractListModel):
    sig_executor_widget_changed = Signal(object)

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.uuid: Optional[str] = None
        self.current_input: Optional[Tuple[str, str]] = None
        self.executor_names: Dict[str, str] = {}
        self.executor_configurations: Dict[Tuple[str, str], Dict[
            str, SupportedExecutionRunConfiguration]] = {}
        self.executors_per_input: Dict[Tuple[str, str], Dict[str, int]] = {}
        self.inverted_pos: Dict[Tuple[str, str], Dict[int, str]] = {}
        self.executor_priority: Dict[Tuple[str, str], Dict[str, int]] = {}

    def set_executor_name(self, executor_id: str, executor_name: str):
        self.executor_names[executor_id] = executor_name

    def add_input_executor_configuration(
        self,
        ext: str,
        context_id: str,
        executor_id: str,
        config: SupportedExecutionRunConfiguration
    ):
        executor_conf = self.executor_configurations.get((ext, context_id), {})
        executor_conf[executor_id] = config
        self.executor_configurations[(ext, context_id)] = executor_conf

        input_executors = self.executors_per_input.get((ext, context_id), {})
        all_exec_prio = self.executor_priority.get((ext, context_id), {})
        priority = config['priority']

        # Remove if existing
        input_executors.pop(executor_id, None)
        all_exec_prio.pop(executor_id, None)
        all_exec_prio[executor_id] = priority

        input_values = list(all_exec_prio.items())
        input_values = sorted(input_values, key=lambda k: k[1])

        input_values = [(x, i) for i, (x, _) in enumerate(input_values)]
        self.executors_per_input[(ext, context_id)] = dict(input_values)

        self.inverted_pos[(ext, context_id)] = {
            v: k for (k, v) in input_values}
        self.executor_priority[(ext, context_id)] = all_exec_prio

    def remove_input_executor_configuration(
        self,
        ext: str,
        context_id: str,
        executor_id: str
    ):
        input_executors = self.executors_per_input[(ext, context_id)]
        pos = input_executors.pop(executor_id)

        inverted_executors = self.inverted_pos[(ext, context_id)]
        inverted_executors.pop(pos)

    def switch_input(self, uuid: str, run_input: Tuple[str, str]):
        if run_input in self.executors_per_input:
            self.beginResetModel()
            self.current_input = run_input
            self.uuid = uuid
            self.endResetModel()
        else:
            raise ValueError(
                f'The requested run input combination {run_input} is not '
                f'registered'
            )

    def get_selected_run_executor(
        self,
        index: int
    ) -> Tuple[str, SupportedExecutionRunConfiguration]:

        executor_indices = self.inverted_pos[self.current_input]
        executor_name = executor_indices[index]
        executors = self.executor_configurations[self.current_input]
        executor = executors[executor_name]

        return executor_name, executor

    def get_run_executor_index(self, executor_name: str) -> int:
        ordered_executors = self.executors_per_input[self.current_input]
        executor_index = ordered_executors[executor_name]
        return executor_index

    def get_initial_index(self) -> int:
        last_executor = self.parent.get_last_used_executor_parameters(
            self.uuid)
        executor_id = last_executor['executor']
        pos = 0

        if executor_id is not None:
            executors = self.executors_per_input[self.current_input]
            pos = executors[executor_id]

        return pos

    def get_default_executor(self, input: Tuple[str, str]) -> str:
        executors = self.inverted_pos[input]
        return executors[0]

    def executor_supports_configuration(
        self,
        executor: str,
        exec_input: Tuple[str, str]
    ) -> bool:

        input_executors = self.executor_configurations.get(exec_input, {})
        return executor in input_executors

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole or role == Qt.EditRole:
            executor_indices = self.inverted_pos[self.current_input]
            executor_id = executor_indices[index.row()]
            return self.executor_names[executor_id]

    def rowCount(self, parent: QModelIndex = None) -> int:
        executors = self.executors_per_input.get(self.current_input, {})
        return len(executors)

    def __contains__(self, exec_input: Tuple[str, str]) -> bool:
        return exec_input in self.executor_configurations

    def __len__(self):
        return len(self.executor_configurations)

    def __iter__(self):
        return iter(self.executor_configurations)

    def __getitem__(
            self, input_executor: tuple) -> SupportedExecutionRunConfiguration:
        (input, executor) = input_executor
        input_executors = self.executor_configurations[input]
        return input_executors[executor]


class RunConfigurationListModel(QAbstractListModel):
    def __init__(self, parent, executor_model):
        super().__init__(parent)
        self.parent = parent
        self.selected_metadata: Optional[RunConfigurationMetadata] = None
        self.current_configuration: Optional[str] = None
        self.metadata_index: Dict[int, str] = {}
        self.inverted_index: Dict[str, int] = {}
        self.run_configurations: OrderedDict[
            str, RunConfigurationMetadata] = OrderedDict()
        self.executor_model: RunExecutorListModel = executor_model

    def get_metadata_context_extension(self, uuid: str):
        run_conf = self.run_configurations[uuid]
        return run_conf['context'], run_conf['input_extension']

    def set_current_run_configuration(self, uuid: str):
        self.current_configuration = uuid
    
    def get_current_run_configuration(self):
        return self.current_configuration

    def get_initial_index(self) -> int:
        return self.inverted_index[self.current_configuration]

    def get_selected_metadata(self) -> Optional[RunConfigurationMetadata]:
        return self.selected_metadata

    def get_metadata(self, index: int) -> RunConfigurationMetadata:
        uuid = self.metadata_index[index]
        metadata = self.run_configurations[uuid]
        return metadata

    def update_index(self, index: int):
        uuid = self.metadata_index[index]
        metadata = self.run_configurations[uuid]
        context_name = metadata['context']['name']
        context_id = getattr(RunContext, context_name)
        ext = metadata['input_extension']
        self.selected_metadata = metadata
        self.executor_model.switch_input(uuid, (ext, context_id))

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole or role == Qt.EditRole:
            uuid = self.metadata_index[index.row()]
            metadata = self.run_configurations[uuid]
            return metadata['name']

    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self.run_configurations)

    def get_run_configuration_parameters(
        self,
        uuid: str,
        executor: str
    ) -> Optional[StoredRunExecutorParameters]:

        context, ext = self.get_metadata_context_extension(uuid)
        context_name = context['name']
        context_id = getattr(RunContext, context_name)

        return self.parent.get_executor_configuration_parameters(
            executor, ext, context_id)

    def get_last_used_execution_params(
        self,
        uuid: str,
        executor: str
    ) -> Optional[str]:

        return self.parent.get_last_used_execution_params(uuid, executor)

    def get_last_used_executor_parameters(
        self,
        uuid: str
    ) -> StoredRunConfigurationExecutor:

        return self.parent.get_last_used_executor_parameters(uuid)

    def pop(self, uuid: str) -> RunConfigurationMetadata:
        item = self.run_configurations.pop(uuid)
        self.metadata_index = dict(enumerate(self.run_configurations))
        self.inverted_index = {v: k for k, v in self.metadata_index.items()}
        if self.current_configuration not in self.inverted_index:
            self.current_configuration = None
        self.dataChanged.emit(self.createIndex(0, 0),
                              self.createIndex(len(self.metadata_index), 0))
        return item

    def __iter__(self):
        return iter(self.run_configurations)

    def __len__(self):
        return len(self.run_configurations)

    def __getitem__(self, uuid: str) -> RunConfigurationMetadata:
        return self.run_configurations[uuid]

    def __setitem__(self, uuid: str, metadata: RunConfigurationMetadata):
        self.run_configurations[uuid] = metadata
        self.metadata_index[len(self.metadata_index)] = uuid
        self.inverted_index[uuid] = len(self.inverted_index)
        self.dataChanged.emit(self.createIndex(0, 0),
                              self.createIndex(len(self.metadata_index), 0))

    def __contains__(self, uuid: str):
        return uuid in self.run_configurations


class RunExecutorParameters(QAbstractListModel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.executor_conf_params: Dict[
            str, ExtendedRunExecutionParameters] = {}
        self.params_index: Dict[int, str] = {}
        self.inverse_index: Dict[str, int] = {}

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        pos = index.row()
        pos = 0 if pos == -1 else pos
        params_id = self.params_index[pos]
        params = self.executor_conf_params[params_id]
        params_name = params['name']
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return params_name

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self.executor_conf_params)

    def get_parameters(self, index: int) -> ExtendedRunExecutionParameters:
        params_id = self.params_index[index]
        return self.executor_conf_params[params_id]

    def get_parameters_uuid_name(
        self, index: int
    ) -> Tuple[Optional[str], Optional[str]]:

        params_id = self.params_index[index]
        params = self.executor_conf_params[params_id]
        return params['uuid'], params['name']

    def set_parameters(
        self,
        parameters: Dict[str, ExtendedRunExecutionParameters]
    ):
        self.beginResetModel()
        self.executor_conf_params = parameters
        self.params_index = dict(enumerate(self.executor_conf_params))
        self.inverse_index = {
            self.params_index[k]: k for k in self.params_index
        }
        self.endResetModel()

    def get_parameters_index_by_uuid(
        self, parameters_uuid: Optional[str]
    ) -> int:
        return self.inverse_index.get(parameters_uuid, 0)

    def get_parameters_index_by_name(self, parameters_name: str) -> int:
        index = -1
        for id_, idx in self.inverse_index.items():
            if self.executor_conf_params[id_]['name'] == parameters_name:
                index = idx
                break

        return index

    def get_parameter_names(self, filter_global: bool = False) -> List[str]:
        """
        Get all parameter names for this executor.

        Parameters
        ----------
        filter_global: bool, optional
            Whether to filter global parameters from the results.
        """
        names = []
        for params in self.executor_conf_params.values():
            if filter_global:
                if params["file_uuid"] is not None:
                    names.append(params["name"])
            else:
                names.append(params["name"])

        return names

    def get_number_of_custom_params(self, global_params_name: str) -> int:
        """
        Get the number of custom parameters derived from a set of global ones.

        Parameters
        ----------
        global_params_name: str
            Name of the global parameters.
        """
        names = self.get_parameter_names(filter_global=True)
        return len(
            [name for name in names if name.startswith(global_params_name)]
        )

    def __len__(self) -> int:
        return len(self.executor_conf_params)


class RunExecutorNamesListModel(QAbstractListModel):
    def __init__(self, parent, executor_model: RunExecutorListModel):
        super().__init__(parent)
        self.executor_model = executor_model
        self.executor_configurations: OrderedDict[
            str, Set[Tuple[str, str]]] = OrderedDict({})

        for input_conf in self.executor_model.executors_per_input:
            executors_available = self.executor_model.executors_per_input[
                input_conf]
            for executor in executors_available:
                exec_input_conf = self.executor_model[(input_conf, executor)]
                ConfigWidget = exec_input_conf.get(
                    'configuration_widget', None)
                if ConfigWidget is not None:
                    input_set = self.executor_configurations.get(
                        executor,set({}))
                    input_set |= {input_conf}
                    self.executor_configurations[executor] = input_set

        self.executor_indexed_list: Dict[int, str] = dict(
            enumerate(self.executor_configurations))

        self.executor_list: Dict[str, int] = {
            v: k for k, v in self.executor_indexed_list.items()}

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> str:
        row = index.row()
        if role == Qt.DisplayRole or role == Qt.EditRole:
            executor_id = self.executor_indexed_list[row]
            return self.executor_model.executor_names[executor_id]

    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self.executor_list)

    def selected_executor(
            self, index: int) -> Tuple[str, Set[Tuple[str, str]]]:
        executor_name = self.executor_indexed_list[index]
        return executor_name, self.executor_configurations[executor_name]


class ExecutorRunParametersTableModel(QAbstractTableModel):
    NAME = 0
    EXTENSION = 1
    CONTEXT = 2

    sig_data_changed = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.executor_conf_params: Dict[
            Tuple[str, str, str], ExtendedRunExecutionParameters
        ] = {}

        self.params_index: Dict[int, Tuple[str, str, str]] = {}
        self.inverse_index: Dict[Tuple[str, str, str], int] = {}

    def data(self, index: QModelIndex,
             role: int = Qt.DisplayRole) -> Union[str, int]:
        row = index.row()
        column = index.column()

        params_idx = self.params_index[row]
        (extension, context, __) = params_idx
        params = self.executor_conf_params[params_idx]

        if role == Qt.DisplayRole or role == Qt.EditRole:
            if column == self.EXTENSION:
                return extension
            elif column == self.CONTEXT:
                return context
            elif column == self.NAME:
                return _("Default") if params['default'] else params['name']
        elif role == Qt.TextAlignmentRole:
            return int(Qt.AlignHCenter | Qt.AlignVCenter)
        elif role == Qt.ToolTipRole:
            return _("Double-click to view or edit")

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.DisplayRole
    ) -> Union[str, int]:

        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return int(Qt.AlignHCenter | Qt.AlignVCenter)
            return int(Qt.AlignRight | Qt.AlignVCenter)

        if role == Qt.DisplayRole or role == Qt.EditRole:
            if orientation == Qt.Horizontal:
                if section == self.EXTENSION:
                    return _('File extension')
                elif section == self.CONTEXT:
                    return _('Context')
                elif section == self.NAME:
                    return _('Name')

    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self.params_index)

    def columnCount(self, parent: QModelIndex = None) -> int:
        return 3

    def set_parameters(
        self,
        params: Dict[Tuple[str, str, str], ExtendedRunExecutionParameters]
    ):
        self.beginResetModel()

        # Reorder params so that Python and IPython extensions are shown first
        # and second by default, respectively.
        ordered_params = []
        for k, v in params.items():
            if k[0] == "py":
                ordered_params.insert(0, (k, v))
            elif k[0] == "ipy":
                ordered_params.insert(1, (k, v))
            else:
                ordered_params.append((k, v))
        params = dict(ordered_params)

        # Update attributes
        self.executor_conf_params = params
        self.params_index = dict(enumerate(params))
        self.inverse_index = {v: k for k, v in self.params_index.items()}

        self.endResetModel()

    def get_current_view(
        self
    ) -> Dict[Tuple[str, str, str], ExtendedRunExecutionParameters]:

        return self.executor_conf_params

    def get_tuple_index(self, index: int) -> Tuple[str, str, str]:
        return self.params_index[index]

    def reset_model(self):
        self.beginResetModel()
        self.endResetModel()

    def get_parameters_name(self, idx: Tuple[str, str, str]) -> str:
        params = self.executor_conf_params[idx]
        return params['name']

    def sort(self, column: int, order: Qt.SortOrder = ...) -> None:
        self.beginResetModel()
        reverse = order == Qt.DescendingOrder

        if column == self.EXTENSION:
            sorted_keys = sorted(self.executor_conf_params,
                                 key=lambda x: x[0],
                                 reverse=reverse)
        elif column == self.CONTEXT:
            sorted_keys = sorted(self.executor_conf_params,
                                 key=lambda x: x[1],
                                 reverse=reverse)
        elif column == self.NAME:
            sorted_keys = sorted(
                self.executor_conf_params,
                key=lambda x: self.executor_conf_params[x]['name'],
                reverse=reverse)

        self.params_index = dict(enumerate(sorted_keys))
        self.inverse_index = {v: k for k, v in self.params_index.items()}
        self.endResetModel()

    def apply_changes(
        self,
        changes: List[Tuple[str, ExtendedRunExecutionParameters]],
        extension: str,
        context: str
    ):
        self.beginResetModel()

        for (operation, params) in changes:
            key = (extension, context, params['uuid'])
            if operation == 'deleted':
                self.executor_conf_params.pop(key)
            else:
                self.executor_conf_params[key] = params

        self.params_index = dict(enumerate(self.executor_conf_params))
        self.inverse_index = {v: k for k, v in self.params_index.items()}

        self.endResetModel()

        self.sig_data_changed.emit()

    def get_parameter_names(self) -> Dict[Tuple[str, str], List[str]]:
        """Get all parameter names per extension and context."""
        names = {}
        for k, v in self.executor_conf_params.items():
            extension_context = (k[0], k[1])
            current_names = names.get(extension_context, [])
            current_names.append(_("Default") if v["default"] else v["name"])
            names[extension_context] = current_names

        return names

    def __len__(self):
        return len(self.inverse_index)

    def __iter__(self):
        return iter(self.executor_conf_params)

    def __getitem__(
        self,
        index: int
    ) -> Tuple[str, str, ExtendedRunExecutionParameters]:

        tuple_index = self.params_index[index]
        (ext, context, __) = tuple_index
        return (ext, context, self.executor_conf_params[tuple_index])
