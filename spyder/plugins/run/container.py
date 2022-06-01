# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder run container."""

# Standard library imports
import os.path as osp
from collections import OrderedDict
from weakref import WeakSet, WeakValueDictionary
from typing import List, Dict, Tuple, Set, Optional

# Third-party imports
from qtpy.QtCore import Qt, Signal, QAbstractListModel, QModelIndex
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.utils.sourcecode import camel_case_to_snake_case
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.api.translations import get_translation
from spyder.plugins.run.widgets import RunDialog, RunDialogStatus
# from spyder.plugins.run.api import RunActions, RunResult, ExtendedRunExecutionParameters
from spyder.plugins.run.api import (
    RunActions, RunResult, StoredRunExecutorParameters,
    RunContext, RunExecutor, RunResultFormat, RunInputExtension,
    RunConfigurationProvider, SupportedRunConfiguration,
    SupportedExecutionRunConfiguration, RunResultViewer, OutputFormat,
    RunConfigurationMetadata, RunParameterFlags, StoredRunConfigurationExecutor,
    ExtendedRunExecutionParameters, RunExecutionParameters,
    WorkingDirOpts, WorkingDirSource)

# Localization
_ = get_translation('spyder')


class RunExecutorListModel(QAbstractListModel):
    sig_executor_widget_changed = Signal(object)

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.uuid: Optional[str] = None
        self.current_input: Optional[Tuple[str, str]] = None
        # self.current_executor: Optional[str] = None
        self.executor_names: Dict[str, str] = {}
        # self.executors_per_input: Dict[Tuple[str, str], List[str]] = {}
        self.executor_configurations: Dict[Tuple[str, str], Dict[
            str, SupportedExecutionRunConfiguration]] = {}
        self.executors_per_input: Dict[Tuple[str, str], Dict[str, int]] = {}
        self.inverted_pos: Dict[Tuple[str, str], Dict[int, str]] = {}
        self.executor_priority: Dict[Tuple[str, str], Dict[str, int]] = {}

    def set_executor_name(self, executor_id: str, executor_name: str):
        self.executor_names[executor_id] = executor_name

    def add_input_executor_configuration(
            self, ext: str, context_id: str, executor_id: str,
            config: SupportedExecutionRunConfiguration):
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

        self.inverted_pos[(ext, context_id)] = {v: k for (k, v) in input_values}
        self.executor_priority[(ext, context_id)] = all_exec_prio

    def remove_input_executor_configuration(
            self, ext: str, context_id: str, executor_id: str):
        input_executors = self.executors_per_input[(ext, context_id)]
        pos = input_executors.pop(executor_id)

        inverted_executors = self.inverted_pos[(ext, context_id)]
        inverted_executors.pop(pos)

    def switch_input(self, uuid: str, run_input: Tuple[str, str]):
        if run_input in self.executors_per_input:
            self.beginResetModel()
            self.current_input = run_input
            self.uuid = uuid
            executors = self.executors_per_input[run_input]
            self.endResetModel()
        else:
            raise ValueError(
                f'The requested run input combination {run_input} is not '
                'registered')

    def get_selected_run_executor(
            self, index: int) -> Tuple[str, SupportedExecutionRunConfiguration]:
        executor_indices = self.inverted_pos[self.current_input]
        executor_name = executor_indices[index]
        executors = self.executor_configurations[self.current_input]
        executor = executors[executor_name]
        return executor_name, executor

    def get_initial_index(self) -> int:
        last_executor = self.parent.get_last_used_executor(self.uuid)
        executor_id = last_executor['executor']
        pos = 0
        if executor_id is not None:
            executors = self.executors_per_input[self.current_input]
            pos = executors[executor_id]
        return pos

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            executor_indices = self.inverted_pos[self.current_input]
            executor_id = executor_indices[index.row()]
            return self.executor_names[executor_id]

    def rowCount(self, parent: QModelIndex = None) -> int:
        executors = self.executors_per_input.get(self.current_input, {})
        return len(executors)


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
        if role == Qt.DisplayRole:
            uuid = self.metadata_index[index.row()]
            metadata = self.run_configurations[uuid]
            return metadata['name']

    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self.run_configurations)

    def get_run_configuration_parameters(
            self, uuid: str, executor: str) -> Optional[
                StoredRunExecutorParameters]:
        context, ext = self.get_metadata_context_extension(uuid)
        context_name = context['name']
        context_id = getattr(RunContext, context_name)
        return self.parent.get_executor_configuration_parameters(
            executor, ext, context_id)

    def get_last_used_execution_params(
            self, uuid: str, executor: str) -> Optional[str]:
        return self.parent.get_last_used_execution_params(uuid, executor)

    def pop(self, uuid: str) -> RunConfigurationMetadata:
        item = self.run_configurations.pop(uuid)
        self.metadata_index = dict(enumerate(self.run_configurations))
        self.inverted_index = {v: k for k, v in self.metadata_index.items()}
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
        total_saved_params = len(self.executor_conf_params)
        if pos == total_saved_params:
            if role == Qt.DisplayRole:
                return _("Default/Transient")
            elif role == Qt.ToolTipRole:
                return _("This configuration will not be saved after execution")
        else:
            params_id = self.params_index[pos]
            params = self.executor_conf_params[params_id]
            params_name = params['name']
            if role == Qt.DisplayRole:
                return params_name

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self.executor_conf_params) + 1

    def get_executor_parameters(
            self, index: int) -> Tuple[
                RunParameterFlags, RunExecutionParameters]:
        if index == len(self) - 1:
            default_working_dir = WorkingDirOpts(
                source=WorkingDirSource.ConfigurationDirectory,
                path=None)
            default_params = RunExecutionParameters(
                working_dir=default_working_dir,
                executor_params={})
            return RunParameterFlags.SetDefaults, default_params
        else:
            params_id = self.params_index[index]
            params = self.executor_conf_params[params_id]
            actual_params = params['params']
            return RunParameterFlags.SwitchValues, actual_params

    def get_parameters_uuid_name(
            self, index: int) -> Tuple[Optional[str], Optional[str]]:
        if index == len(self) - 1:
            return None, None

        params_id = self.params_index[index]
        params = self.executor_conf_params[params_id]
        return params['uuid'], params['name']

    def set_parameters(
            self, parameters: Dict[str, ExtendedRunExecutionParameters]):
        self.beginResetModel()
        self.executor_conf_params = parameters
        self.params_index = dict(enumerate(self.executor_conf_params))
        self.inverse_index = {self.params_index[k]: k
                              for k in self.params_index}
        self.endResetModel()

    def get_parameters_index(self, parameters_name: Optional[str]) -> int:
        index = self.inverse_index.get(parameters_name,
                                       len(self.executor_conf_params))
        return index

    def __len__(self) -> int:
        return len(self.executor_conf_params) + 1


class RunContainer(PluginMainContainer):
    """Non-graphical container used to spawn dialogs and creating actions."""

    def setup(self):
        self.current_working_dir: Optional[str] = None

        self.parameter_model = RunExecutorParameters(self)
        self.executor_model = RunExecutorListModel(self)
        self.metadata_model = RunConfigurationListModel(
            self, self.executor_model)

        self.run_metadata_provider: WeakValueDictionary[
            str, RunConfigurationProvider] = WeakValueDictionary()
        self.run_executors: WeakValueDictionary[
            str, RunExecutor] = WeakValueDictionary()
        self.viewers: WeakValueDictionary[
            str, RunResultViewer] = WeakValueDictionary()

        self.executor_use_count: Dict[str, int] = {}
        self.viewers_per_output: Dict[str, Set[str]] = {}
        self.currently_selected_configuration: Optional[str] = None

        self.run_action = self.create_action(
            RunActions.Run, _('&Run (New)'), self.create_icon('run'),
            tip=_("Run file"), triggered=self.run_file,
            register_shortcut=True, shortcut_context='_')

        self.configure_action = self.create_action(
            RunActions.Configure, _('&Configuration per file...'),
            self.create_icon('run_settings'), tip=_('Run settings'),
            triggered=self.edit_run_configurations, register_shortcut=True,
            shortcut_context='_'
        )

        self.re_run_action = self.create_action(
            RunActions.ReRun, _('Re-run &last script'),
            self.create_icon('run_again'), tip=_('Run again last file'),
            triggered=self.re_run_file, register_shortcut=True,
            shortcut_context='_'
        )

    def update_actions(self):
        pass

    def run_file(self):
        dialog = RunDialog(self, self.metadata_model, self.executor_model,
                           self.parameter_model)
        dialog.setup()
        dialog.exec_()

        status = dialog.status
        if status == RunDialogStatus.Close:
            return

        uuid, executor_name, ext_params = dialog.get_configuration()

        if (status & RunDialogStatus.Save) == RunDialogStatus.Save:
            exec_uuid = ext_params['uuid']
            if exec_uuid is not None:
                context, ext = self.metadata_model.get_metadata_context_extension(
                    uuid)
                context_name = context['name']
                context_id = getattr(RunContext, context_name)
                all_exec_params = self.get_executor_configuration_parameters(
                    executor_name, ext, context_id)
                exec_params = all_exec_params['params']
                exec_params[exec_uuid] = ext_params
                self.set_executor_configuration_parameters(
                    executor_name, ext, context_id, all_exec_params)

        if (status & RunDialogStatus.Run) == RunDialogStatus.Run:
            provider = self.run_metadata_provider[uuid]
            executor = self.run_executors[executor_name]
            run_conf = provider.get_run_configuration(uuid)

            working_dir_opts = ext_params['params']['working_dir']
            working_dir_source = working_dir_opts['source']
            if working_dir_source == WorkingDirSource.ConfigurationDirectory:
                fname = run_conf['metadata']['path']
                dirname = osp.dirname(fname)
            elif working_dir_source == WorkingDirSource.CurrentDirectory:
                dirname = self.current_working_dir
            else:
                dirname = working_dir_opts['path']

            dirname = dirname.replace("'", r"\'").replace('"', r'\"')
            working_dir_opts['path'] = dirname

            executor.exec_run_configuration(run_conf, ext_params)

            last_used_conf = StoredRunConfigurationExecutor(
                executor=executor_name, selected=ext_params['uuid'])

            self.set_last_used_execution_params(uuid, last_used_conf)

    def edit_run_configurations(self):
        pass

    def re_run_file(self):
        pass

    def switch_focused_run_configuration(self, uuid: Optional[str]):
        uuid = uuid or None
        if uuid is not None:
            self.run_action.setEnabled(True)
            self.currently_selected_configuration = uuid
            self.metadata_model.set_current_run_configuration(uuid)
        else:
            self.run_action.setEnabled(False)

    def set_current_working_dir(self, path: str):
        self.current_working_dir = path

    def register_run_configuration_metadata(
            self, provider: RunConfigurationProvider,
            metadata: RunConfigurationMetadata):
        """
        Register the metadata for a run configuration.

        Parameters
        ----------
        provider: RunConfigurationProvider
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunConfigurationProvider` interface and will register
            and own a run configuration.
        metadata: RunConfigurationMetadata
            The metadata for a run configuration that the provider is able to
            produce.
        """
        ext = metadata['input_extension']
        if ext not in RunInputExtension:
            RunInputExtension.add(ext)
        context = metadata['context']
        context_name = context['name']
        context_identifier = context.get('identifier', None)
        if context_identifier is None:
            context_identifier = camel_case_to_snake_case(context_name)
            context['identifier'] = context_identifier
        setattr(RunContext, context_name, context_identifier)

        run_id = metadata['uuid']
        self.run_metadata_provider[run_id] = provider
        self.metadata_model[run_id] = metadata

    def deregister_run_configuration_metadata(self, uuid: str):
        """
        Deregister a given run configuration by its unique identifier.

        Parameters
        ----------
        uuid: str
            Unique identifier for a run configuration metadata that will not
            longer exist. This id should have been registered using
            `register_run_configuration_metadata`.
        """
        self.metadata_model.pop(uuid)
        self.run_metadata_provider.pop(uuid)

    def register_executor_configuration(
            self, executor: RunExecutor,
            configuration: List[SupportedExecutionRunConfiguration]):
        """
        Register a :class:`RunExecutorProvider` instance to indicate its
        support for a given set of run configurations.

        Parameters
        ----------
        provider: RunExecutor
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunExecutor` interface and will register execution
            input type information.
        configuration: List[SupportedExecutionRunConfiguration]
            A list of input configurations that the provider is able to
            produce. Each configuration specifies the input extension
            identifier as well as the available execution context for that
            type.
        """
        executor_id = executor.NAME
        executor_name = executor.get_name()
        self.run_executors[executor_id] = executor
        executor_count = self.executor_use_count.get(executor_id, 0)
        for config in configuration:
            ext = config['input_extension']
            context = config['context']
            context_name = context['name']
            context_id = context.get('identifier', None)
            if context_id is None:
                context_id = camel_case_to_snake_case(context_name)
            setattr(RunContext, context_name, context_id)

            output_formats = []
            for out in config['output_formats']:
                output_name = out['name']
                output_id = out.get('identifier', None)
                if not output_id:
                    output_id = camel_case_to_snake_case(output_name)
                setattr(RunResultFormat, output_name, output_id)
                updated_out = {'name': output_name, 'identifier': output_id}
                output_formats.append(updated_out)

            config['output_formats'] = output_formats
            self.executor_model.add_input_executor_configuration(
                ext, context_id, executor_id, config)
            executor_count += 1

        self.executor_use_count[executor_id] = executor_count
        self.executor_model.set_executor_name(executor_id, executor_name)

    def deregister_executor_configuration(
            self, executor: RunExecutor,
            configuration: List[SupportedExecutionRunConfiguration]):
        """
        Deregister a :class:`RunExecutor` instance from providing a set
        of run configurations that are no longer supported by it.

        Parameters
        ----------
        executor: RunExecutor
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunExecutor` interface and will deregister execution
            input type information.
        configuration: List[SupportedExecutionRunConfiguration]
            A list of input configurations that the executor wants to
            deregister. Each configuration specifies the input extension
            identifier as well as the available execution context for that
            type.
        """
        executor_id = executor.NAME
        for config in configuration:
            ext = config['input_extension']
            context = config['context']
            context_name = context['name']
            context_id = getattr(RunContext, context_name)
            self.executor_model.remove_input_executor_configuration(
                ext, context_id, executor_id)
            self.executor_use_count[executor_id] -= 1

        if self.executor_use_count[executor_id] <= 0:
            self.run_executors.pop(executor_id)

    def register_viewer_configuration(
            self, viewer: RunResultViewer, formats: List[OutputFormat]):
        """
        Register a :class:`RunResultViewer` instance to indicate its support
        for a given set of output run result formats.

        Parameters
        ----------
        provider: RunResultViewer
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunResultViewer` interface and will register
            supported output formats.
        formats: List[OutputFormat]
            A list of output formats that the viewer is able to
            display.
        """
        for out_format in formats:
            format_name = out_format['name']
            format_id = out_format.get('identifier', None)
            if format_id is None:
                format_id = camel_case_to_snake_case(format_name)
            setattr(RunResultFormat, format_name, format_id)

            viewers_set = self.viewers.get(format_id, WeakSet())
            viewers_set.add(viewer)
            self.viewers[format_id] = viewers_set

    def deregister_viewer_configuration(
            self, viewer: RunResultViewer, formats: List[OutputFormat]):
        """
        Deregister a :class:`RunResultViewer` instance from supporting a set of
        output formats that are no longer supported by it.

        Parameters
        ----------
        provider: RunResultViewer
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunResultViewer` interface and will deregister
            output format support.
        formats: List[OutputFormat]
            A list of output formats that the viewer wants to deregister.
        """
        for out_format in formats:
            format_name = out_format['name']
            format_id = getattr(RunResultFormat, format_name)
            if format_id in self.viewers:
                viewer_set = self.viewers[format_id]
                viewer_set.discard(viewer)

    def get_executor_configuration_parameters(
            self, executor_name: str,
            extension: str, context_id: str) -> StoredRunExecutorParameters:
        """
        Retrieve the stored parameters for a given executor `executor_name`
        using context `context_id` with file extension `extension`.

        Parameters
        ----------
        executor_name: str
            The identifier of the run executor.
        extension: str
            The file extension to register the configuration parameters for.
        context_id: str
            The context to register the configuration parameters for.

        Returns
        -------
        config: StoredRunExecutorParameters
            A dictionary containing the run executor parameters for the given
            run configuration.
        """

        all_executor_params: Dict[
            str, Dict[Tuple[str, str],
                      StoredRunExecutorParameters]] = self.get_conf(
                        'parameters', default={})

        executor_params = all_executor_params.get(executor_name, {})
        params = executor_params.get(
            (extension, context_id), StoredRunExecutorParameters(params={}))

        return params

    def set_executor_configuration_parameters(
            self, executor_name: str, extension: str, context_id: str,
            params: StoredRunExecutorParameters):
        """
        Update and save the list of configuration parameters for a given
        executor on a given pair of context and file extension.

        Parameters
        ----------
        executor_name: str
            The identifier of the run executor.
        extension: str
            The file extension to register the configuration parameters for.
        context_id: str
            The context to register the configuration parameters for.
        params: StoredRunExecutorParameters
            A dictionary containing the run configuration parameters for
            the given executor.
        """
        all_executor_params: Dict[
            str, Dict[Tuple[str, str],
                      StoredRunExecutorParameters]] = self.get_conf(
                        'parameters', default={})

        executor_params = all_executor_params.get(executor_name, {})
        executor_params[(extension, context_id)] = params
        all_executor_params[executor_name] = executor_params
        self.set_conf('parameters', all_executor_params)

    def get_last_used_executor(self, uuid: str) -> StoredRunConfigurationExecutor:
        """
        Retrieve the last used executor for a given run configuration.

        Parameters
        ----------
        uuid: str
            The run configuration identifier.

        Returns
        -------
        last_used_executor: StoredRunConfigurationExecutor
            A dictionary containing the last used executor and parameters
            for the given run configuration.
        """
        mru_executors_uuids: Dict[
            str, StoredRunConfigurationExecutor] = self.get_conf(
                'last_used_parameters', default={})

        last_used_executor = mru_executors_uuids.get(
            uuid, StoredRunConfigurationExecutor(executor=None, selected=None))
        return last_used_executor

    def get_last_used_execution_params(
            self, uuid: str, executor_name: str) -> Optional[str]:
        """
        Retrieve the last used execution parameters for a given pair of run
        configuration and execution identifiers.

        Parameters
        ----------
        uuid: str
            The run configuration identifier.
        executor_name: str
            The identifier of the run executor.

        Returns
        -------
        last_used_params: Optional[str]
            The identifier of the last used parameters for the given
            run configuration on the given executor. None if the executor has
            not executed the run configuration.
        """

        mru_executors_uuids: Dict[
            str, StoredRunConfigurationExecutor] = self.get_conf(
                'last_used_parameters', default={})

        default = StoredRunConfigurationExecutor(
            executor=executor_name, selected=None)
        params = mru_executors_uuids.get(uuid, default)

        last_used_params = None
        if params['executor'] == executor_name:
            last_used_params = params['selected']
        return last_used_params

    def set_last_used_execution_params(
            self, uuid: str, params: StoredRunConfigurationExecutor):
        """
        Store the last used executor and parameters for a given run
        configuration.

        Parameters
        ----------
        uuid: str
            The run configuration identifier.
        params: StoredRunConfigurationExecutor
            Dictionary containing the last used executor and run parameters
            used.
        """
        mru_executors_uuids: Dict[
            str, StoredRunConfigurationExecutor] = self.get_conf(
                'last_used_parameters', default={})

        mru_executors_uuids[uuid] = params
        self.set_conf('last_used_parameters', mru_executors_uuids)
