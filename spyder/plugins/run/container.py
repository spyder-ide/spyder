# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder run container."""

# Standard library imports
from cProfile import run
import re
from collections import OrderedDict
from weakref import WeakSet, WeakValueDictionary
from typing import List, Dict, Tuple

# Third-party imports
from qtpy.QtCore import Qt, Signal, QAbstractListModel, QModelIndex
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.utils.sourcecode import camel_case_to_snake_case
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.api.translations import get_translation
from spyder.plugins.run.api import RunActions, RunResult
from spyder.plugins.run.api import (
    RunContext, RunExecutor, RunResultFormat, RunInputExtension,
    RunConfigurationProvider, SupportedRunConfiguration,
    SupportedExecutionRunConfiguration, RunResultViewer, OutputFormat,
    RunConfigurationMetadata)

# Localization
_ = get_translation('spyder')


class RunContainer(PluginMainContainer):
    """Non-graphical container used to spawn dialogs and creating actions."""

    def setup(self):
        self.run_metadata_provider: WeakValueDictionary[str, RunConfigurationProvider] = WeakValueDictionary()
        self.executors: Dict[Tuple[str, str, str], WeakSet[RunExecutor]] = {}
        self.viewers: Dict[str, WeakSet[RunResultViewer]] = {}

        self.run_action = self.create_action(
            RunActions.Run, _('&Run'), self.create_icon('run'),
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
        pass

    def edit_run_configurations(self):
        pass

    def re_run_file(self):
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
        for config in configuration:
            ext = config['input_extension']
            context = config['context']
            context_name = context['name']
            context_id = getattr(RunContext, context_name)
            for out in config['output_formats']:
                output_name = out['name']
                output_id = out.get('identifier', None)
                if not output_id:
                    output_id = camel_case_to_snake_case(output_name)
                setattr(RunResultFormat, output_name, output_id)

                executor_set = self.executors.get((ext, context_id, output_id), WeakSet())
                executor_set.add(executor)
                self.executors[(ext, context_id, output_id)] = executor_set

    def deregister_executor_configuration(
            self, provider: RunExecutor,
            configuration: List[SupportedExecutionRunConfiguration]):
        """
        Deregister a :class:`RunExecutor` instance from providing a set
        of run configurations that are no longer supported by it.

        Parameters
        ----------
        provider: RunExecutor
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunExecutor` interface and will deregister execution
            input type information.
        configuration: List[SupportedExecutionRunConfiguration]
            A list of input configurations that the provider wants to deregister.
            Each configuration specifies the input extension
            identifier as well as the available execution context for that
            type.
        """
        for config in configuration:
            ext = config['input_extension']
            context = config['context']
            context_name = context['name']
            context_id = getattr(RunContext, context_name)

            for out in config['output_formats']:
                output_name = out['name']
                output_id = out.get('identifier', None)
                output_id = getattr(RunResultFormat, output_name, output_id)
                if (ext, context_id, output_id) in self.executors:
                    executor_set = self.executors[(ext, context_id, output_id)]
                    executor_set.discard(provider)

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
