# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder run container."""

# Standard library imports
import functools
import os.path as osp
from collections import OrderedDict
from weakref import WeakSet, WeakValueDictionary
from typing import Any, Callable, List, Dict, Tuple, Set, Optional

# Third-party imports
from qtpy.QtGui import QIcon
from qtpy.QtCore import Qt, Signal, QAbstractListModel, QModelIndex
from qtpy.QtWidgets import QMessageBox, QAction, QDialog

# Local imports
from spyder.utils.sourcecode import camel_case_to_snake_case
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.api.translations import get_translation
from spyder.plugins.run.widgets import RunDialog, RunDialogStatus
# from spyder.plugins.run.api import RunActions, RunResult, ExtendedRunExecutionParameters
from spyder.plugins.run.api import (
    RunActions, RunConfiguration, RunExecutionMetadata, RunResult, StoredRunExecutorParameters,
    RunContext, RunExecutor, RunResultFormat, RunInputExtension,
    RunConfigurationProvider, SupportedRunConfiguration,
    SupportedExecutionRunConfiguration, RunResultViewer, OutputFormat,
    RunConfigurationMetadata, RunParameterFlags, StoredRunConfigurationExecutor,
    ExtendedRunExecutionParameters, RunExecutionParameters,
    WorkingDirOpts, WorkingDirSource, Context)

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

    def executor_supports_configuration(self, executor: str,
                                        exec_input: Tuple[str, str]) -> bool:
        input_executors = self.executor_configurations.get(exec_input, {})
        return executor in input_executors

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            executor_indices = self.inverted_pos[self.current_input]
            executor_id = executor_indices[index.row()]
            return self.executor_names[executor_id]

    def rowCount(self, parent: QModelIndex = None) -> int:
        executors = self.executors_per_input.get(self.current_input, {})
        return len(executors)

    def __contains__(self, exec_input: Tuple[str, str]) -> bool:
        return exec_input in self.executor_configurations

    def __getitem__(self, input_executor: tuple) -> SupportedExecutionRunConfiguration:
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

    def get_last_used_executor_parameters(
            self, uuid: str) -> StoredRunConfigurationExecutor:
        return self.parent.get_last_used_executor_parameters(uuid)

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

    sig_run_action_created = Signal(str, bool, str)

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
            RunActions.Run, _('&Run'), self.create_icon('run'),
            tip=_("Run file"), triggered=self.run_file,
            register_shortcut=True, shortcut_context='_',
            context=Qt.ApplicationShortcut)

        self.configure_action = self.create_action(
            RunActions.Configure, _('&Configuration per file...'),
            self.create_icon('run_settings'), tip=_('Run settings'),
            triggered=functools.partial(self.edit_run_configurations,
                                        display_dialog=True,
                                        disable_run_btn=True),
            register_shortcut=True,
            shortcut_context='_', context=Qt.ApplicationShortcut
        )

        self.re_run_action = self.create_action(
            RunActions.ReRun, _('Re-run &last file'),
            self.create_icon('run_again'), tip=_('Run again last file'),
            triggered=self.re_run_file, register_shortcut=True,
            shortcut_context='_'
        )

        self.current_input_provider: Optional[str] = None
        self.current_input_extension: Optional[str] = None
        self.context_actions: Dict[
            Tuple[str, str], Tuple[QAction, Callable]] = {}
        self.last_executed_per_context: Dict[
            str, Tuple[
                str, RunConfiguration, ExtendedRunExecutionParameters]] = {}

    def update_actions(self):
        pass

    def gen_annonymous_execution_run(self, context: str,
                                     action_name: Optional[str]) -> Callable:
        def annonymous_execution_run():
            input_provider = self.run_metadata_provider[
                self.currently_selected_configuration]
            run_conf = input_provider.get_run_configuration_per_context(
                context, action_name)

            if run_conf is None:
                return

            uuid = self.currently_selected_configuration
            super_metadata = self.metadata_model[uuid]
            extension = super_metadata['input_extension']

            path = super_metadata['path']
            dirname = osp.dirname(path)
            dirname = dirname.replace("'", r"\'").replace('"', r'\"')

            last_executor = self.get_last_used_executor_parameters(uuid)
            last_executor = last_executor['executor']
            run_comb = (extension, context)
            if (last_executor is None or
                    not self.executor_model.executor_supports_configuration(
                        last_executor, run_comb)):
                last_executor = self.executor_model.get_default_executor(
                    run_comb)
            executor_metadata = self.executor_model[
                ((extension, context), last_executor)]
            ConfWidget = executor_metadata['configuration_widget']

            conf = {}
            if ConfWidget is not None:
                conf = ConfWidget.get_default_configuration()

            working_dir = WorkingDirOpts(
                source=WorkingDirSource.ConfigurationDirectory,
                path=dirname)

            exec_params = RunExecutionParameters(
                working_dir=working_dir, executor_params=conf)

            ext_exec_params = ExtendedRunExecutionParameters(
                uuid=None, name=None, params=exec_params)
            executor = self.run_executors[last_executor]
            executor.exec_run_configuration(run_conf, ext_exec_params)
        return annonymous_execution_run

    def run_file(self, selected_uuid=None):
        if not isinstance(selected_uuid, bool) and selected_uuid is not None:
            self.switch_focused_run_configuration(selected_uuid)

        exec_params = self.get_last_used_executor_parameters(
            self.currently_selected_configuration)

        first_execution = exec_params['first_execution']
        display_dialog = exec_params['display_dialog']
        display_dialog = display_dialog or first_execution

        status, conf = self.edit_run_configurations(
            display_dialog=display_dialog)

        if status == RunDialogStatus.Close:
            return

        (uuid, executor_name,
         ext_params, __) = conf

        if (status & RunDialogStatus.Run) == RunDialogStatus.Run:
            provider = self.run_metadata_provider[uuid]
            executor = self.run_executors[executor_name]
            run_conf = provider.get_run_configuration(uuid)

            context, ext = self.metadata_model.get_metadata_context_extension(
                    uuid)
            context_name = context['name']
            context_id = getattr(RunContext, context_name)

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


    def edit_run_configurations(self, display_dialog=True,
                                disable_run_btn=False):
        dialog = RunDialog(self, self.metadata_model, self.executor_model,
                           self.parameter_model,
                           disable_run_btn=disable_run_btn)
        dialog.setup()

        if display_dialog:
            dialog.exec_()
        else:
            dialog.run_btn_clicked()
            dialog.accept()

        status = dialog.status
        if status == RunDialogStatus.Close:
            return status, tuple()

        (uuid, executor_name,
         ext_params, open_dialog) = dialog.get_configuration()

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

            last_used_conf = StoredRunConfigurationExecutor(
                executor=executor_name, selected=ext_params['uuid'],
                display_dialog=open_dialog, first_execution=False)

            self.set_last_used_execution_params(uuid, last_used_conf)

        return status, (uuid, executor_name, ext_params, open_dialog)

    def re_run_file(self):
        pass

    def switch_focused_run_configuration(self, uuid: Optional[str]):
        uuid = uuid or None
        if uuid is not None and uuid != self.currently_selected_configuration:
            self.run_action.setEnabled(True)
            self.currently_selected_configuration = uuid
            self.metadata_model.set_current_run_configuration(uuid)

            metadata = self.metadata_model[uuid]
            self.current_input_provider = metadata['source']
            self.current_input_extension = metadata['input_extension']

            input_provider = self.run_metadata_provider[uuid]
            input_provider.focus_run_configuration(uuid)

            for context, act in self.context_actions:
                status = (self.current_input_extension,
                          context) in self.executor_model
                action, __ = self.context_actions[(context, act)]
                action.setEnabled(status)
        elif uuid is None:
            self.run_action.setEnabled(False)
            for context, act in self.context_actions:
                action, __ = self.context_actions[(context, act)]
                action.setEnabled(False)

    def set_current_working_dir(self, path: str):
        self.current_working_dir = path

    def create_run_button(self, context_name: str, text: str,
                          icon: Optional[QIcon] = None,
                          tip: Optional[str] = None,
                          shortcut_context: Optional[str] = None,
                          register_shortcut: bool = False,
                          extra_action_name: Optional[str] = None,
                          conjunction_or_preposition: str = "and"
                          ) -> QAction:
        """
        Create a run or a "run and do something" button
        for a specific run context.

        Parameters
        ----------
        context_name: str
            The identifier of the run context.
        text: str
           Localized text for the action
        icon: Optional[QIcon]
            Icon for the action when applied to menu or toolbutton.
        tip: Optional[str]
            Tooltip to define for action on menu or toolbar.
        shortcut_context: Optional[str]
            Set the `str` context of the shortcut.
        register_shortcut: bool
            If True, main window will expose the shortcut in Preferences.
            The default value is `False`.
        extra_action_name: Optional[str]
            The name of the action to execute on the run input provider
            after requesting the run input.
        conjunction_or_preposition: str
            The conjunction or preposition used to describe the action that
            should take place after the context. i.e., run <and> advance,
            run selection <from> the current line, etc. Default: and

        Notes
        -----
        1. The context passed as a parameter must be a subordinate of the
        context of the current focused run configuration that was
        registered via `register_run_configuration_metadata`. e.g., Cell can
        be used if and only if the file was registered.

        2. The button will be registered as `run <context>` or
        `run <context> and <extra_action_name>` on the action registry.

        3. The created button will operate over the last focused run input
        provider.

        4. If the requested button already exists, this method will not do
        anything, which implies that the first registered shortcut will be the
        one to be used. For the built-in run contexts
        (file, cell and selection), the editor will register their
        corresponding icons and shortcuts.
        """
        if (context_name, extra_action_name) in self.context_actions:
            action, __ = self.context_actions[
                (context_name, extra_action_name)]
            return action

        action_name = f'run {context_name}'
        if extra_action_name is not None:
            action_name = (f'{action_name} {conjunction_or_preposition} '
                           f'{extra_action_name}')

        func = self.gen_annonymous_execution_run(
            context_name, extra_action_name)

        action = self.create_action(
            action_name, text, icon, tip=tip,
            triggered=func,
            register_shortcut=register_shortcut,
            shortcut_context=shortcut_context,
            context=Qt.ApplicationShortcut
        )

        self.context_actions[(context_name, extra_action_name)] = (
            action, func)

        self.sig_run_action_created.emit(action_name, register_shortcut,
                                         shortcut_context)
        return action

    def create_re_run_button(self, context: Context, extra_behaviour: str):
        pass

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

    def get_last_used_executor_parameters(
            self, uuid: str) -> StoredRunConfigurationExecutor:
        """
        Retrieve the last used execution parameters for a given
        run configuration.

        Parameters
        ----------
        uuid: str
            The run configuration identifier.

        Returns
        -------
        last_used_params: StoredRunConfigurationExecutor
            A dictionary containing the last used executor and parameters
            for the given run configuration.
        """
        mru_executors_uuids: Dict[
            str, StoredRunConfigurationExecutor] = self.get_conf(
                'last_used_parameters', default={})

        last_used_params = mru_executors_uuids.get(
            uuid, StoredRunConfigurationExecutor(
                executor=None, selected=None, display_dialog=False,
                first_execution=True))
        return last_used_params

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
            executor=executor_name, selected=None, display_dialog=False,
            first_execution=True)
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
