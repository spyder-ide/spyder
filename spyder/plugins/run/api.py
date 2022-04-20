# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Run API."""

# Standard library imports
from __future__ import annotations

import sys
from datetime import datetime
from typing import Any, Set, List, Union, Optional, Type

# PEP 589 and 544 are available from Python 3.8 onwards
if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

# Support PEP 655 (available from Python 3.11 onwards)
from typing_extensions import NotRequired

# Qt imports
from qtpy.QtWidgets import QWidget


class RunActions:
    Run = 'run'
    Configure = 'configure'
    ReRun = 're-run last script'


class RunContextType(dict):
    def __init__(self, identifier: str):
        super().__init__()

        self.identifier = identifier

    def __setattr__(self, key: str, value: str) -> None:
        if key not in self:
            self[key] = value

    def __getattribute__(self, key: str) -> str:
        if key in self:
            return self[key]
        return super().__getattribute__(key)


RunContext = RunContextType('context')
RunResultFormat = RunContextType('result display format')
RunInputExtension = set({})

# RunContext.File = 'file'
# RunContext.Selection = 'selection'
# RunContext.Cell = 'cell'

RunResultFormat.NoDisplay = 'no_display'


class RunConfigurationMetadata(TypedDict):
    """Run input metadata schema."""
    # Human-readable name for the run input.
    name: str
    # Name of the RunConfigurationProvider that produced the run configuration.
    source: str
    # Timestamp of the run input information.
    timestamp: datetime
    # Extra metadata information.
    extra: NotRequired[dict]
    # Unique identifier for this run configuration. This should be generated
    # and managed by the RunConfigurationProvider
    uuid: str
    # The context of the input provided. e.g., file, selection, cell, others.
    # This attribute can be customized by the `RunConfigurationProvider` when
    # registering with the run plugin. The context can be compared against the
    # values of `RunContext`. e.g., `info['context'] == RunContext.File`
    context: Context
    # File extension or identifier of the input context. It must belong to the
    # `RunInputExtension` set.
    input_extension: str


class RunConfiguration(TypedDict):
    """Run input information schema."""

    # The output format to produce after executing the input. Each entry on the
    # set must belong to the `RunResultFormat` dict. The executor is responsible
    # of producing the correct format. This field will be available on a
    # RunExecutor but it is not necessary for a RunConfigurationProvider to
    # include it.
    output_formats: NotRequired[Set[str]]

    # Input to process by the executor. The executor is responsible for the
    # correct interpretation of the input type.
    run_input: Any

    # Run input metadata information.
    metadata: RunConfigurationMetadata


class RunExecutionMetadata(TypedDict):
    """Run result metadata schema."""

    # Human readable identifier for the run executor.
    executor: str
    # Start timestamp of the run execution.
    start_timestamp: datetime
    # End timestamp of the run execution.
    end_timestamp: datetime
    # Extra execution metadata. This field can be used to store
    # resource consumption, statistics and other fields that might be relevant.
    extra: NotRequired[dict]


class RunResultError(TypedDict):
    # Error code for the current error.
    code: Optional[int]
    # Human-readable message that describes the error.
    message: Optional[str]


class RunResult(TypedDict):
    """Run result entry schema."""

    # The output format for the current run result. It must belong to the
    # `RunResultDisplay` dict.
    output_format: str

    # The output of the run result. The viewer is responsible for the current
    # interpretation of the output type.
    run_output: Union[Any, RunResultError]

    # File extension or identifier of the input context. It must belong to the
    # `RunInputExtension` set.
    input_extension: str

    # Original run input metadata.
    metadata: RunConfigurationMetadata

    # Execution metadata.
    execution_metadata: RunExecutionMetadata

    # True if the execution result yielded an error, False otherwise. If the
    # execution failed, then the `run_output` field will comply with the
    # `RunResultError` schema.
    is_error: bool


class Context(TypedDict):
    """Run context name schema."""
    # CamelCase name of the context.
    name: str
    # String identifier for the run context. If non-existent or None, then
    # a snake_case version of the name is used.
    identifier: NotRequired[Optional[str]]


class OutputFormat(TypedDict):
    """Output format information schema."""
    # Human-readable name for the output format. It must be CamelCase
    name: str
    # String identifier for the output format. If non-existent or None, then
    # a snake_case version of the name is used.
    identifier: NotRequired[Optional[str]]


class SupportedRunConfiguration(TypedDict):
    """Run configuration entry schema."""

    # File extension or identifier of the input context. It must belong to the
    # `RunInputExtension` set.
    input_extension: str

    # The supported contexts for the given input extension.
    # e.g., file, selection, cell, others.
    # The context can be compared against the values of `RunContext`. e.g.,
    # `info['context'] == RunContext.File`
    contexts: List[Context]


class SupportedExecutionRunConfiguration(TypedDict):
    """Run execution configuration metadata."""

    # File extension or identifier of the input context. It must belong to the
    # `RunInputExtension` set.
    input_extension: str

    # The context for the given input extension.
    # e.g., file, selection, cell, others.
    # The context can be compared against the values of `RunContext`. e.g.,
    # `info['context'] == RunContext.File`
    context: Context

    # The output formats available for the given context and extension.
    output_formats: List[OutputFormat]

    # The configuration widget used to set the options for the current
    # input extension and context combination. If None or missing then no
    # configuration widget will be shown on the Run dialog for that combination.
    configuration_widget: NotRequired[Optional[RunExecutorConfigurationGroup]]

    # True if the executor requires a path in order to work. False otherwise
    requires_cwd: bool


class RunConfigurationProvider:
    """
    Interface used to retrieve inputs to run on a code executor.

    This API needs to be implemented by any plugin that wants to provide
    an input/file to a code runner. e.g., Editor files/ to be executed into
    the IPythonConsole. This interface needs to be covariant with respect to
    :class:`spyder.api.plugins.SpyderDockablePlugin`
    """

    def get_run_configuration(self, uuid: str) -> RunConfiguration:
        """
        Return the run information for the specified identifier.

        Arguments
        ---------
        context: str
            The unique identifier for the run configuration requested, such
            id should have been registered previously via
            `register_run_configuration_metadata` on the Run plugin.

        Returns
        -------
        configuration: RunConfiguration
            A dictionary containing the information required by the run
            executor.
        """
        raise NotImplementedError(f'{type(self)} must implement get_run_input')


class RunExecutor:
    """
    Interface used to execute run context information.

    This API needs to be implemented by any plugin that wants to execute
    an input produced by a :class:`RunConfigurationProvider` to produce an output
    compatible by a :class:`RunResultViewer`. This interface needs to be
    covariant with respect to :class:`spyder.api.plugins.SpyderPluginV2`
    """

    def exec_run_configuration(self, input: RunConfiguration) -> List[RunResult]:
        """
        Execute a run configuration.

        Arguments
        ---------
        input: RunConfiguration
            A dictionary containing the information required to execute the
            run input.

        Returns
        -------
        results: List[RunResult]
            A list of `RunResult` dictionary entries, one per each `run_output`
            format requested by the input. Each entry must comply with the
            format requested.

        Notes
        -----
        This function must not crash or raise an exception, instead the
        `RunResult` must wrap a `RunResultError` structure.
        """
        raise NotImplementedError(f'{type(self)} must implement exec_run_input')


class RunResultViewer:
    """
    Interface used to display run execution results.

    This API needs to be implemented by any plugin that wants to display
    an output produced by a :class:`RunResultViewer`. This interface needs
    to be covariant with respect to :class:`spyder.api.plugins.SpyderPluginV2`
    """

    def display_run_result(self, result: RunResult):
        """
        Display the output of a run execution.

        Arguments
        ---------
        result: RunResult
            A `RunResult` entry that contains the run execution information,
            including both input and execution metadata, as well as the result
            representation in a format that the `RunResultViewer` instance
            supports.
        """
        raise NotImplementedError(
            f'{type(self)} must implement display_run_result')


class RunExecutorConfigurationGroup(QWidget):
    """
    QWidget subclass used to declare a RunExecutor configuration options.

    Every executor that wants to add a configuration group to the Run
    dialog for a given context and input extension must subclass this
    interface.

    Parameters
    ---------
    parent: QWidget
        The instance of the run dialog, which will be always given by
        parameter.
    context: Context
        The run configuration context for which the dialog will provide
        options.
    input_extension: str
        The run configuration input extension for which the dialog will
        provide options.
    input_metadata: RunConfigurationMetadata
        The run configuration metadata that will be tentatively executed.

    Notes
    -----
    The aforementioned parameters will be always be passed by the Run
    dialog instance, and no subclass should modify them.
    """

    def __init__(self, parent: QWidget, context: Context, input_extension: str,
                 input_metadata: RunConfigurationMetadata):
        """Create a run executor configuration widget."""
        super().__init__(parent)
        self.context = context
        self.input_extension = input_extension
        self.input_metadata = input_metadata

    def get_configuration(self) -> dict:
        """
        Obtain a dictionary containing the configuration options for
        the executor.
        """
        return {}

    def get_default_configuration(self) -> dict:
        """
        Obtain a dictionary containing the default values for the
        executor configuration.
        """
        return {}

    def set_configuration(self, config: dict):
        """
        Given a configuration dictionary compatible with the current
        configuration group, set the graphical elements to their corresponding
        values.
        """
        raise NotImplementedError(f'{type(self)} must implement '
                                  'set_configuration')
