# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Run API."""

# Standard library imports
from __future__ import annotations

import functools
from datetime import datetime
import logging
from typing import Any, Callable, Set, List, Union, Optional, Dict, TypedDict

# Third-party imports
from qtpy.QtCore import QObject
from qtpy.QtWidgets import QWidget
from typing_extensions import NotRequired # Available from Python 3.11+

logger = logging.getLogger(__name__)


class RunActions:
    Run = 'run'
    Configure = 'configure'
    ReRun = 're-run last script'
    GlobalConfigurations = "global configurations"


class RunContextType(dict):
    def __init__(self, identifier: str):
        super().__init__()

    def __setattr__(self, key: str, value: str) -> None:
        if key not in self:
            self[key] = value

    def __getattribute__(self, key: str) -> str:
        if key in self:
            return self[key]
        return super().__getattribute__(key)


RunContext = RunContextType('context')
RunContext.File = 'file'
RunContext.Cell = 'cell'
RunContext.Selection = 'selection'

RunResultFormat = RunContextType('result display format')

RunResultFormat.NoDisplay = 'no_display'


class RunConfigurationMetadata(TypedDict):
    """Run input metadata schema."""

    # Human-readable name for the run input.
    name: str

    # Name of the RunConfigurationProvider that produced the run configuration.
    source: str

    # File path to the source used for the run configuration.
    path: str

    # Timestamp of the run input information.
    timestamp: datetime

    # Extra metadata information.
    extra: NotRequired[dict]

    # Unique identifier for this run configuration. This should be generated
    # and managed by the RunConfigurationProvider
    uuid: str

    # The context of the input provided. e.g. file, selection, cell or others.
    # This attribute can be customized by the `RunConfigurationProvider` when
    # registering with the run plugin. The context can be compared against the
    # values of `RunContext`. e.g. `info['context'] == RunContext.File`.
    context: Context

    # File extension or identifier of the input context.
    input_extension: str


class RunConfiguration(TypedDict):
    """Run input information schema."""

    # The output format to produce after executing the input. Each entry on the
    # set must belong to the `RunResultFormat` dict. The executor is
    # responsible of producing the correct format. This field will be available
    # on a RunExecutor but it is not necessary for a RunConfigurationProvider
    # to include it.
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

    # Extra execution metadata. This field can be used to store resource
    # consumption, statistics and other fields that might be relevant.
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

    # File extension or identifier of the input context.
    input_extension: str

    # Original run input metadata.
    metadata: RunConfigurationMetadata

    # Execution metadata.
    execution_metadata: RunExecutionMetadata

    # True if the execution result yielded an error, False otherwise. If the
    # execution failed, then the `run_output` field will comply with the
    # `RunResultError` schema.
    is_error: bool


PossibleRunResult = Union[RunResult, RunResultError]


class Context(TypedDict):
    """Run context name schema."""

    # CamelCase name of the context.
    name: str

    # String identifier for the run context. If non-existent or None, then a
    # snake_case version of the name is used.
    identifier: NotRequired[Optional[str]]


class OutputFormat(TypedDict):
    """Output format information schema."""

    # Human-readable name for the output format. It must be CamelCase
    name: str

    # String identifier for the output format. If non-existent or None, then a
    # snake_case version of the name is used.
    identifier: NotRequired[Optional[str]]


class ExtendedContext(TypedDict):
    """Extended context information schema."""

    # The specified context information.
    context: Context

    # True if entities identified with the given context can be registered as
    # run configurations via `register_run_configuration_metadata`. False if
    # the specified context is a subordinate of another one.
    is_super: bool


class SupportedExtensionContexts(TypedDict):
    """Supported file extension and contexts schema."""

    # File extension or identifier of the input context.
    input_extension: str

    # The supported contexts for the given input extension, e.g. file,
    # selection, cell or others.
    # The context can be compared against the values of `RunContext`. e.g.,
    # `info['context'] == RunContext.File`
    contexts: List[ExtendedContext]


class WorkingDirSource:
    ConfigurationDirectory = 0
    CurrentDirectory = 1
    CustomDirectory = 2


class WorkingDirOpts(TypedDict):
    """Run execution working directory options."""

    # Source used to look for the working directory that will be used in
    # the run execution.
    source: WorkingDirSource

    # If not None, then it specifies a path to a custom directory location.
    path: Optional[str]


class RunExecutionParameters(TypedDict):
    """Run execution parameters."""

    # The working directory options
    working_dir: WorkingDirOpts

    # The run executor parameters
    executor_params: dict


class ExtendedRunExecutionParameters(TypedDict):
    """Extended run execution parameters."""

    # The unique identifier for the execution parameter set.
    uuid: str

    # The name of the run execution parameter set.
    name: str

    # The run execution parameters.
    params: RunExecutionParameters

    # The unique identifier for the file to which these parameters correspond
    # to, if any.
    file_uuid: Optional[str]

    # To identify these parameters as default
    default: bool


class StoredRunExecutorParameters(TypedDict):
    """Per run executor configuration parameters."""

    # Dictionary that maps from parameter identifiers to the actual
    # configuration.
    params: Dict[str, ExtendedRunExecutionParameters]


class StoredRunConfigurationExecutor(TypedDict):
    """Stored run executor options per run configuration settings."""

    # Name of the last used run executor for the current run configuration.
    executor: Optional[str]

    # Unique identifier for the currently selected parameters. None
    # if using default or transient settings.
    selected: Optional[str]


class RunConfigurationProvider(QObject):
    """
    Interface used to retrieve inputs to run on a code executor.

    This API needs to be implemented by any plugin that wants to provide
    an input/file to a code runner, e.g. editor files to be executed in
    the IPythonConsole. It also needs to be covariant with respect to
    :class:`spyder.api.plugins.SpyderDockablePlugin`.
    """

    def get_run_configuration(self, uuid: str) -> RunConfiguration:
        """
        Return the run information for the specified identifier.

        Arguments
        ---------
        uuid: str
            The unique identifier for the requested run configuration. Such
            id should have been registered previously via
            `register_run_configuration_metadata` on the Run plugin.

        Returns
        -------
        configuration: RunConfiguration
            A dictionary containing the information required by the run
            executor.
        """
        raise NotImplementedError(f'{type(self)} must implement '
                                  'get_run_configuration')

    def get_run_configuration_per_context(
            self,
            context: str,
            extra_action_name: Optional[str] = None,
            context_modificator: Optional[str] = None,
            re_run: bool = False
        ) -> Optional[RunConfiguration]:
        """
        Return the run information for the given context.

        The run configuration requested must be returned based on the
        currently focused file/object/etc.

        Arguments
        ---------
        context: str
            The context identifier for which the run configuration
            is requested.
        extra_action_name: Optional[str]
            If not None, the name of the action that the provider should take
            after gathering the run configuration input. Else, no action needs
            to take place.
        context_modificator: Optional[str]
            str describing how to alter the context, e.g. run selection
            <from line>.
        re_run: bool
            If True, then the requested configuration should correspond to the
            last executed configuration for the given context.

        Returns
        -------
        configuration: Optional[RunConfiguration]
            A dictionary containing the information required by the run
            executor. If None, then the provider indicates to the Run plugin
            that the input needs to be discarded.
        """
        raise NotImplementedError(f'{type(self)} must implement '
                                  'get_run_configuration_per_context')

    def focus_run_configuration(self, uuid: str):
        """
        Switch the focus of the run configuration provider to
        the run configuration given by parameter.

        Arguments
        ---------
        uuid: str
            The unique identifier for the run configuration that should be
            focused on. Such id should have been registered previously via
            `register_run_configuration_metadata` on the Run plugin.
        """
        raise NotImplementedError(f'{type(self)} must implement '
                                  'focus_run_configuration')


RunExecuteFunc = Callable[
    [RunConfiguration, ExtendedRunExecutionParameters],
    List[PossibleRunResult]]


def run_execute(
        func: RunExecuteFunc = None,
        extension: Optional[Union[str, List[str]]] = None,
        context: Optional[Union[str, List[str]]] = None
    ) -> RunExecuteFunc:
    """
    Method decorator used to mark a method as an executor for a given file
    extension and context.

    The methods that use this decorator must have the following signature:

    .. code-block:: python
        def execution_handler(
            input: RunConfiguration,
            conf: ExtendedRunExecutionParameters) -> List[PossibleRunResult]:
            ...

    Arguments
    ---------
    func: RunExecuteFunc
        Method to mark as an executor handler. Given by default when applying
        the decorator.
    extension: Optional[Union[str, List[str]]]
        The file extension or list of file extensions that the executor
        should handle. If None then the method will handle all extensions.
    context: Optional[Union[str, List[str]]]
        The execution context or list of contexts that the executor should
        handle. If None then the method will handle all contexts.

    Returns
    -------
    func: RunExecuteFunc
        The same method that was given as input.

    Notes
    -----
    The method must not crash or raise an exception, instead the
    `RunResult` must wrap a `RunResultError` structure.
    """
    if func is None:
        return functools.partial(
            run_execute, extension=extension, context=context)

    if extension is None:
        extension = '__extension'

    if context is None:
        context = '__context'

    if isinstance(extension, str):
        extension = [extension]

    if isinstance(context, str):
        context = [context]

    run_exec_list = []
    for ext in extension:
        for ctx in context:
            run_exec_list.append((ext, ctx))
    func._run_exec = run_exec_list
    return func


class RunExecutor(QObject):
    """
    Interface used to execute run context information.

    This API needs to be implemented by any plugin that wants to execute
    an input produced by a :class:`RunConfigurationProvider` to produce an
    output compatible by a :class:`RunResultViewer`. It also needs to be
    covariant with respect to :class:`spyder.api.plugins.SpyderPluginV2`
    """

    def __init__(self, parent):
        super().__init__(parent)
        self._exec_methods: Dict[str, RunExecuteFunc] = {}
        self._exec_ext_methods: Dict[str, RunExecuteFunc] = {}
        self._exec_context_methods: Dict[str, RunExecuteFunc] = {}

        for method_name in dir(self):
            method = getattr(self, method_name, None)
            if hasattr(method, '_run_exec'):
                if not isinstance(method._run_exec, list):
                    continue
                for extension, context in method._run_exec:
                    if extension == '__extension' and context != '__context':
                        self._exec_ext_methods[context] = method
                    elif extension != '__extension' and context == '__context':
                        self._exec_context_methods[extension] = method
                    else:
                        self._exec_methods[(extension, context)] = method

    def exec_run_configuration(
        self,
        input: RunConfiguration,
        conf: ExtendedRunExecutionParameters
    ) -> List[PossibleRunResult]:
        """
        Execute a run configuration.

        Arguments
        ---------
        input: RunConfiguration
            A dictionary containing the information required to execute the
            run input.
        conf: ExtendedRunExecutionParameters
            A dictionary containing the configuration parameters to use
            during execution.

        Returns
        -------
        results: List[PossibleRunResult]
            A list of `RunResult` dictionary entries, one per each `run_output`
            format requested by the input. Each entry must comply with the
            format requested.
        """
        metadata = input['metadata']
        context = metadata['context']
        extension = metadata['input_extension']
        context = RunContext[context['name']]
        query = (extension, context)

        logger.info('Running extension %s with context %s on executor %s',
                    extension, context, self)

        all_query = ('__extension', '__context')
        if query in self._exec_methods:
            method = self._exec_methods[query]
        elif context in self._exec_ext_methods:
            method = self._exec_ext_methods[context]
        elif extension in self._exec_context_methods:
            method = self._exec_context_methods[extension]
        elif all_query in self._exec_methods:
            method = self._exec_methods[all_query]
        else:
            raise NotImplementedError(
                f'There is no method available to '
                f'execute the requested context ({context}) and file '
                f'extension ({extension}) in {type(self)}')

        return method(input, conf)


class RunResultViewer:
    """
    Interface used to display run execution results.

    This API needs to be implemented by any plugin that wants to display
    an output produced by a :class:`RunResultViewer`. It also needs to be
    covariant with respect to :class:`spyder.api.plugins.SpyderPluginV2`
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
    QWidget subclass used to declare configuration options for a RunExecutor.

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
    The aforementioned parameters will always be passed by the Run
    dialog instance, and no subclass should modify them.
    """

    def __init__(
        self,
        parent: QWidget,
        context: Context,
        input_extension: str,
        input_metadata: RunConfigurationMetadata
    ):
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

    @staticmethod
    def get_default_configuration() -> dict:
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
        pass


RunExecutorConfigurationGroupFactory = Callable[
    [QWidget, Context, str, RunConfigurationMetadata],
    RunExecutorConfigurationGroup]

RunExecutorConfigurationGroupCreator = Union[
    RunExecutorConfigurationGroup, RunExecutorConfigurationGroupFactory]


class SupportedExecutionRunConfiguration(TypedDict):
    """Run execution configuration metadata."""

    # File extension or identifier of the input context.
    input_extension: str

    # The context for the given input extension, e.g. file, selection, cell or
    # others.
    # The context can be compared against the values of `RunContext`. e.g.,
    # `info['context'] == RunContext.File`
    context: Context

    # The output formats available for the given context and extension.
    output_formats: List[OutputFormat]

    # The configuration widget used to set the options for the current
    # input extension and context combination. If None or missing then no
    # configuration widget will be shown on the Run dialog for that
    # combination.
    configuration_widget: NotRequired[
        Optional[RunExecutorConfigurationGroupCreator]]

    # True if the executor requires a path in order to work. False otherwise
    requires_cwd: bool

    # Priority number used to select the executor. The lower, the better.
    priority: int
