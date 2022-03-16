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
from typing import Any, Set, List, Union, Optional

# PEP 589 and 544 are available from Python 3.8 onwards
if sys.version_info >= (3, 8):
    from typing import TypedDict, Protocol
else:
    from typing_extensions import TypedDict, Protocol

# Support PEP 655 (available from Python 3.11 onwards)
from typing_extensions import NotRequired


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


class RunInputMetadata(TypedDict):
    """Run input metadata schema."""
    # Human-readable name for the run input.
    name: str
    # Source of the input provided.
    source: str
    # Timestamp of the run input information.
    timestamp: datetime
    # Extra metadata information.
    extra: NotRequired[dict]


class RunInformation(TypedDict):
    """Run input information schema."""

    # The context of the input provided. e.g., file, selection, cell, others.
    # This attribute can be customized by the `RunInputProvider` when
    # registering with the run plugin. The context can be compared against the
    # values of `RunContext`. e.g., `info['context'] == RunContext.File`
    context: str

    # The output format to produce after executing the input. Each entry on the
    # set must belong to the `RunResultFormat` dict. The executor is responsible
    # of producing the correct format. This field will be available on a
    # RunExecutor but it is not necessary for a RunInputProvider to
    # include it.
    output_formats: NotRequired[Set[str]]

    # Input to process by the executor. The executor is responsible for the
    # correct interpretation of the input type.
    run_input: Any

    # Run input metadata information.
    metadata: RunInputMetadata

    # File extension or identifier of the input context. It must belong to the
    # `RunInputExtension` set.
    input_extension: str


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
    metadata: RunInputMetadata

    # Execution metadata.
    execution_metadata: RunExecutionMetadata

    # True if the execution result yielded an error, False otherwise. If the
    # execution failed, then the `run_output` field will comply with the
    # `RunResultError` schema.
    is_error: bool


class Context(TypedDict):
    """Run context name schema."""
    # Human-readable name for the run context. It must be CamelCase
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

    # The supported contexts for the given input extension. e.g., file, selection, cell, others.
    # The context can be compared against the values of `RunContext`. e.g.,
    # `info['context'] == RunContext.File`
    contexts: List[Context]


class SupportedExecutionRunConfiguration(TypedDict):
    """Run execution configuration metadata."""

    # File extension or identifier of the input context. It must belong to the
    # `RunInputExtension` set.
    input_extension: str

    # The context for the given input extension. e.g., file, selection, cell, others.
    # The context can be compared against the values of `RunContext`. e.g.,
    # `info['context'] == RunContext.File`
    context: Context

    # The output formats available for the given context and extension.
    output_formats: List[OutputFormat]


class RunInputProvider:
    """
    Interface used to retrieve inputs to run on a code executor.

    This API needs to be implemented by any plugin that wants to provide
    an input/file to a code runner. e.g., Editor files/ to be executed into
    the IPythonConsole. This interface needs to be covariant with respect to
    :class:`spyder.api.plugins.SpyderDockablePlugin`
    """

    def get_run_input(self, context: str) -> RunInformation:
        """
        Return the run information for the specified context.

        Arguments
        ---------
        context: str
            The context for the run request. It must be a member of
            :data:`RunContext`.

        Returns
        -------
        information: RunInformation
            A dictionary containing the information required by the run
            executor.
        """
        raise NotImplementedError(f'{type(self)} must implement get_run_input')


class RunExecutor:
    """
    Interface used to execute run context information.

    This API needs to be implemented by any plugin that wants to execute
    an input produced by a :class:`RunInputProvider` to produce an output
    compatible by a :class:`RunResultViewer`. This interface needs to be
    covariant with respect to :class:`spyder.api.plugins.SpyderPluginV2`
    """

    def exec_run_input(self, input: RunInformation) -> List[RunResult]:
        """
        Execute a run input.

        Arguments
        ---------
        input: RunInformation
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
        raise NotImplementedError(f'{type(self)} must implement display_run_result')
