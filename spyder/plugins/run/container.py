# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder run container."""

# Standard library imports
from optparse import Option
import re
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
from spyder.plugins.run.widgets import RunDialog
from spyder.plugins.run.api import RunActions, RunResult
from spyder.plugins.run.api import (
    RunContext, RunExecutor, RunResultFormat, RunInputExtension,
    RunConfigurationProvider, SupportedRunConfiguration,
    SupportedExecutionRunConfiguration, RunResultViewer, OutputFormat,
    RunConfigurationMetadata)

# Localization
_ = get_translation('spyder')


class RunExecutorListModel(QAbstractListModel):
    sig_executor_widget_changed = Signal(object)

    def __init__(self, parent):
        super().__init__(parent)
        self.current_input: Optional[Tuple[str, str]] = None
        # self.current_executor: Optional[str] = None
        self.executor_names: Dict[str, str] = {}
        self.executors_per_input: Dict[
            Tuple[str, str], Dict[
                str, SupportedExecutionRunConfiguration]] = {}

    def set_executor_name(self, executor_id: str, executor_name: str):
        self.executor_names[executor_id] = executor_name

    def add_input_executor_configuration(
            self, ext: str, context_id: str, executor_id: str,
            config: SupportedExecutionRunConfiguration):
        input_executors = self.executors_per_input.get((ext, context_id), {})
        executor_configurations = input_executors.get(executor_id, {})
        executor_configurations[executor_id] = config
        self.executors_per_input[(ext, context_id)] = executor_configurations

    def remove_input_executor_configuration(
            self, ext: str, context_id: str, executor_id: str):
        input_executors = self.executors_per_input[(ext, context_id)]
        input_executors.pop(executor_id)

    def switch_input(self, run_input: Tuple[str, str]):
        if run_input in self.executors_per_input:
            self.beginResetModel()
            self.current_input = run_input
            executors = self.executors_per_input[run_input]
            self.endResetModel()
        else:
            raise ValueError(
                f'The requested run input combination {run_input} is not '
                'registered')

    def get_selected_run_configuration(self, index: int) -> SupportedExecutionRunConfiguration:
        input_executors = self.executors_per_input[self.current_input]
        sorted_executors = sorted(list(input_executors.keys()))
        executor = sorted_executors[index]
        return input_executors[executor]

    def get_initial_index(self) -> int:
        return 0

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            executors = self.executors_per_input[self.current_input]
            sorted_executors = sorted(list(executors.keys()))
            executor_id = sorted_executors[index.row()]
            # self.current_executor = executor_id
            return self.executor_names[executor_id]

    def rowCount(self, parent: QModelIndex = None) -> int:
        executors = self.executors_per_input.get(self.current_input, {})
        return len(executors)


class RunConfigurationListModel(QAbstractListModel):
    def __init__(self, parent, executor_model):
        super().__init__(parent)
        self.parent = parent
        self.current_configuration: Optional[str] = None
        self.metadata_index: Dict[int, str] = {}
        self.inverted_index: Dict[str, int] = {}
        self.run_configurations: OrderedDict[
            str, RunConfigurationMetadata] = OrderedDict()
        self.executor_model: RunExecutorListModel = executor_model

    def set_current_run_configuration(self, uuid: str):
        self.current_configuration = uuid

    def get_initial_index(self) -> int:
        return self.inverted_index[self.current_configuration]

    def update_index(self, index: int):
        uuid = self.metadata_index[index]
        metadata = self.run_configurations[uuid]
        context_name = metadata['context']['name']
        context_id = getattr(RunContext, context_name)
        ext = metadata['input_extension']
        self.executor_model.switch_input((ext, context_id))

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            uuid = self.metadata_index[index.row()]
            metadata = self.run_configurations[uuid]
            return metadata['name']

    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self.run_configurations)

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

class RunContainer(PluginMainContainer):
    """Non-graphical container used to spawn dialogs and creating actions."""

    def setup(self):
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
        dialog = RunDialog(self, self.metadata_model, self.executor_model)
        dialog.setup()
        dialog.exec_()

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
        Register a :class:`RunExecutorProvider` instance to indicate its support
        for a given set of run configurations.

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
            A list of input configurations that the executor wants to deregister.
            Each configuration specifies the input extension
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
